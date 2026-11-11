import hashlib
import bisect

class HotelSystem:
    def __init__(self):
        self.__building = {}
        self.__max_node = 0
        self.__node_line = []
        self.__guests = {}
        self.__guests_per_channel = {}

    def _hash_position(self, text: str):
        data = text.encode("utf-8")
        result = hashlib.sha256(data).digest()
        return int.from_bytes(result[:8], "big")

#เพิ่ม node position and node key ให้ใช้ pattern เดียวกันเสมอ , node key ไว้คืน key
    def _node_position(self, building_id: int, j: int):
        return self._hash_position(f"node:{building_id}:{j}")
 
    @staticmethod
    def _node_key(node):
        return (node.id, node.building.id, node.node_ind)

    def init_setting(self, N, V, guests_per_channel):  ## เรียกครั้งเดียวตอน run 
        self.__max_node = V
        self.__guests_per_channel = guests_per_channel.copy()

        for i in range(N):
            building = Building(i)
            self.__building[building.id] = building
            for node_ind in range(V):
                node = Node(
                    self._node_position(i, node_ind),
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
        right = len(self.__node_line) - 1
        while left <= right:
            middle = (left + right) // 2
            if position > self.__node_line[middle].id:
                left = middle + 1
            else:
                right = middle - 1

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
    
    # --------------------------------------------------- #
    # ======= ADD/REMOVE GUEST FUNCTION ======= #
    # --------------------------------------------------- #
    
    def add_guest(self, channel_id: int, sequence_id: int):
        
        if not self.__node_line:
            raise ValueError("Hotel has not been initialized.")
        if type(channel_id) is not int or channel_id < 1:
            raise ValueError("Channel ID must be a positive integer.")
        if type(sequence_id) is not int or sequence_id < 1:
            raise ValueError("Sequence ID must be a positive integer.")
        
        
        building = self.find_building(channel_id, sequence_id)
        guest = Guest(channel_id, sequence_id, building)
        room = Room(guest.room_no, guest)

        if guest.id in self.__guests:
            return False, f"Guest {guest.id} already exist."
        
        building.add_room(room)
        self.__guests[guest.id] = guest
        self.__guests_per_channel[channel_id] = self.__guests_per_channel.get(channel_id, 0) + 1
        
        return True, guest

    def add_guest_batch(self, channel_id: int, s_start: int, count: int):
       
        if not self.__node_line:
            raise ValueError("Hotel has not been initialized.")
        if type(channel_id) is not int or channel_id < 1:
            raise ValueError("Channel ID must be a positive integer.")
        if type(s_start) is not int or s_start < 1:
            raise ValueError("Starting sequence ID must be a positive integer.")
        if type(count) is not int or count < 0:
            raise ValueError("Count must be a positive integer.")
        
        # 0 guests to be added = no change
        if count == 0:
            return True, ()

        # if some guest already exist, deny all
        for s in range(s_start, s_start + count):
            if (channel_id, s) in self.__guests:
                return False, f"Batch denied: Guest ({channel_id}, {s}) already exist."
                
        added_guests = []
        for s in range(s_start, s_start + count):
            building = self.find_building(channel_id, s)
            guest = Guest(channel_id, s, building)
            room = Room(guest.room_no, guest)

            building.add_room(room)
            self.__guests[guest.id] = guest
            added_guests.append(guest)

        self.__guests_per_channel[channel_id] = self.__guests_per_channel.get(channel_id, 0) + count
        return True, tuple(added_guests)
    
    def remove_guest(self, channel_id: int, sequence_id: int):
        
        if type(channel_id) is not int or channel_id < 1:
            raise ValueError("Channel ID must be a positive integer.")
        if type(sequence_id) is not int or sequence_id < 1:
            raise ValueError("Sequence ID must be a positive integer.")

        guest_id = (channel_id, sequence_id)
        guest = self.__guests.get(guest_id)

        if guest is None:
            return False, f"Guest {guest_id} does not exist."

        guest.building.remove_room(guest.room_no)
        del self.__guests[guest_id]

        if channel_id in self.__guests_per_channel:
            self.__guests_per_channel[channel_id] -= 1
            if self.__guests_per_channel[channel_id] <= 0:
                del self.__guests_per_channel[channel_id]

        return True, guest

    # --------------------------------------------------- #
    # ======= ADD/REMOVE BUILDING FUNCTION ======= #
    # --------------------------------------------------- #
 
    def add_building(self, building_id: int):
        if not self.__node_line:
            raise ValueError("Hotel has not been initialized.")
        if type(building_id) is not int or building_id < 0:
            raise ValueError("Building ID must be a non-negative integer.")
        if building_id in self.__building:
            return False, f"Building {building_id} already exists."
 
        # สร้างอาคารใหม่ แทรกเฉพาะ V จุดของอาคารนั้นด้วย
        new_building = Building(building_id)
        self.__building[building_id] = new_building
        for j in range(self.__max_node):
            node = Node(self._node_position(building_id, j), new_building, j)
            bisect.insort(self.__node_line, node, key=self._node_key)
 
        # ตรวจใหม่ทุกคน เทียบอาคารเดิมกับที่วงแหวนใหม่ให้มา
        to_move = []
        for guest in self.__guests.values():
            target = self.find_building(*guest.id)
            if target is not guest.building:
                to_move.append((guest, target))
 
        # (c) เอาห้องออกจากอาคารเก่า → ใส่ห้องเข้าอาคารใหม่
        moves = self._relocate(to_move)
        return True, self._move_report("add", building_id, moves)
 
    def remove_building(self, building_id: int):
        if not self.__node_line:
            raise ValueError("Hotel has not been initialized.")
        if type(building_id) is not int or building_id < 0:
            raise ValueError("Building ID must be a non-negative integer.")
 
        building = self.__building.get(building_id)
        if building is None:
            return False, f"Building {building_id} not found."
        if len(self.__building) == 1:
            return False, "Cannot remove the last building (N must stay >= 1)."
 
        # ปรับวงแหวน
        self.__node_line = [
            n for n in self.__node_line if n.building is not building
        ]
        del self.__building[building_id]
 
        # หาแขกที่ต้องย้าย
        to_move = [
            (room.guest, self.find_building(*room.guest.id))
            for room in building.rooms
        ]
 
        #ย้ายและรายงาน
        moves = self._relocate(to_move)
        return True, self._move_report("remove", building_id, moves)
 
    def _relocate(self, to_move):
        """Move (guest, target) pairs; room_no never changes."""
        moves = []
        for guest, target in to_move:
            old = guest.building
            room = old.remove_room(guest.room_no)
            guest.building = target
            target.add_room(room)
            c, s = guest.id
            moves.append((c, s, old.id, target.id, guest.room_no))
        moves.sort()
        return moves
 
    def _move_report(self, action, building_id, moves):
        k = len(self.__guests)
        return {
            "action": action,
            "building_id": building_id,
            "guest_count": k,
            "moved_count": len(moves),
            "move_rate": len(moves) / k if k > 0 else None,
            "moves": tuple(moves),  # (c, s, old_building, new_building, room_no)
        } 
    
    def search_by_guest(self, channel_id: int, sequence_id: int):
        if type(channel_id) is not int or channel_id < 1:
            raise ValueError("Channel ID must be a positive integer.")
        if type(sequence_id) is not int or sequence_id < 1:
            raise ValueError("Sequence ID must be a positive integer.")
        
        guest = self.get_guest(channel_id,sequence_id)
        if guest is None:
            return False, f"Guest ({channel_id},{sequence_id}) not found."
        return True, (guest.building.id, guest.room_no)


    def search_by_room(self, node_id: int, room_no: int):
        if type(node_id) is not int or node_id < 0: #แก้จาก 1 เป็น 0 เพราะตอนแรกที่วน วนเริ่มจาก 0 แต่อันนี้เริ่มที่ 1 
            raise ValueError("Node ID must be a positive integer.")
        if type(room_no) is not int or room_no < 1:
            raise ValueError("Room ID must be a positive integer.")
        
        building = self.__building.get(node_id)
        if building is None:
            return False, f"Building {node_id} not found."
        
        room = building.get_room(room_no)
        if room is None:
            return False, f"Room {room_no} in building {node_id} not found."
        return True, room.guest.id

#แสดงรายการห้องที่มีผู้พัก เรียงตาม node_id จากน้อยไปมาก และเรียง room_no 
# แบบตัวเลขจากน้อยไปมากภายในแต่ละอาคาร
    def list_rooms(self):
        """Occupied rooms sorted by node_id, then room_no (both numeric).

        Returns a tuple of (node_id, room_no, channel_id, sequence_id).
        """
        rows = []
        for building_id in sorted(self.__building):
            building = self.__building[building_id]
            for room in sorted(building.rooms, key=lambda r: r.id):
                c, s = room.guest.id
                rows.append((building_id, room.id, c, s))
        return tuple(rows)

    @property
    def buildings(self):
        return tuple(self.__building.values())

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
        
        # ----- แก้จากของเพื่อน เป็นใช้ element id แทน ----
        # self.__channel_id = channel_id
        # self.__sequence_id = sequence_id
        self.__id = (channel_id,sequence_id)
        self.__building = building

        # Cantor pairing uses only the guest ID, never the building.
        a = channel_id - 1
        b = sequence_id - 1
        self.__room_no = ((a + b) * (a + b + 1)) // 2 + b + 1

    # @property
    # def id(self):
    #     return self.__channel_id, self.__sequence_id

    @property
    def id(self):
        return self.__id

    # @property
    # def channel_id(self):
    #     return self.__channel_id

    # @property
    # def sequence_id(self):
    #     return self.__sequence_id

    @property
    def building(self):
        return self.__building

    @property
    def room_no(self):
        return self.__room_no
    
    @building.setter
    def building(self, new_building):
        self.__building = new_building


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
    
    def remove_room(self, room_id: int):
        if room_id not in self.__rooms:
            raise ValueError("Room does not exist.")
        return self.__rooms.pop(room_id)

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
