"""Tests for CSV export (section 5 item 10 and section 9.2 item 6).

Run:  python -m unittest test_export -v
"""
import csv
import os
import tempfile
import unittest

from hotel import HotelSystem
from export_csv import export_guests, export_moves, export_load_report


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


class TestExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_guest_rows_equal_guest_count(self):
        hotel = HotelSystem()
        hotel.init_setting(5, 8, {c: 37 for c in range(1, 6)})
        hotel.add_guest(9, 9)
        hotel.remove_guest(1, 1)
        n = export_guests(hotel, self.path("guests.csv"))
        rows = read_csv(self.path("guests.csv"))
        self.assertEqual(rows[0], ["channel_id", "sequence_id", "node_id", "room_no"])
        self.assertEqual(n, hotel.guest_count)
        self.assertEqual(len(rows) - 1, hotel.guest_count)   # minus header

    def test_guest_rows_match_search(self):
        hotel = HotelSystem()
        hotel.init_setting(3, 4, {1: 20, 2: 20})
        export_guests(hotel, self.path("guests.csv"))
        for c, s, node, room in read_csv(self.path("guests.csv"))[1:]:
            self.assertEqual(hotel.search_by_guest(int(c), int(s)),
                             (True, (int(node), int(room))))

    def test_rows_after_moving_buildings(self):
        hotel = HotelSystem()
        hotel.init_setting(4, 8, {1: 300, 2: 300})
        hotel.add_building(7)
        hotel.remove_building(0)
        export_guests(hotel, self.path("guests.csv"))
        self.assertEqual(len(read_csv(self.path("guests.csv"))) - 1, hotel.guest_count)

    def test_empty_hotel_writes_header_only(self):
        hotel = HotelSystem()
        hotel.init_setting(2, 2, {})
        self.assertEqual(export_guests(hotel, self.path("g.csv")), 0)
        self.assertEqual(len(read_csv(self.path("g.csv"))), 1)

    def test_move_rows_equal_moved_count(self):
        hotel = HotelSystem()
        hotel.init_setting(4, 8, {1: 300, 2: 300})
        ok, rep = hotel.add_building(9)
        n = export_moves(rep, self.path("moves.csv"))
        rows = read_csv(self.path("moves.csv"))
        self.assertEqual(n, rep["moved_count"])
        self.assertEqual(len(rows) - 1, rep["moved_count"])
        for c, s, old, new, room in rows[1:]:
            self.assertEqual(int(new), 9)

    def test_load_report_lists_every_building(self):
        hotel = HotelSystem()
        hotel.init_setting(4, 4, {})
        self.assertEqual(export_load_report(hotel, self.path("load.csv")), 4)
        with open(self.path("load.csv"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("not calculated", text)          # K = 0: no CV

    def test_creates_missing_folder(self):
        hotel = HotelSystem()
        hotel.init_setting(2, 2, {1: 3})
        export_guests(hotel, self.path(os.path.join("new", "g.csv")))
        self.assertTrue(os.path.exists(self.path(os.path.join("new", "g.csv"))))


if __name__ == "__main__":
    unittest.main(verbosity=2)