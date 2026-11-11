"""Automated tests for HotelSystem (hotel.py) and the display code in main.py.

Run:  python -m unittest test_HotelSystem -v
Requires Python 3.10+ (bisect.insort with key).
"""
import io
import unittest
from contextlib import redirect_stdout

from hotel import HotelSystem, Guest, Building, Node, Room


def make_hotel(N=3, V=4, guests=None):
    hotel = HotelSystem()
    hotel.init_setting(N, V, guests if guests is not None else {1: 20, 2: 20})
    return hotel


def address_book(hotel):
    """Snapshot {guest_id: (building_id, room_no)} of every guest."""
    return {g.id: (g.building.id, g.room_no) for g in hotel.guests}


def make_small_ring(positions):
    """Build a hotel whose ring uses hand-picked positions (section 9.1).

    positions: list of (position, building_id, j)
    Writes the private list directly (name mangling) only for testing.
    """
    hotel = HotelSystem()
    buildings = {}
    nodes = []
    for pos, b_id, j in positions:
        b = buildings.setdefault(b_id, Building(b_id))
        nodes.append(Node(pos, b, j))
    nodes.sort(key=lambda n: (n.id, n.building.id, n.node_ind))
    hotel._HotelSystem__node_line = nodes
    return hotel


# ---------------------------------------------------------------- #
# 1) Hash
# ---------------------------------------------------------------- #
class TestHash(unittest.TestCase):
    def test_hash_is_stable_and_64_bit(self):
        h = HotelSystem()
        a = h._hash_position("guest:1:1")
        b = HotelSystem()._hash_position("guest:1:1")
        self.assertEqual(a, b)               # same text -> same position
        self.assertTrue(0 <= a < 2**64)       # inside the 64-bit ring

    def test_known_value(self):
        # Fixed expected value: proves it does not change between runs.
        import hashlib
        expect = int.from_bytes(
            hashlib.sha256(b"guest:1:1").digest()[:8], "big")
        self.assertEqual(HotelSystem()._hash_position("guest:1:1"), expect)


# ---------------------------------------------------------------- #
# 2) Room number (Cantor pairing)
# ---------------------------------------------------------------- #
class TestRoomNumber(unittest.TestCase):
    def test_table_from_spec(self):
        table = {(1, 1): 1, (2, 1): 2, (1, 2): 3, (3, 1): 4, (2, 2): 5}
        for (c, s), expect in table.items():
            self.assertEqual(Guest(c, s, None).room_no, expect)

    def test_room_numbers_unique(self):
        seen = set()
        for c in range(1, 101):
            for s in range(1, 101):
                r = Guest(c, s, None).room_no
                self.assertNotIn(r, seen)
                seen.add(r)

    def test_room_must_match_guest(self):
        g = Guest(1, 1, None)
        with self.assertRaises(ValueError):
            Room(99, g)


# ---------------------------------------------------------------- #
# 3) Ring and find_node (section 9.1 small ring, size 100, V = 1)
# ---------------------------------------------------------------- #
class TestRing(unittest.TestCase):
    def test_ring_size_and_sorted(self):
        hotel = make_hotel(N=5, V=8)
        self.assertEqual(hotel.node_count, 40)
        keys = [(n.id, n.building.id, n.node_ind) for n in hotel.node_line]
        self.assertEqual(keys, sorted(keys))

    def test_small_ring_from_spec(self):
        A, B, C = 1, 2, 3
        hotel = make_small_ring([(20, A, 0), (50, B, 0), (80, C, 0)])
        expect = {10: A, 20: A, 25: B, 35: B, 50: B, 70: C, 90: A}
        for pos, b in expect.items():
            self.assertEqual(hotel.find_node(pos).building.id, b, f"pos {pos}")

    def test_exact_point_between_and_wrap(self):
        hotel = make_small_ring([(20, 1, 0), (50, 2, 0)])
        self.assertEqual(hotel.find_node(20).building.id, 1)   # exactly on point
        self.assertEqual(hotel.find_node(21).building.id, 2)   # between points
        self.assertEqual(hotel.find_node(51).building.id, 1)   # after last -> wrap
        self.assertEqual(hotel.find_node(2**64 - 1).building.id, 1)

    def test_collision_uses_smallest_key(self):
        # Two points at the same position: (50, 2, 0) must win over (50, 7, 0)
        hotel = make_small_ring([(50, 7, 0), (50, 2, 0), (90, 3, 0)])
        self.assertEqual(hotel.find_node(40).building.id, 2)
        self.assertEqual(hotel.node_count, 3)      # both points kept

    def test_push_node_keeps_order(self):
        hotel = make_small_ring([(20, 1, 0), (80, 3, 0)])
        hotel.push_node(Node(50, Building(2), 0))
        self.assertEqual([n.id for n in hotel.node_line], [20, 50, 80])

    def test_guest_building_matches_ring(self):
        hotel = make_hotel()
        for g in hotel.guests:
            self.assertIs(hotel.find_building(*g.id), g.building)

    def test_empty_ring_raises(self):
        with self.assertRaises(ValueError):
            HotelSystem().find_node(5)


