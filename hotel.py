import hashlib


class HotelSystem:
    def __init__(self):
        self.__building = []
        self.__max_node = 0
        self.__node_line = []
        self.__guests = {}
        self.__guests_per_channel = {}

    def _hash_position(self, text: str):
        data = text.encode("utf-8")
        result = hashlib.sha256(data).digest()
        return int.from_bytes(result[:8], "big")

    def init_setting(self, N, V, guests_per_channel):  ## เรียกครั้งเดียวตอน run 
        self.__max_node = V
        self.__guests_per_channel = guests_per_channel.copy()

        for i in range(N):
            building = Building(i)
            self.__building.append(building)
            for node_ind in range(V):
                node = Node(
                    self._hash_position(f"Build{i}:{node_ind}"),
                    building,
                    node_ind
                )
                self.__node_line.append(node)

        self.__node_line.sort(
            key=lambda n: (n.id, n.building.id, n.node_ind)
        )

        # The ring must be complete before any guest chooses a building.
        for channel_id in self.__guests_per_channel:
            count = self.__guests_per_channel[channel_id]
            for sequence_id in range(1, count + 1):
                building = self.find_building(channel_id, sequence_id)
                guest = Guest(channel_id, sequence_id, building)
                room = Room(guest.room_no, guest)
                building.add_room(room)
                self.__guests[guest.id] = guest

    def find_node(self, position: int):
        """Return the first point at or after position, wrapping if needed."""
        if not self.__node_line:
            raise ValueError("Initialize the hotel before searching the ring.")
        if type(position) is not int or not 0 <= position < 2**64:
            raise ValueError("Position must be an integer in the 64-bit range.")

        left = 0
        right = len(self.__node_line)
        while left < right:
            middle = (left + right) // 2
            if self.__node_line[middle].id < position:
                left = middle + 1
            else:
                right = middle

        if left == len(self.__node_line):
            left = 0
        return self.__node_line[left]

    def find_building(self, channel_id: int, sequence_id: int):
        """Calculate a destination using the guest ID and the current ring."""
        if type(channel_id) is not int or channel_id < 1:
            raise ValueError("Channel ID must be a positive integer.")
        if type(sequence_id) is not int or sequence_id < 1:
            raise ValueError("Sequence ID must be a positive integer.")

        position = self._hash_position(f"guest:{channel_id}:{sequence_id}")
        return self.find_node(position).building

    def push_node(self, node: object):
        if self.__node_line == []:
            self.__node_line.append(node)
            return

        node_key = (node.id, node.building.id, node.node_ind)
        for i in range(len(self.__node_line)):
            current = self.__node_line[i]
            current_key = (current.id, current.building.id, current.node_ind)
            if node_key < current_key:
                self.__node_line.insert(i, node)
                return
        self.__node_line.append(node)

    def get_guest(self, channel_id: int, sequence_id: int):
        return self.__guests.get((channel_id, sequence_id))

    @property
    def buildings(self):
        return tuple(self.__building)

    @property
    def node_line(self):
        return tuple(self.__node_line)

    @property
    def guests(self):
        return tuple(self.__guests.values())

    @property
    def max_node(self):
        return self.__max_node

    @property
    def building_count(self):
        return len(self.__building)

    @property
    def node_count(self):
        return len(self.__node_line)

    @property
    def channel_count(self):
        return len(self.__guests_per_channel)

    @property
    def guest_count(self):
        return len(self.__guests)


class Guest:
    def __init__(self, channel_id: int, sequence_id: int, building):
        if type(channel_id) is not int or channel_id < 1:
            raise ValueError("Channel ID must be a positive integer.")
        if type(sequence_id) is not int or sequence_id < 1:
            raise ValueError("Sequence ID must be a positive integer.")

        self.__channel_id = channel_id
        self.__sequence_id = sequence_id
        self.__building = building

        # Cantor pairing uses only the guest ID, never the building.
        a = channel_id - 1
        b = sequence_id - 1
        self.__room_no = ((a + b) * (a + b + 1)) // 2 + b + 1

    @property
    def id(self):
        return self.__channel_id, self.__sequence_id

    @property
    def channel_id(self):
        return self.__channel_id

    @property
    def sequence_id(self):
        return self.__sequence_id

    @property
    def building(self):
        return self.__building

    @property
    def room_no(self):
        return self.__room_no


class Building:
    def __init__(self, building_id: int):
        self.__building_id = building_id
        self.__rooms = {}

    def add_room(self, room):
        if room.guest.building is not self:
            raise ValueError("The guest belongs to another building.")
        if room.id in self.__rooms:
            raise ValueError("The room is already occupied.")
        self.__rooms[room.id] = room

    def get_room(self, room_id: int):
        return self.__rooms.get(room_id)

    @property
    def id(self):
        return self.__building_id

    @property
    def rooms(self):
        return tuple(self.__rooms.values())

    @property
    def guest_count(self):
        return len(self.__rooms)


class Node:
    def __init__(self, id: int, Building: object, node_ind: int):
        self.__building = Building
        self.__id = int(id)
        self.__node_ind = node_ind

    @property
    def id(self):
        return self.__id

    @property
    def node_ind(self):
        return self.__node_ind

    @property
    def building(self):
        return self.__building


class Room:
    def __init__(self, room_id: int, guest: Guest):
        if room_id != guest.room_no:
            raise ValueError("The room number must match the guest ID.")
        self.__id = room_id
        self.__guest = guest

    @property
    def id(self):
        return self.__id

    @property
    def guest(self):
        return self.__guest
