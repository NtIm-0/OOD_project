import hashlib


class ModNHotel:
    def __init__(self, salt=""):
        self.__salt = str(salt)
        self.__order = []
        self.__place = {}

    # ---------------------------------------------------------------- #
    # Hashing
    # ---------------------------------------------------------------- #
    def _hash_position(self, text: str):
        data = f"{self.__salt}:{text}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(data).digest()[:8], "big")

    def find_building(self, channel_id: int, sequence_id: int):
        if not self.__order:
            raise ValueError("Hotel has not been initialized.")
        h = self._hash_position(f"guest:{channel_id}:{sequence_id}")
        return self.__order[h % len(self.__order)]

    @staticmethod
    def room_no(channel_id: int, sequence_id: int):
        a, b = channel_id - 1, sequence_id - 1
        return ((a + b) * (a + b + 1)) // 2 + b + 1

    # ---------------------------------------------------------------- #
    # Setup and guests
    # ---------------------------------------------------------------- #
    def init_setting(self, N: int, guests_per_channel: dict):
        if self.__order:
            raise ValueError("Hotel is already initialized.")
        if type(N) is not int or N < 1:
            raise ValueError("N must be a positive integer.")
        self.__order = list(range(N))
        for c, count in guests_per_channel.items():
            if count > 0:
                self.add_guest_batch(c, 1, count)

    def add_guest_batch(self, channel_id: int, s_start: int, count: int):
        ids = [(channel_id, s) for s in range(s_start, s_start + count)]
        for gid in ids:
            if gid in self.__place:
                return False, f"Batch denied: Guest {gid} already exist."
        for c, s in ids:
            self.__place[(c, s)] = self.find_building(c, s)
        return True, len(ids)

    # ---------------------------------------------------------------- #
    # Add / remove building
    # ---------------------------------------------------------------- #
    def add_building(self, building_id: int):
        if building_id in self.__order:
            return False, f"Building {building_id} already exists."
        self.__order.append(building_id)
        return True, self.__rebalance("add", building_id)

    def remove_building(self, building_id: int):
        if building_id not in self.__order:
            return False, f"Building {building_id} not found."
        if len(self.__order) == 1:
            return False, "Cannot remove the last building (N must stay >= 1)."
        self.__order.remove(building_id)          # keeps the order of the rest
        return True, self.__rebalance("remove", building_id)

    def __rebalance(self, action, building_id):
        """Recompute every guest; N changed, so almost everyone may move."""
        moves = []
        for (c, s), old in self.__place.items():
            new = self.find_building(c, s)
            if new != old:                         # compare real IDs
                moves.append((c, s, old, new, self.room_no(c, s)))
                self.__place[(c, s)] = new
        moves.sort()
        k = len(self.__place)
        return {
            "action": action,
            "building_id": building_id,
            "guest_count": k,
            "moved_count": len(moves),
            "move_rate": len(moves) / k if k > 0 else None,
            "moves": tuple(moves),   # (c, s, old_building, new_building, room_no)
        }

    @property
    def buildings(self):
        return tuple(self.__order)

    @property
    def guest_count(self):
        return len(self.__place)

    def building_of(self, channel_id: int, sequence_id: int):
        return self.__place.get((channel_id, sequence_id))