import hashlib

class HotelSystem:
    def __init__(self):
        self.__building = []
        self.__max_node = int
        self.__node_line = []


    def _hash_position(self, text: str):
        data = text.encode("utf-8")
        result = hashlib.sha256(data).digest()
        return int.from_bytes(result[:8], "big")
    
    def init_setting(self, N, V):
        if type(N) is not int or N < 1:
            raise ValueError("N must be a positive integer.")
        if type(V) is not int or V < 1:
            raise ValueError("V must be a positive integer.")

        buildings = []
        node_line = []
        for i in range(N):
            building = Building(i)
            buildings.append(building)
            for j in range(V):
                node = Node(
                    self._hash_position(f"Build{i}:{j}"),
                    building,
                    j
                )
                node_line.append(node)

        node_line.sort(key=lambda n: (n.id, n.building.id, n.node_ind))
        self.__building = buildings
        self.__max_node = V
        self.__node_line = node_line
        return
        
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
        return
    
class Guest:
    def __init__(self):
        pass

class Building:
    def __init__(self,building_id: str):
        self.__building_id = building_id

    @property
    def id(self):
        return self.__building_id

    
class Node:
    def __init__(self, id: int, Building: object, node_ind: int):
        self.__building = Building
        self.__id = int(id)
        self.__node_ind = node_ind
        self.__room = None

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
    def __init__(self,room_id: int):
        self.__id = room_id

