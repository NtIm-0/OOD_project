"""Export hotel data to UTF-8 CSV files (project section 5, item 10).

Kept apart from hotel.py so the core logic never touches files.
Every function returns the number of data rows written (header not counted).
"""
import csv
import os


def _open(path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    return open(path, "w", newline="", encoding="utf-8")


def export_guests(hotel, path):
    """One row per guest: channel_id, sequence_id, node_id, room_no.

    Rows follow list_rooms(): node_id ascending, then room_no ascending.
    """
    rows = hotel.list_rooms()                 # (node_id, room_no, c, s)
    with _open(path) as f:
        writer = csv.writer(f)
        writer.writerow(["channel_id", "sequence_id", "node_id", "room_no"])
        for node_id, room_no, c, s in rows:
            writer.writerow([c, s, node_id, room_no])
    return len(rows)


def export_moves(report, path):
    """Move list from add_building / remove_building."""
    moves = report["moves"]                   # (c, s, old, new, room_no)
    with _open(path) as f:
        writer = csv.writer(f)
        writer.writerow(["channel_id", "sequence_id", "old_node_id",
                         "new_node_id", "room_no"])
        writer.writerows(moves)
    return len(moves)


def export_load_report(hotel, path):
    """Guests per building, then the summary statistics."""
    rep = hotel.load_report()
    with _open(path) as f:
        writer = csv.writer(f)
        writer.writerow(["node_id", "guests"])
        for node_id, count in rep["guests_per_building"].items():
            writer.writerow([node_id, count])
        writer.writerow([])
        writer.writerow(["statistic", "value"])
        for key in ("max", "min", "mean", "std", "cv"):
            value = rep[key]
            writer.writerow([key, "not calculated" if value is None else value])
        if rep.get("note"):
            writer.writerow(["note", rep["note"]])
    return len(rep["guests_per_building"])