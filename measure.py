"""Experiments A, B, C (project section 7) -> CSV files for plots.py.

Run:   python measure.py            (about 30 seconds)
Then:  python plots.py

Output (folder results/):
  exp_A.csv   time and memory vs K          (N = 10, V = 32)
  exp_B.csv   moves: consistent vs mod N    (K = 10,000, V = 32)
  exp_C.csv   balance and memory vs V       (N = 10, K = 10,000)
  exp_C_loads.csv  guests in every building for each V and salt
  guests_sample_N10_V32_K10000_salt0.csv  sample guest data
  moves_*.csv example move lists (guest id, old/new building, room)
  run_info.txt Python version, machine, salts and parameters

Every setting runs 3 times with salt 0, 1, 2. Both methods in the same
round use the same salt, guest IDs and building IDs. Memory is measured in
separate runs from timing, and is what Python tracks (tracemalloc), not the
whole process.
"""
import csv
import os
import platform
import statistics
import sys
import time
import tracemalloc

from hotel import HotelSystem
from mod_n import ModNHotel
from export_csv import export_guests

CHANNELS = 10
SEARCH_BATCH = 1000
SALTS = (0, 1, 2)
OUT_DIR = "results"


class SaltedHotel(HotelSystem):
    """HotelSystem whose every hash text gets a salt prefix.

    _hash_position has a single underscore, so it can be overridden
    without touching hotel.py. Same salt -> same ring and same guest
    positions, so two methods can be compared fairly.
    """

    def __init__(self, salt):
        super().__init__()
        self._salt = str(salt)

    def _hash_position(self, text: str):
        return super()._hash_position(f"{self._salt}:{text}")


def split_guests(K, channels=CHANNELS):
    """Spread K guests over channels 1..channels as evenly as possible."""
    base, extra = divmod(K, channels)
    return {c: base + (1 if c <= extra else 0) for c in range(1, channels + 1)}


def build_system(N, V, K, salt):
    """Build ring, then seat guests."""
    hotel = SaltedHotel(salt)
    hotel.init_setting(N, V, {})
    for c, count in split_guests(K).items():
        if count > 0:
            hotel.add_guest_batch(c, 1, count)
    return hotel


def build_mod_n(N, K, salt):
    hotel = ModNHotel(salt)
    hotel.init_setting(N, split_guests(K))
    return hotel


MS = 1_000          # seconds -> milliseconds
US = 1_000_000      # seconds -> microseconds
MIB = 1024 ** 2
KIB = 1024


# ------------------------------------------------------------------ #
# Timing (time.perf_counter). No input, print or file writing inside.
# ------------------------------------------------------------------ #
def run_timing(N, V, K, salt):
    """One timing round of the consistent-hashing system."""
    result = {"N": N, "V": V, "K": K, "salt": salt}
    hotel = SaltedHotel(salt)

    # 1) build ring (no guests yet)
    t0 = time.perf_counter()
    hotel.init_setting(N, V, {})
    result["build_ring_ms"] = (time.perf_counter() - t0) * MS

    # 2) seat initial guests
    t0 = time.perf_counter()
    for c, count in split_guests(K).items():
        if count > 0:
            hotel.add_guest_batch(c, 1, count)
    result["assign_guests_ms"] = (time.perf_counter() - t0) * MS

    # sample of 1,000 existing guests, prepared before timing
    guests = hotel.guests
    step = max(1, len(guests) // SEARCH_BATCH)
    picked = guests[::step][:SEARCH_BATCH]
    sample = [g.id for g in picked]
    addrs = [(g.building.id, g.room_no) for g in picked]
    n = len(sample)

    if n > 0:
        # 3a) search by guest id (dict lookup)
        t0 = time.perf_counter()
        for c, s in sample:
            hotel.search_by_guest(c, s)
        result["search_us"] = (time.perf_counter() - t0) / n * US

        # 3b) search by (node_id, room_no)
        t0 = time.perf_counter()
        for node_id, room_no in addrs:
            hotel.search_by_room(node_id, room_no)
        result["search_room_us"] = (time.perf_counter() - t0) / n * US

        # 3c) compute building from the ring (hash + binary search)
        t0 = time.perf_counter()
        for c, s in sample:
            hotel.find_building(c, s)
        result["find_building_us"] = (time.perf_counter() - t0) / n * US
    else:
        result["search_us"] = result["search_room_us"] = None
        result["find_building_us"] = None

    # 4) sort / list rooms
    t0 = time.perf_counter()
    rows = hotel.list_rooms()
    result["sort_ms"] = (time.perf_counter() - t0) * MS
    result["rows"] = len(rows)

    # 5) add building N, then remove it again
    t0 = time.perf_counter()
    ok, report = hotel.add_building(N)
    result["add_building_ms"] = (time.perf_counter() - t0) * MS
    result["moved_add"] = report["moved_count"] if ok else None

    t0 = time.perf_counter()
    ok, report = hotel.remove_building(N)
    result["remove_building_ms"] = (time.perf_counter() - t0) * MS
    result["moved_remove"] = report["moved_count"] if ok else None
    return result


# ------------------------------------------------------------------ #
# Memory (tracemalloc). Separate from timing.
# ------------------------------------------------------------------ #
def run_memory(N, V, K, salt):
    """Python-traced memory added since the same starting point."""
    # ring only (no guests)
    tracemalloc.start()
    try:
        base, _ = tracemalloc.get_traced_memory()
        ring = SaltedHotel(salt)
        ring.init_setting(N, V, {})
        ring_current, _ = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    del ring

    # whole system (ring + guests)
    tracemalloc.start()
    try:
        base_current, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        hotel = build_system(N, V, K, salt)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "N": N, "V": V, "K": K, "salt": salt,
        "ring_mem_kib": (ring_current - base) / KIB,
        "mem_current_mib": (current - base_current) / MIB,
        "mem_peak_mib": (peak - base_current) / MIB,
        "guest_count": hotel.guest_count,   # keeps hotel alive until here
    }