# ---------------------------------------------------------------- #
# 4) Add / remove guest
# ---------------------------------------------------------------- #
class TestGuests(unittest.TestCase):
    def test_init_counts(self):
        hotel = make_hotel(guests={1: 10, 2: 5})
        self.assertEqual(hotel.guest_count, 15)
        self.assertEqual(sum(b.guest_count for b in hotel.buildings), 15)

    def test_new_guest_does_not_move_old_guests(self):
        hotel = make_hotel()
        before = address_book(hotel)
        hotel.add_guest(1, 999)            # old channel
        hotel.add_guest(50, 1)             # new channel
        hotel.add_guest_batch(60, 1, 30)   # new channel, batch
        after = address_book(hotel)
        for gid, addr in before.items():
            self.assertEqual(after[gid], addr)

    def test_duplicate_guest_rejected(self):
        hotel = make_hotel()
        before = address_book(hotel)
        ok, _ = hotel.add_guest(1, 1)
        self.assertFalse(ok)
        self.assertEqual(address_book(hotel), before)

    def test_batch_partial_overlap_rejected(self):
        hotel = make_hotel(guests={1: 20})
        before = address_book(hotel)
        ok, _ = hotel.add_guest_batch(1, 15, 10)   # 15..24 overlaps 15..20
        self.assertFalse(ok)
        self.assertEqual(address_book(hotel), before)
        self.assertIsNone(hotel.get_guest(1, 21))   # nothing half-added

    def test_batch_zero(self):
        hotel = make_hotel()
        before = address_book(hotel)
        self.assertEqual(hotel.add_guest_batch(1, 100, 0), (True, ()))
        self.assertEqual(address_book(hotel), before)

    def test_remove_missing_guest(self):
        hotel = make_hotel()
        count = hotel.guest_count
        ok, _ = hotel.remove_guest(99, 99)
        self.assertFalse(ok)
        self.assertEqual(hotel.guest_count, count)

    def test_remove_then_readd(self):
        hotel = make_hotel()
        ok, g = hotel.remove_guest(1, 1)
        self.assertTrue(ok)
        self.assertIsNone(g.building.get_room(g.room_no))
        ok, g2 = hotel.add_guest(1, 1)
        self.assertTrue(ok)
        self.assertEqual(g2.room_no, g.room_no)

    def test_invalid_id_raises(self):
        hotel = make_hotel()
        with self.assertRaises(ValueError):
            hotel.add_guest(0, 1)
        with self.assertRaises(ValueError):
            hotel.add_guest_batch(1, 1, -1)


# ---------------------------------------------------------------- #
# 5) Search
# ---------------------------------------------------------------- #
class TestSearch(unittest.TestCase):
    def test_search_by_guest(self):
        hotel = make_hotel()
        g = hotel.get_guest(1, 1)
        self.assertEqual(hotel.search_by_guest(1, 1),
                         (True, (g.building.id, g.room_no)))
        self.assertFalse(hotel.search_by_guest(77, 77)[0])

    def test_search_round_trip_all_guests(self):
        """Every guest can be found again from (building, room), incl. building 0."""
        hotel = make_hotel()
        for g in hotel.guests:
            ok, (b, r) = hotel.search_by_guest(*g.id)
            self.assertEqual(hotel.search_by_room(b, r), (True, g.id))


# ---------------------------------------------------------------- #
# 6) Add / remove building
# ---------------------------------------------------------------- #
class FixedRingHotel(HotelSystem):
    """Hotel whose hash returns hand-picked positions (section 9.1)."""
    def __init__(self, table):
        super().__init__()
        self.table = table

    def _hash_position(self, text):
        return self.table[text]


