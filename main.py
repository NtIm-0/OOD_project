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
        print(
            f"{guest.channel_id} {guest.sequence_id} "
            f"{guest.building.id} {guest.room_no}"
        )
    if hotel.guest_count > preview_limit:
        print(f"Showing {preview_limit} of {hotel.guest_count} guests.")


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
    
    return hotel


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nInitialization cancelled.")
