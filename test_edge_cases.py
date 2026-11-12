"""Extra edge cases from section 4.5 and setup rules (section 5 item 1).

Run:  python -m unittest test_edge_cases -v
"""
import unittest

from hotel import HotelSystem


def snapshot(hotel):
    return ({g.id: (g.building.id, g.room_no) for g in hotel.guests},
            hotel.node_count, hotel.building_count)


class TestSetup(unittest.TestCase):
    def test_bad_settings_refused(self):
        for N, V, guests in [(0, 4, {}), (3, 0, {}), (-1, 4, {}),
                             (3, 4, {0: 5}), (3, 4, {1: -2}), ("3", 4, {})]:
            with self.subTest(N=N, V=V, guests=guests):
                hotel = HotelSystem()
                with self.assertRaises(ValueError):
                    hotel.init_setting(N, V, guests)
                self.assertEqual(hotel.node_count, 0)     # nothing half-built

    def test_init_twice_refused_and_data_kept(self):
        hotel = HotelSystem()
        hotel.init_setting(3, 4, {1: 5})
        before = snapshot(hotel)
        with self.assertRaises(ValueError):
            hotel.init_setting(3, 4, {1: 5})
        self.assertEqual(snapshot(hotel), before)

    def test_sequence_starts_at_1(self):
        hotel = HotelSystem()
        hotel.init_setting(2, 4, {1: 3, 2: 2})
        self.assertEqual(sorted(g.id for g in hotel.guests),
                         [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2)])

    def test_channel_count_ignores_empty_channels(self):
        hotel = HotelSystem()
        hotel.init_setting(2, 4, {1: 2, 2: 0, 3: 0})
        self.assertEqual(hotel.channel_count, 1)
        hotel.add_guest(5, 1)
        self.assertEqual(hotel.channel_count, 2)
        hotel.remove_guest(5, 1)
        self.assertEqual(hotel.channel_count, 1)


class TestEdgeCasesKeepData(unittest.TestCase):

    def setUp(self):
        self.hotel = HotelSystem()
        self.hotel.init_setting(2, 4, {1: 10, 2: 10})

    def check_refused(self, result):
        ok, reason = result
        self.assertFalse(ok)
        self.assertIsInstance(reason, str)
        self.assertTrue(reason)

    def test_each_refusal_keeps_data(self):
        h = self.hotel
        before = snapshot(h)
        self.check_refused(h.add_building(0))          # building ID already used
        self.check_refused(h.remove_building(77))      # building does not exist
        self.check_refused(h.add_guest(1, 1))          # guest ID already used
        self.check_refused(h.add_guest_batch(2, 9, 5)) # batch overlaps (2, 9), (2, 10)
        self.check_refused(h.remove_guest(9, 9))       # guest does not exist
        self.check_refused(h.search_by_guest(9, 9))    # not found
        self.check_refused(h.search_by_room(0, 10**6))  # room not found
        self.check_refused(h.search_by_room(55, 1))    # building not found
        self.assertEqual(snapshot(h), before)

    def test_remove_last_building_without_guests(self):
        hotel = HotelSystem()
        hotel.init_setting(1, 4, {})
        self.check_refused(hotel.remove_building(0))
        self.assertEqual(hotel.node_count, 4)
        self.assertTrue(hotel.add_guest(1, 1)[0])      # ring still usable

    def test_remove_down_to_one_then_refuse(self):
        h = self.hotel
        self.assertTrue(h.remove_building(0)[0])
        before = snapshot(h)
        self.check_refused(h.remove_building(1))
        self.assertEqual(snapshot(h), before)
        self.assertTrue(all(g.building.id == 1 for g in h.guests))

    def test_readd_removed_guest_uses_current_ring(self):
        h = self.hotel
        h.remove_guest(1, 1)
        h.add_building(5)
        ok, g = h.add_guest(1, 1)
        self.assertTrue(ok)
        self.assertIs(g.building, h.find_building(1, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)