# ------------------------------------------------------------------ #
# Moves: consistent hashing vs hash mod N (experiment B)
# ------------------------------------------------------------------ #
def run_moves(N, V, K, salt, keep_lists=False):
    """Add 1 building and remove 1 building, each from a fresh system.

    The new building gets ID N; the removed building is ID 0.
    Same salt, guests and building IDs for both methods.
    """
    rows, lists = [], {}
    cases = (("add", lambda h: h.add_building(N)),
             ("remove", lambda h: h.remove_building(0)))
    makers = (("consistent", lambda: build_system(N, V, K, salt)),
              ("mod_n", lambda: build_mod_n(N, K, salt)))
    for method, make in makers:
        for action, do in cases:
            hotel = make()
            t0 = time.perf_counter()
            ok, report = do(hotel)
            elapsed = (time.perf_counter() - t0) * MS
            moves = report["moves"]
            if method == "consistent" and action == "add":
                rule_ok = all(m[3] == N for m in moves)     # only into new one
            elif method == "consistent":
                rule_ok = all(m[2] == 0 for m in moves)     # only out of removed one
            else:
                rule_ok = ""                                 # no such rule for mod N
            rows.append({
                "N": N, "V": V, "K": K, "salt": salt,
                "method": method, "action": action,
                "moved": report["moved_count"],
                "move_rate": report["move_rate"],
                "expected_ch_rate": 1 / (N + 1) if action == "add" else 1 / N,
                "time_ms": elapsed,
                "count_matches_list": report["moved_count"] == len(moves),
                "rule_ok": rule_ok,
            })
            if keep_lists:
                lists[(method, action)] = moves
    return rows, lists


# ------------------------------------------------------------------ #
# Balance (experiment C)
# ------------------------------------------------------------------ #
def run_balance(N, V, K, salt):
    """Returns (summary row, per-building rows)."""
    hotel = build_system(N, V, K, salt)
    rep = hotel.load_report()
    loads = [{"V": V, "N": N, "K": K, "salt": salt, "node_id": b, "guests": n}
             for b, n in rep["guests_per_building"].items()]
    ok, moves = hotel.add_building(N)
    return {"N": N, "V": V, "K": K, "salt": salt,
            "cv": rep["cv"], "max": rep["max"], "min": rep["min"],
            "mean": rep["mean"], "std": rep["std"],
            "move_rate_add": moves["move_rate"]}, loads


# ------------------------------------------------------------------ #
# Summary: median over rounds, with min-max
# ------------------------------------------------------------------ #
def summarize(rounds, keys):
    summary = {}
    for key in keys:
        vals = [r[key] for r in rounds if r.get(key) not in (None, "")]
        if vals:
            summary[key] = {
                "median": statistics.median(vals),
                "min": min(vals),
                "max": max(vals),
            }
    return summary


def print_summary(rounds, keys):
    for key, v in summarize(rounds, keys).items():
        print(f"  {key:20s} {v['median']:12.4f}   [{v['min']:.4f} - {v['max']:.4f}]")


def write_csv(path, rows):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"saved {path} ({len(rows)} rows)")


def write_moves(path, moves):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["channel_id", "sequence_id", "old_node_id",
                         "new_node_id", "room_no"])
        writer.writerows(moves)
    print(f"saved {path} ({len(moves)} moves)")


