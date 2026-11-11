import csv
import statistics
import time
import tracemalloc
from hotel import HotelSystem

CHANNELS = 10
SEARCH_BATCH = 1000
SALTS = (0, 1, 2)


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
    """Build ring, then seat guests. Used by the memory run."""
    hotel = SaltedHotel(salt)
    hotel.init_setting(N, V, {})
    for c, count in split_guests(K).items():
        if count > 0:
            hotel.add_guest_batch(c, 1, count)
    return hotel


# ------------------------------------------------------------------ #
# Timing (time.perf_counter, seconds)
# ------------------------------------------------------------------ #
def run_timing(N, V, K, salt):
    """One timing round. Returns a dict of seconds (search = per call)."""
    result = {"N": N, "V": V, "K": K, "salt": salt}
    hotel = SaltedHotel(salt)

    # 1) build ring (no guests yet)
    t0 = time.perf_counter()
    hotel.init_setting(N, V, {})
    result["t_build_ring"] = time.perf_counter() - t0

    # 2) seat initial guests
    t0 = time.perf_counter()
    for c, count in split_guests(K).items():
        if count > 0:
            hotel.add_guest_batch(c, 1, count)
    result["t_seat_guests"] = time.perf_counter() - t0

    # sample of 1,000 existing guest ids (spread evenly over all guests)
    guests = hotel.guests
    step = max(1, len(guests) // SEARCH_BATCH)
    sample = [g.id for g in guests[::step][:SEARCH_BATCH]]
    n = len(sample)

    if n > 0:
        # 3a) search by guest id (dict lookup)
        t0 = time.perf_counter()
        for c, s in sample:
            hotel.search_by_guest(c, s)
        result["t_search_guest"] = (time.perf_counter() - t0) / n

        # 3b) search by (node_id, room_no)
        addrs = [(g.building.id, g.room_no) for g in guests[::step][:SEARCH_BATCH]]
        t0 = time.perf_counter()
        for node_id, room_no in addrs:
            hotel.search_by_room(node_id, room_no)
        result["t_search_room"] = (time.perf_counter() - t0) / n

        # 3c) compute building from the ring (hash + binary search)
        t0 = time.perf_counter()
        for c, s in sample:
            hotel.find_building(c, s)
        result["t_find_building"] = (time.perf_counter() - t0) / n
    else:
        result["t_search_guest"] = result["t_search_room"] = None
        result["t_find_building"] = None

    # 4) sort / list rooms
    t0 = time.perf_counter()
    rows = hotel.list_rooms()
    result["t_list_rooms"] = time.perf_counter() - t0
    result["rows"] = len(rows)

    # 5) add building N, then remove it again
    t0 = time.perf_counter()
    ok, report = hotel.add_building(N)
    result["t_add_building"] = time.perf_counter() - t0
    result["moved_add"] = report["moved_count"] if ok else None

    t0 = time.perf_counter()
    ok, report = hotel.remove_building(N)
    result["t_remove_building"] = time.perf_counter() - t0
    result["moved_remove"] = report["moved_count"] if ok else None
    return result


# ------------------------------------------------------------------ #
# Memory (tracemalloc, MiB). Separate from timing.
# ------------------------------------------------------------------ #
def run_memory(N, V, K, salt):
    """Python-traced memory added since the same starting point."""
    tracemalloc.start()
    try:
        base_current, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        hotel = build_system(N, V, K, salt)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    mib = 1024 ** 2
    return {
        "N": N, "V": V, "K": K, "salt": salt,
        "mem_current_mib": (current - base_current) / mib,
        "mem_peak_mib": (peak - base_current) / mib,
        "guest_count": hotel.guest_count,   # keeps hotel alive until here
    }


# ------------------------------------------------------------------ #
# Summary: median over rounds, with min-max
# ------------------------------------------------------------------ #
def summarize(rounds, keys):
    summary = {}
    for key in keys:
        vals = [r[key] for r in rounds if r.get(key) is not None]
        if vals:
            summary[key] = {
                "median": statistics.median(vals),
                "min": min(vals),
                "max": max(vals),
            }
    return summary



TIMING_KEYS = (
    "t_build_ring", "t_seat_guests", "t_search_guest", "t_search_room",
    "t_find_building", "t_list_rooms", "t_add_building", "t_remove_building",
)
MEMORY_KEYS = ("mem_current_mib", "mem_peak_mib")


def measure(N, V, K, salts=SALTS):
    timing_rounds = [run_timing(N, V, K, s) for s in salts]
    memory_rounds = [run_memory(N, V, K, s) for s in salts]   # separate pass
    return timing_rounds, memory_rounds


def write_csv(path, rows):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def run_experiment(title, configs, all_timing, all_memory):
    print(f"------------- {title} ------------")
    for N, V, K in configs:
        t_rounds, m_rounds = measure(N=N, V=V, K=K)
        for r in t_rounds + m_rounds:
            r["experiment"] = title[:6]
        all_timing += t_rounds
        all_memory += m_rounds

        print(f"\n=== N={N} V={V} K={K:,} (median of {len(SALTS)} rounds, min-max) ===")
        for key, v in summarize(t_rounds, TIMING_KEYS).items():
            print(f"{key:20s} {v['median']:.6f} s  [{v['min']:.6f} - {v['max']:.6f}]")
        for key, v in summarize(m_rounds, MEMORY_KEYS).items():
            print(f"{key:20s} {v['median']:.3f} MiB  [{v['min']:.3f} - {v['max']:.3f}]")

if __name__ == "__main__":
    # Experiment A: vary K, fixed N = 10, V = 32
    all_timing, all_memory = [], []
    run_experiment("Test A : K = 1,000; 10,000; 100,000",
                   [(10, 32, K) for K in (1_000, 10_000, 100_000)], all_timing, all_memory)
    run_experiment("Test B : N = 5; 10; 20",
                   [(N, 32, 10_000) for N in (5, 10, 20)], all_timing, all_memory)
    run_experiment("Test C : V = 1; 8; 32",
                   [(10, V, 10_000) for V in (1, 8, 32)], all_timing, all_memory)
    write_csv("timing_results.csv", all_timing)
    write_csv("memory_results.csv", all_memory)
    print("\nSaved timing_results.csv and memory_results.csv")
    print("Note: memory is what Python tracks (tracemalloc), not the whole process.")