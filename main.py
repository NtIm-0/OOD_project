import os

from hotel import HotelSystem
from export_csv import export_guests, export_moves, export_load_report

PREVIEW = 20                 # rows shown on screen; files always have everything
OUT_DIR = "output"


# ------------------------------------------------------------------ #
# Reading input (asks again instead of stopping the program)
# ------------------------------------------------------------------ #
def read_int(prompt, minimum):
    while True:
        try:
            value = int(input(prompt))
        except ValueError:
            print("Input must be an integer. Try again.")
            continue
        if value < minimum:
            print(f"Input must be an integer >= {minimum}. Try again.")
            continue
        return value


def read_ring_settings():
    while True:
        try:
            N, V = map(int, input("Enter N V: ").split())
        except ValueError:
            print("Enter two integers for N V, e.g. 10 32. Try again.")
            continue
        if N < 1 or V < 1:
            print("N and V must both be positive integers. Try again.")
            continue
        return N, V


# ------------------------------------------------------------------ #
# Display helpers
# ------------------------------------------------------------------ #
def show_initial_state(hotel, preview_limit=PREVIEW):
    print("\nInitialization complete.")
    show_state(hotel, preview_limit)


def show_state(hotel, preview_limit=PREVIEW):
    print(f"Buildings: {hotel.building_count}")
    print(f"Virtual nodes: {hotel.node_count} ({hotel.max_node} per building)")
    print(f"Channels: {hotel.channel_count}")
    print(f"Guests: {hotel.guest_count}")

    for building in hotel.buildings:
        print(f"Building {building.id}: {building.guest_count} guests")

    if hotel.guest_count == 0:
        print("No guests checked in.")
        return

    print("\nGuests (check-in order):")
    print("channel_id sequence_id building_id room_no")
    for guest in hotel.guests[:preview_limit]:
        c, s = guest.id
        print(f"{c} {s} {guest.building.id} {guest.room_no}")
    if hotel.guest_count > preview_limit:
        print(f"Showing {preview_limit} of {hotel.guest_count} guests.")


def show_move_report(report, preview_limit=PREVIEW):
    print(f"\nAction: {report['action']} building {report['building_id']}")
    print(f"Moved: {report['moved_count']} of {report['guest_count']} guests")
    if report["move_rate"] is None:
        print("Move rate: not calculated (no guests)")
    else:
        print(f"Move rate: {report['move_rate']:.4f} ({report['move_rate'] * 100:.2f}%)")

    if report["moved_count"] == 0:
        return
    print("channel_id sequence_id from_building to_building room_no")
    for c, s, old, new, room in report["moves"][:preview_limit]:
        print(f"{c} {s} {old} {new} {room}")
    if report["moved_count"] > preview_limit:
        print(f"Showing {preview_limit} of {report['moved_count']} moves.")


def show_load_report(hotel):
    report = hotel.load_report()
    print("\nLoad balance:")
    print("building_id guests")
    for building_id, count in report["guests_per_building"].items():
        print(f"{building_id} {count}")
    print(f"Max: {report['max']}  Min: {report['min']}")
    print(f"Mean: {report['mean']:.2f}  Std: {report['std']:.2f}")
    if report["cv"] is None:
        print(f"CV: not calculated ({report['note']})")
    else:
        print(f"CV: {report['cv']:.4f}")


def show_search_by_guest(hotel, c, s):
    ok, result = hotel.search_by_guest(c, s)
    if ok:
        building_id, room_no = result
        print(f"Guest ({c}, {s}) -> building {building_id}, room {room_no}")
    else:
        print(f"Not found: {result}")


def show_search_by_room(hotel, building_id, room_no):
    ok, result = hotel.search_by_room(building_id, room_no)
    if ok:
        c, s = result
        print(f"Building {building_id}, room {room_no} -> guest ({c}, {s})")
    else:
        print(f"Not found: {result}")


def show_rooms(hotel, preview_limit=PREVIEW):
    rows = hotel.list_rooms()
    print(f"\nOccupied rooms: {len(rows)}")
    if not rows:
        print("No occupied rooms.")
        return
    print("building_id room_no channel_id sequence_id")
    for building_id, room_no, c, s in rows[:preview_limit]:
        print(f"{building_id} {room_no} {c} {s}")
    if len(rows) > preview_limit:
        print(f"Showing {preview_limit} of {len(rows)} rooms.")


# ------------------------------------------------------------------ #
# Menu actions (each one reads its own input)
# ------------------------------------------------------------------ #
def do_add_guest(hotel, state):
    c = read_int("Channel: ", 1)
    s = read_int("Sequence: ", 1)
    ok, result = hotel.add_guest(c, s)
    if ok:
        print(f"Added guest {result.id} -> building {result.building.id}, "
              f"room {result.room_no}")
    else:
        print(f"Refused: {result}")