# ------------------------------------------------------------------ #
# Experiments
# ------------------------------------------------------------------ #
def experiment_a():
    print("\n===== Experiment A: K = 1,000; 10,000; 100,000 (N = 10, V = 32) =====")
    rows = []
    for K in (1_000, 10_000, 100_000):
        timing = [run_timing(10, 32, K, s) for s in SALTS]
        memory = [run_memory(10, 32, K, s) for s in SALTS]   # separate pass
        for t, m in zip(timing, memory):
            t.update({k: m[k] for k in ("ring_mem_kib", "mem_current_mib", "mem_peak_mib")})
        rows += timing
        print(f"\nK = {K:,}  (median of {len(SALTS)} salts [min - max]; ms, µs, MiB)")
        print_summary(timing, ("build_ring_ms", "assign_guests_ms", "search_us",
                               "search_room_us", "find_building_us", "sort_ms",
                               "add_building_ms", "remove_building_ms",
                               "mem_current_mib", "mem_peak_mib"))
    write_csv(os.path.join(OUT_DIR, "exp_A.csv"), rows)


def experiment_b():
    print("\n===== Experiment B: N = 5; 10; 20 (K = 10,000, V = 32) =====")
    rows = []
    for N in (5, 10, 20):
        for salt in SALTS:
            r, lists = run_moves(N, 32, 10_000, salt, keep_lists=(N == 10 and salt == 0))
            rows += r
            for (method, action), moves in lists.items():
                write_moves(os.path.join(OUT_DIR, f"moves_{method}_{action}_N10_salt0.csv"), moves)
        print(f"\nN = {N}  (median move rate of {len(SALTS)} salts)")
        for method in ("consistent", "mod_n"):
            for action in ("add", "remove"):
                sel = [r for r in rows if r["N"] == N and r["method"] == method
                       and r["action"] == action]
                med = statistics.median(r["move_rate"] for r in sel)
                exp = sel[0]["expected_ch_rate"]
                ms = statistics.median(r["time_ms"] for r in sel)
                print(f"  {method:10s} {action:6s} rate {med:6.2%}  "
                      f"(CH expected {exp:6.2%})  time {ms:8.2f} ms")
    bad = [r for r in rows if r["rule_ok"] is False or not r["count_matches_list"]]
    print(f"\nRule checks failed: {len(bad)}")
    write_csv(os.path.join(OUT_DIR, "exp_B.csv"), rows)


def experiment_c():
    print("\n===== Experiment C: V = 1; 8; 32 (N = 10, K = 10,000) =====")
    rows, load_rows = [], []
    for V in (1, 8, 32):
        results = [run_balance(10, V, 10_000, s) for s in SALTS]
        balance = [summary for summary, _ in results]
        for _, loads in results:
            load_rows += loads
        memory = [run_memory(10, V, 10_000, s) for s in SALTS]
        for b, m in zip(balance, memory):
            b.update({k: m[k] for k in ("ring_mem_kib", "mem_current_mib", "mem_peak_mib")})
        rows += balance
        print(f"\nV = {V}  (median of {len(SALTS)} salts [min - max])")
        print_summary(balance, ("cv", "max", "min", "move_rate_add",
                                "ring_mem_kib", "mem_current_mib", "mem_peak_mib"))
    write_csv(os.path.join(OUT_DIR, "exp_C.csv"), rows)
    write_csv(os.path.join(OUT_DIR, "exp_C_loads.csv"), load_rows)


def write_sample_guests():
    """Sample guest data (section 10.1 item 3): N=10, V=32, K=10,000, salt 0."""
    hotel = build_system(10, 32, 10_000, 0)
    path = os.path.join(OUT_DIR, "guests_sample_N10_V32_K10000_salt0.csv")
    n = export_guests(hotel, path)
    print(f"saved {path} ({n} rows = {hotel.guest_count} guests)")


def write_run_info():
    path = os.path.join(OUT_DIR, "run_info.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Python: {sys.version}\n")
        f.write(f"Platform: {platform.platform()}\n")
        f.write(f"Processor: {platform.processor() or platform.machine()}\n")
        f.write(f"Salts: {SALTS} (hash text = '<salt>:<text>')\n")
        f.write(f"Channels: {CHANNELS}, guests split evenly\n")
        f.write(f"Search batch: {SEARCH_BATCH} lookups, time divided per lookup\n")
        f.write("A: N=10 V=32 K=1000/10000/100000\n")
        f.write("B: K=10000 V=32 N=5/10/20; add building ID N, remove building ID 0\n")
        f.write("C: N=10 K=10000 V=1/8/32\n")
        f.write("Memory: tracemalloc (Python-tracked, not whole process), "
                "separate runs from timing\n")
    print(f"saved {path}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    start = time.perf_counter()
    experiment_a()
    experiment_b()
    experiment_c()
    write_sample_guests()
    write_run_info()
    print(f"\nDone in {time.perf_counter() - start:.1f} s. Next: python plots.py")