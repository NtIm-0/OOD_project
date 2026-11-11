from hotel import HotelSystem

def read_int(prompt, minimum):
    try:
        value = int(input(prompt))
    except ValueError:
        print("Input must be an integer. Please run the program again.")
        return -1
    if value < minimum:
        print(f"Input must be an integer >= {minimum}. Please run the program again.")
        return -1
    return value


def read_ring_settings():
    try:
        N, V = map(int, input("Enter N V: ").split())
    except ValueError:
        print("Enter two integers for N V. Please run the program again.")
        return -1, -1
    if N < 1 or V < 1:
        print("N and V must both be positive integers. Please run the program again.")
        return -1, -1
    return N, V


def show_initial_state(hotel, preview_limit=20):
    print("\nInitialization complete.")
    print(f"Buildings: {hotel.building_count}")
    print(f"Virtual nodes: {hotel.node_count} ({hotel.max_node} per building)")
    print(f"Channels: {hotel.channel_count}")
    print(f"Guests: {hotel.guest_count}")

    for building in hotel.buildings:
        print(f"Building {building.id}: {building.guest_count} guests")

    if hotel.guest_count == 0:
        print("No guests checked in.")
        return

    print("\nInitial guests (channel order):")
    print("channel_id sequence_id building_id room_no")
    for guest in hotel.guests[:preview_limit]:
        # print(
        #     f"{guest.channel_id} {guest.sequence_id} "
        #     f"{guest.building.id} {guest.room_no}"
        # )
        c, s = guest.id
        print(f"{c} {s} {guest.building.id} {guest.room_no}")
        
    if hotel.guest_count > preview_limit:
        print(f"Showing {preview_limit} of {hotel.guest_count} guests.")
        
def show_state(hotel, preview_limit=20):
    print(f"Buildings: {hotel.building_count}")
    print(f"Virtual nodes: {hotel.node_count} ({hotel.max_node} per building)")
    print(f"Channels: {hotel.channel_count}")
    print(f"Guests: {hotel.guest_count}")

    for building in hotel.buildings:
        print(f"Building {building.id}: {building.guest_count} guests")

    if hotel.guest_count == 0:
        print("No guests checked in.")
        return

    print("\nInitial guests (channel order):")
    print("channel_id sequence_id building_id room_no")
    for guest in hotel.guests[:preview_limit]:
        # print(
        #     f"{guest.channel_id} {guest.sequence_id} "
        #     f"{guest.building.id} {guest.room_no}"
        # )
        c, s = guest.id
        print(f"{c} {s} {guest.building.id} {guest.room_no}")
        #ส่วนที่คอมเม้นไว้มันไม่มีใน hotel.py แล้ว
    if hotel.guest_count > preview_limit:
        print(f"Showing {preview_limit} of {hotel.guest_count} guests.")

def show_move_report(report, preview_limit=20):
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

# แสดงการ search

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


def show_rooms(hotel, preview_limit=20):
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

def main():
    N, V = read_ring_settings()
    if N == -1:
        return
    channel_count = read_int("Number of channels (0 or more): ", 0)
    if channel_count == -1:
        return
    
    guests_per_channel = {}
    for channel_id in range(1, channel_count + 1):
        count = read_int(f"Guests in channel {channel_id} (0 or more): ", 0)
        if count == -1:
            return
        guests_per_channel[channel_id] = count

    hotel = HotelSystem()
    hotel.init_setting(N, V, guests_per_channel)
    show_initial_state(hotel)
    show_load_report(hotel)
    
    # testing adding/removing guest
    try :
        c = int(input("Adding guest from channel: "))
        s = int(input("Sequence: "))
        print(f"Result: {hotel.add_guest(c, s)}")
        show_state(hotel)
        show_load_report(hotel)
        
        c = int(input("Adding guest batch from channel: "))
        s_start = int(input("Starting sequence: "))
        count = int(input("Count: "))
        print(f"Result: {hotel.add_guest_batch(c, s_start, count)}")
        show_state(hotel)
        show_load_report(hotel)
        
        c = int(input("Removing guest from channel: "))
        s = int(input("Sequence: "))
        print(f"Result: {hotel.remove_guest(c, s)}")
        show_state(hotel)
        show_load_report(hotel)
    #เพิ่มการ add / remove buliding
        b = int(input("Add building id: "))
        ok, result = hotel.add_building(b)
        if ok:
            show_move_report(result)
        else:
            print(f"Result: {result}")
        show_state(hotel)

        b = int(input("Remove building id: "))
        ok, result = hotel.remove_building(b)
        if ok:
            show_move_report(result)
        else:
            print(f"Result: {result}")
        show_state(hotel)

    # search both ways + list occupied rooms

        c = int(input("Search guest - channel: "))
        s = int(input("Search guest - sequence: "))
        show_search_by_guest(hotel, c, s)

        b = int(input("Search room - building id: "))
        r = int(input("Search room - room no: "))
        show_search_by_room(hotel, b, r)

        show_rooms(hotel)
        
        return hotel

    except ValueError as e:
        print(f"Error: {e}")

#ถ้าพิมพ์ c = 0 จะ error เลยใส่ try ครอบ

if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nInitialization cancelled.")
