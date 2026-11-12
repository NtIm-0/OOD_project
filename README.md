# Distributed Hilbert's Hotel — Consistent Hashing

Object Oriented Data Structure project, semester 1/2569.

Guests are placed in buildings with consistent hashing (SHA-256 ring with
virtual nodes) and get a room number computed from their own ID (Cantor
pairing). Adding or removing a building moves only a small share of guests;
the program reports who moved and compares the result with `hash mod N`.

## Requirements

- **Python 3.10 or newer** (developed and tested on Python 3.14, Windows).
  3.10+ is needed because `bisect.insort(..., key=...)` is used.
- Standard library only for the program and tests.
- `matplotlib` only for drawing graphs: `pip install matplotlib`

## Files

| File | What it does |
|---|---|
| `hotel.py` | Core logic: `HotelSystem`, `Guest`, `Building`, `Node`, `Room` |
| `mod_n.py` | `ModNHotel`, the `hash mod N` method used for comparison |
| `export_csv.py` | Writes guests, move lists and load report as UTF-8 CSV |
| `main.py` | Text menu (user interface) |
| `measure.py` | Experiments A, B, C: time, memory, moves, balance → `results/*.csv` |
| `plots.py` | Draws the 3 required graphs from `results/*.csv` |
| `test_HotelSystem.py` | Automated tests for the core rules |
| `test_mod_n.py` | Tests for `hash mod N` |
| `test_export.py` | Tests for CSV export (row count = guest count) |
| `test_edge_cases.py` | Edge cases of section 4.5 and setup checks |

## Run the program

```
python main.py
```

1. Enter `N V`, e.g. `10 32`
2. Enter the number of channels, then the number of guests in each channel
3. Choose from the menu:

```
 1. Show state                           7. Search by guest (c, s)
 2. Add guest                            8. Search by room (node_id, room_no)
 3. Add guest batch                      9. List occupied rooms (sorted)
 4. Remove guest                        10. Load balance report
 5. Add building                        11. Export CSV (guests, load, last moves)
 6. Remove building                     12. Run experiments A/B/C and draw graphs
 0. Exit
```

Wrong input is refused with a message and the menu continues. Long lists show
the first 20 rows and the total; exported files always contain every row.
Option 11 writes to `output/`.

## Run the tests

```
python -m unittest test_HotelSystem test_mod_n test_export test_edge_cases -v
```

Expected: `Ran 63 tests ... OK`

## Run the experiments and graphs

```
python measure.py
python plots.py
```

`measure.py` takes about 30 seconds and writes to `results/`:

| File | Content |
|---|---|
| `exp_A.csv` | Time and memory vs K = 1,000 / 10,000 / 100,000 (N = 10, V = 32) |
| `exp_B.csv` | Moves when adding/removing 1 building, consistent hashing vs hash mod N, N = 5 / 10 / 20 (K = 10,000, V = 32) |
| `exp_C.csv` | CV, max, min and memory vs V = 1 / 8 / 32 (N = 10, K = 10,000) |
| `exp_C_loads.csv` | Guests in every building, for each V and salt |
| `guests_sample_N10_V32_K10000_salt0.csv` | Sample guest data: channel_id, sequence_id, node_id, room_no |
| `moves_*.csv` | Example move lists (N = 10, salt 0) for both methods |
| `run_info.txt` | Python version, machine, salts and parameters |
| `figures/*.png` | Graphs (a) time vs K, (b) move rate vs N, (c) effect of V |

Every setting runs 3 times with salt `0`, `1`, `2` (hash text becomes
`"<salt>:<text>"`). Both methods use the same salt, guest IDs and building IDs
in the same round. Time uses `time.perf_counter()`; memory uses `tracemalloc`
in separate runs and is memory tracked by Python, not the whole process.
Reported values are the median of the 3 runs with the min–max range.

## Main rules (summary)

- Ring positions: SHA-256 of UTF-8 text, first 8 bytes as a big-endian
  64-bit integer. Node text `node:<building_id>:<j>`, guest text `guest:<c>:<s>`.
- A guest goes to the first point with position ≥ the guest's position,
  wrapping to the start. Ties are ordered by `(position, building_id, j)`.
- `room_no = ((a+b)(a+b+1))//2 + b + 1` with `a = c−1`, `b = s−1`; it never
  changes when a guest moves building.
- Adding a building inserts only its V points; removing one deletes only its
  points. The last building cannot be removed.