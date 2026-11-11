"""Tests for the hash mod N comparison class.

Run:  python -m unittest test_mod_n -v
"""
import unittest

from mod_n import ModNHotel


def make(N=5, K=2000, salt=0):
    hotel = ModNHotel(salt)
    hotel.init_setting(N, {1: K // 2, 2: K - K // 2})
    return hotel


def snapshot(hotel, K=2000):
    ids = [(1, s) for s in range(1, K // 2 + 1)] + \
          [(2, s) for s in range(1, K - K // 2 + 1)]
    return {g: hotel.building_of(*g) for g in ids}


class TestModN(unittest.TestCase):
    def test_index_is_hash_mod_n(self):
        hotel = make(N=7)
        h = hotel._hash_position("guest:1:5")
        self.assertEqual(hotel.building_of(1, 5), hotel.buildings[h % 7])

    def test_same_salt_same_result(self):
        self.assertEqual(snapshot(make(salt=1)), snapshot(make(salt=1)))
        self.assertNotEqual(snapshot(make(salt=1)), snapshot(make(salt=2)))

    def test_add_appends_and_reports_real_ids(self):
        hotel = make(N=5)
        before = snapshot(hotel)
        ok, rep = hotel.add_building(42)
        self.assertTrue(ok)
        self.assertEqual(hotel.buildings, (0, 1, 2, 3, 4, 42))
        after = snapshot(hotel)
        moved = {g for g in before if before[g] != after[g]}
        self.assertEqual(rep["moved_count"], len(moved))
        self.assertEqual(len(rep["moves"]), rep["moved_count"])
        for c, s, old, new, room in rep["moves"]:
            self.assertEqual(old, before[(c, s)])
            self.assertEqual(new, after[(c, s)])
            self.assertEqual(room, ModNHotel.room_no(c, s))

    def test_remove_keeps_order(self):
        hotel = make(N=5)
        hotel.remove_building(2)
        self.assertEqual(hotel.buildings, (0, 1, 3, 4))

    def test_mod_n_moves_most_guests(self):
        hotel = make(N=10)
        ok, rep = hotel.add_building(10)
        self.assertGreater(rep["move_rate"], 0.8)   # expected about N/(N+1)

    def test_edge_cases(self):
        hotel = make(N=1, K=10)
        self.assertFalse(hotel.add_building(0)[0])     # duplicate
        self.assertFalse(hotel.remove_building(9)[0])  # not found
        self.assertFalse(hotel.remove_building(0)[0])  # last building
        self.assertEqual(hotel.guest_count, 10)

    def test_no_guests(self):
        hotel = ModNHotel(0)
        hotel.init_setting(3, {})
        ok, rep = hotel.add_building(3)
        self.assertEqual(rep["moved_count"], 0)
        self.assertIsNone(rep["move_rate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)