def spec_ring():
    # A=0 at 20, B=1 at 50, C=2 at 80, D=3 at 35 (only used after add)
    table = {"node:0:0": 20, "node:1:0": 50, "node:2:0": 80, "node:3:0": 35}
    for s, pos in enumerate([10, 20, 25, 35, 50, 70, 90], start=1):
        table[f"guest:1:{s}"] = pos
    hotel = FixedRingHotel(table)
    hotel.init_setting(3, 1, {1: 7})
    return hotel


def check_consistent(test, hotel):
    """Every guest sits where the current ring says, and both indexes agree."""
    for g in hotel.guests:
        test.assertIs(hotel.find_building(*g.id), g.building)
        ok, (b, r) = hotel.search_by_guest(*g.id)
        test.assertEqual(hotel.search_by_room(b, r), (True, g.id))
    test.assertEqual(sum(b.guest_count for b in hotel.buildings),
                     hotel.guest_count)


class TestBuildings(unittest.TestCase):
    def test_spec_example_add_D(self):
        hotel = spec_ring()
        ok, rep = hotel.add_building(3)
        self.assertTrue(ok)
        self.assertEqual(rep["moved_count"], 2)
        self.assertEqual([(m[2], m[3]) for m in rep["moves"]], [(1, 3), (1, 3)])
        self.assertEqual(sorted(m[1] for m in rep["moves"]), [3, 4])

    def test_spec_example_remove_B(self):
        hotel = spec_ring()
        ok, rep = hotel.remove_building(1)
        self.assertTrue(ok)
        self.assertEqual(rep["moved_count"], 3)
        self.assertTrue(all(m[2] == 1 and m[3] == 2 for m in rep["moves"]))

    def test_add_rules_with_V_gt_1(self):
        hotel = make_hotel(N=5, V=16, guests={c: 400 for c in range(1, 6)})
        before = address_book(hotel)
        ok, rep = hotel.add_building(99)
        after = address_book(hotel)
        moved = {gid for gid in before if before[gid][0] != after[gid][0]}
        self.assertEqual(len(moved), rep["moved_count"])
        self.assertEqual(len(rep["moves"]), rep["moved_count"])
        for gid in moved:
            self.assertEqual(after[gid][0], 99)              # only into new one
            self.assertEqual(after[gid][1], before[gid][1])  # room_no kept
        self.assertEqual(hotel.guest_count, len(before))
        self.assertEqual(hotel.node_count, 6 * 16)
        self.assertGreater(rep["moved_count"], 0)
        check_consistent(self, hotel)

    def test_remove_rules_with_V_gt_1(self):
        hotel = make_hotel(N=5, V=16, guests={c: 400 for c in range(1, 6)})
        before = address_book(hotel)
        ok, rep = hotel.remove_building(2)
        after = address_book(hotel)
        for gid, (b, r) in before.items():
            if b != 2:
                self.assertEqual(after[gid], (b, r))  # others do not move
            else:
                self.assertNotEqual(after[gid][0], 2)
                self.assertEqual(after[gid][1], r)
        self.assertEqual(rep["moved_count"],
                         sum(1 for b, _ in before.values() if b == 2))
        self.assertEqual(hotel.node_count, 4 * 16)
        check_consistent(self, hotel)

    def test_add_then_remove_returns_to_start(self):
        hotel = make_hotel(N=4, V=8, guests={1: 300, 2: 300})
        before = address_book(hotel)
        hotel.add_building(10)
        hotel.remove_building(10)
        self.assertEqual(address_book(hotel), before)

    def test_edge_cases(self):
        hotel = make_hotel(N=2, V=4)
        snap = address_book(hotel)
        self.assertFalse(hotel.add_building(0)[0])      # duplicate id
        self.assertEqual(hotel.node_count, 8)
        self.assertFalse(hotel.remove_building(42)[0])  # not found
        self.assertTrue(hotel.remove_building(0)[0])
        self.assertFalse(hotel.remove_building(1)[0])   # last building
        self.assertEqual(hotel.building_count, 1)
        self.assertEqual(hotel.guest_count, len(snap))

    def test_no_guests(self):
        hotel = make_hotel(N=3, V=4, guests={})
        ok, rep = hotel.add_building(7)
        self.assertEqual(rep["moved_count"], 0)
        self.assertIsNone(rep["move_rate"])