def do_add_batch(hotel, state):
    c = read_int("Channel: ", 1)
    s_start = read_int("Starting sequence: ", 1)
    count = read_int("Count (0 or more): ", 0)
    ok, result = hotel.add_guest_batch(c, s_start, count)
    if ok:
        print(f"Added {len(result)} guests: ({c}, {s_start}) .. ({c}, {s_start + count - 1})"
              if result else "Count is 0: nothing changed.")
    else:
        print(f"Refused (nothing added): {result}")


def do_remove_guest(hotel, state):
    c = read_int("Channel: ", 1)
    s = read_int("Sequence: ", 1)
    ok, result = hotel.remove_guest(c, s)
    print(f"Removed guest {result.id}" if ok else f"Refused: {result}")


def do_add_building(hotel, state):
    b = read_int("New building id: ", 0)
    ok, result = hotel.add_building(b)
    if ok:
        show_move_report(result)
        state["last_moves"] = result
    else:
        print(f"Refused: {result}")


def do_remove_building(hotel, state):
    b = read_int("Building id to remove: ", 0)
    ok, result = hotel.remove_building(b)
    if ok:
        show_move_report(result)
        state["last_moves"] = result
    else:
        print(f"Refused: {result}")


def do_search_guest(hotel, state):
    show_search_by_guest(hotel, read_int("Channel: ", 1), read_int("Sequence: ", 1))


def do_search_room(hotel, state):
    show_search_by_room(hotel, read_int("Building id: ", 0), read_int("Room no: ", 1))


def do_export(hotel, state):
    guests_path = os.path.join(OUT_DIR, "guests.csv")
    n = export_guests(hotel, guests_path)
    print(f"Saved {guests_path} ({n} rows, {hotel.guest_count} guests in system)")

    load_path = os.path.join(OUT_DIR, "load_report.csv")
    export_load_report(hotel, load_path)
    print(f"Saved {load_path}")

    report = state.get("last_moves")
    if report is None:
        print("No move list yet (add or remove a building first).")
    else:
        name = f"moves_{report['action']}_{report['building_id']}.csv"
        moves_path = os.path.join(OUT_DIR, name)
        m = export_moves(report, moves_path)
        print(f"Saved {moves_path} ({m} moves)")


def do_experiments(hotel, state):
    print("Runs experiments A, B, C with salts 0, 1, 2 (about 30 seconds).")
    if input("Start? (y/n): ").strip().lower() != "y":
        print("Cancelled.")
        return
    import measure
    os.makedirs(measure.OUT_DIR, exist_ok=True)
    measure.experiment_a()
    measure.experiment_b()
    measure.experiment_c()
    measure.write_run_info()
    try:
        import plots
    except ImportError:
        print("matplotlib is not installed: run 'pip install matplotlib', "
              "then 'python plots.py' to draw the graphs.")
        return
    jobs = [("exp_A.csv", plots.plot_time_vs_k),
            ("exp_B.csv", plots.plot_move_rate_vs_n),
            ("exp_C.csv", plots.plot_v_effect)]
    for name, plot in jobs:
        plot(plots.read_rows(os.path.join(measure.OUT_DIR, name)),
             os.path.join(measure.OUT_DIR, "figures"))


MENU = [
    ("Show state", lambda h, st: show_state(h)),
    ("Add guest", do_add_guest),
    ("Add guest batch", do_add_batch),
    ("Remove guest", do_remove_guest),
    ("Add building", do_add_building),
    ("Remove building", do_remove_building),
    ("Search by guest (c, s)", do_search_guest),
    ("Search by room (node_id, room_no)", do_search_room),
    ("List occupied rooms (sorted)", lambda h, st: show_rooms(h)),
    ("Load balance report", lambda h, st: show_load_report(h)),
    ("Export CSV (guests, load, last moves)", do_export),
    ("Run experiments A/B/C and draw graphs", do_experiments),
]


def print_menu():
    print("\n========== MENU ==========")
    for i, (label, _) in enumerate(MENU, start=1):
        print(f"{i:2d}. {label}")
    print(" 0. Exit")


# ------------------------------------------------------------------ #
def setup():
    N, V = read_ring_settings()
    channel_count = read_int("Number of channels (0 or more): ", 0)
    guests_per_channel = {}
    for channel_id in range(1, channel_count + 1):
        guests_per_channel[channel_id] = read_int(
            f"Guests in channel {channel_id} (0 or more): ", 0)
    hotel = HotelSystem()
    hotel.init_setting(N, V, guests_per_channel)
    show_initial_state(hotel)
    return hotel


def main():
    hotel = setup()
    state = {"last_moves": None}
    while True:
        print_menu()
        choice = read_int("Choose: ", 0)
        if choice == 0:
            print("Goodbye.")
            return hotel
        if choice > len(MENU):
            print(f"Choose 0 to {len(MENU)}.")
            continue
        label, action = MENU[choice - 1]
        print(f"\n--- {label} ---")
        try:
            action(hotel, state)
        except ValueError as e:          # refused politely; data unchanged
            print(f"Error: {e}")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nProgram closed.")