# ---------------------------------------------------------------- #
# 7) Search and room list
# ---------------------------------------------------------------- #
class TestSearchAndList(unittest.TestCase):
    def test_not_found_messages(self):
        hotel = make_hotel()
        self.assertFalse(hotel.search_by_guest(99, 99)[0])
        self.assertFalse(hotel.search_by_room(77, 1)[0])        # no building
        self.assertFalse(hotel.search_by_room(0, 10**9)[0])     # no room

    def test_search_building_zero(self):
        hotel = make_hotel(N=3, V=8, guests={c: 50 for c in range(1, 6)})
        b0 = [g for g in hotel.guests if g.building.id == 0]
        self.assertTrue(b0)
        g = b0[0]
        self.assertEqual(hotel.search_by_room(0, g.room_no), (True, g.id))

    def test_search_after_move(self):
        hotel = make_hotel(N=4, V=8, guests={1: 300, 2: 300})
        ok, rep = hotel.add_building(9)
        c, s, old, new, room = rep["moves"][0]
        self.assertEqual(hotel.search_by_guest(c, s), (True, (new, room)))
        self.assertEqual(hotel.search_by_room(new, room), (True, (c, s)))
        self.assertFalse(hotel.search_by_room(old, room)[0])

    def test_list_rooms_sorted_and_complete(self):
        hotel = make_hotel(N=5, V=8, guests={c: 40 for c in range(1, 8)})
        rows = hotel.list_rooms()
        self.assertEqual(len(rows), hotel.guest_count)
        keys = [(b, r) for b, r, _, _ in rows]
        self.assertEqual(keys, sorted(keys))          # numeric, not text
        self.assertEqual(len(set(keys)), len(keys))   # no duplicate address
        for b, r, c, s in rows:
            self.assertEqual(hotel.search_by_room(b, r), (True, (c, s)))

    def test_list_rooms_numeric_order(self):
        hotel = make_hotel(N=1, V=1, guests={1: 12})
        rooms = [r for _, r, _, _ in hotel.list_rooms()]
        self.assertEqual(rooms, sorted(rooms))
        self.assertLess(rooms.index(3), rooms.index(10))  # 3 before 10

    def test_list_rooms_empty(self):
        self.assertEqual(make_hotel(guests={}).list_rooms(), ())


# ---------------------------------------------------------------- #
# 8) Load balance statistics
# ---------------------------------------------------------------- #
class TestLoadStats(unittest.TestCase):
    def test_values_match_statistics_module(self):
        import statistics
        hotel = make_hotel(N=6, V=8, guests={c: 100 for c in range(1, 6)})
        st = hotel.load_stats()
        values = [n for _, n in st["counts"]]
        self.assertEqual(len(values), 6)              # every building listed
        self.assertEqual(sum(values), hotel.guest_count)
        self.assertEqual(st["max"], max(values))
        self.assertEqual(st["min"], min(values))
        self.assertAlmostEqual(st["mean"], statistics.mean(values))
        self.assertAlmostEqual(st["std"], statistics.pstdev(values))
        self.assertAlmostEqual(st["cv"], st["std"] / st["mean"])

    def test_includes_empty_building(self):
        hotel = make_hotel(N=3, V=4, guests={1: 5})
        hotel.add_building(50)
        for g in [g for g in hotel.guests if g.building.id == 50]:
            hotel.remove_guest(*g.id)
        counts = dict(hotel.load_stats()["counts"])
        self.assertIn(50, counts)
        self.assertEqual(counts[50], 0)
        self.assertEqual(hotel.load_stats()["min"], 0)

    def test_sorted_by_building_id(self):
        hotel = make_hotel(N=3, V=4)
        hotel.add_building(10)
        hotel.add_building(5)
        ids = [b for b, _ in hotel.load_stats()["counts"]]
        self.assertEqual(ids, sorted(ids))

    def test_no_guests(self):
        st = make_hotel(N=4, V=4, guests={}).load_stats()
        self.assertEqual((st["max"], st["min"], st["mean"], st["std"]), (0, 0, 0, 0))
        self.assertIsNone(st["cv"])
        self.assertEqual(len(st["counts"]), 4)

    def test_more_vnodes_more_balanced(self):
        guests = {c: 1000 for c in range(1, 11)}
        cv1 = make_hotel(N=10, V=1, guests=guests).load_stats()["cv"]
        cv32 = make_hotel(N=10, V=32, guests=guests).load_stats()["cv"]
        self.assertLess(cv32, cv1)


# ---------------------------------------------------------------- #
# 9) main.py display
# ---------------------------------------------------------------- #
class TestMainDisplay(unittest.TestCase):
    def test_show_initial_state(self):
        """show_initial_state runs without crashing."""
        from main import show_initial_state
        with redirect_stdout(io.StringIO()):
            show_initial_state(make_hotel())


if __name__ == "__main__":
    unittest.main(verbosity=2)