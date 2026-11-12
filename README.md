# Rubik's Cube Scanner & Solver

Point a webcam at a scrambled Rubik's Cube, scan its six faces, and get a step-by-step solution you can follow with the cube in your hands. Choose between the **fastest possible solve** (Kociemba's two-phase algorithm) or a **beginner walkthrough** from a layer-by-layer solver I wrote from scratch.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![OpenCV](https://img.shields.io/badge/OpenCV-computer%20vision-green)

<!-- TODO: add a demo GIF or screenshots, e.g. docs/demo.gif, docs/scanner.png, docs/walkthrough.png -->

## How this was built

| File | What it is | How it was made |
|---|---|---|
| `jspSolver.py` | A complete beginner-method Rubik's Cube solver (~1,300 lines, pure Python, no dependencies) | **Written entirely by hand. No AI assistants or code-generation tools were used.** |
| `rubiks_solver.py` | Webcam scanner, colour classifier, correction screen, solver menu and step-by-step viewer | Built with help from an AI assistant (Claude). I specified the features and behaviour, and iterated on the results. |

I wanted the core algorithmic work to be entirely my own, and to use AI where it saves time on the surrounding application code (OpenCV windows, parsing, layout). I'm happy to walk through any part of `jspSolver.py` in detail.

## Features

- **Webcam scanning** of all six faces with a live grid overlay and a mirrored preview
- **Lighting-robust colour detection**: sticker colours are matched to the cube's own centre pieces in LAB colour space, so no fixed colour calibration is needed
- **Correction screen**: an unfolded view of the cube where you can click any sticker to fix a misread colour, or rotate a mis-oriented face
- **Two solvers behind one menu**: fastest solve (Kociemba) or beginner walkthrough (`jspSolver`)
- **Guided walkthrough** with named algorithms ("right sexy", "sune", "F2L algorithm left"), per-step directions, whole-cube rotation help, and a list of which pieces are still wrong at each stage
- **Notation guide** linked from the solution screen: [jperm.net/3x3/moves](https://jperm.net/3x3/moves)

## Quick start

```bash
pip install opencv-python numpy kociemba
python rubiks_solver.py              # default webcam
python rubiks_solver.py --camera 1   # a different camera
python rubiks_solver.py --no-mirror  # raw, un-mirrored preview
```

Requires Python 3.10 or newer (`jspSolver.py` uses `match` statements and modern type hints). Keep `jspSolver.py` in the same folder as `rubiks_solver.py`.

### Using the solver on its own

```python
import jspSolver

facelets = jspSolver.scramble("R U R' U' F2 D L'")   # or a 54-character facelet string from a real cube
print(jspSolver.solve(facelets))
```

## Using the app

1. **Scan.** Hold the cube with **white on top and green in front**, line a face up with the on-screen grid and press `SPACE`. The app tells you how to turn the cube for each of the six faces (front, right, back, left, top, bottom).
2. **Review.** Check the unfolded cube. Click a sticker to cycle its colour, or press a face letter (`U R F D L B`) to rotate that face. Every colour must appear exactly 9 times before you can continue.
3. **Choose a method.** Press `ENTER`, then `1` for the fastest solve or `2` for the beginner walkthrough.
4. **Follow along.** Step through the solution one move (or algorithm) at a time.

| Screen | Keys |
|---|---|
| Scanner | `SPACE` capture, `B` back, `M` mirror on/off, `Q` quit |
| Review | click = recolour, `U/R/F/D/L/B` = rotate that face, `ENTER` = solve |
| Method menu | `1` fastest, `2` beginner walkthrough, `B` back |
| Solution | `N` / `SPACE` next, `P` previous, `O` open notation guide, `Q` quit |

<!-- TODO: add a screenshot of the review screen and the walkthrough screen -->

## How it works

### 1. Reading the cube (computer vision)

- Each sticker's colour is the **median** of a small patch after a Gaussian blur, which ignores glare spots and sensor noise.
- Colours are compared in **LAB space** with lightness down-weighted, so shadows and bright spots matter less than the actual hue.
- Instead of hard-coded colour ranges, each sticker is assigned to whichever of the six **centre pieces** it is closest to. Centres never move on a real cube, so this works with any lighting and any colour scheme.
- The live preview is mirrored like a real mirror, but colours are always sampled from the raw frame and the on-screen swatches are remapped to match, so faces are stored exactly as they look from outside the cube.
- The result is a 54-character facelet string in `URFDLB` order, the same convention the `kociemba` library uses.

### 2. The beginner solver, `jspSolver.py` (hand-written)

The cube is stored as a flat list of 54 facelets. Everything is built on top of index tables (`edges`, `corners`, `centers`, `faces`, `layers`) and one small helper, `triangulate()`, which finds the squares shared by several lists. Intersecting two layers gives an edge, intersecting three gives a corner, and swapping a layer for a face gives a single square. That one idea is used to locate and check every piece.

Core pieces:

- `turn()` implements all face turns (`U D R L F B` with `'` and `2`) as index permutations. A single clockwise turn is coded once, and primes and half-turns repeat it 3 or 2 times.
- `sexy()`, `algorithm()` and `scramble()` perform and record named algorithms and generate test cubes.
- `pieceSolved()` and `correctSpot()` tell apart a piece that is *solved* from one that is merely *in the right spot but twisted*.

The solve runs the standard layer-by-layer method in eight stages, one per output line:

| # | Stage | `jspSolver` function | What it does |
|---|---|---|---|
| 1 | Daisy | `daisy()` | Brings all four white edges around the yellow centre, without disturbing petals already placed |
| 2 | Cross | `cross()` | Lines each white edge up with its centre and half-turns it into place |
| 3 | First layer | `firstLayer()` | Inserts each white corner by repeating a sexy move until it drops in |
| 4 | Second layer | `secondLayer()` | Works out the turns needed to line up each middle edge, then inserts it left or right (and frees edges stuck in the wrong slot) |
| 5 | Yellow cross | `yellowCross()` | Repeats `F L D L' D' F'` until the yellow edges form a cross |
| 6 | Orient edges | `orientEdges()` | Uses a sune to match the yellow edges with their side centres |
| 7 | Orient corners | `orientCorners()` | Repeats the corners algorithm until every yellow corner is in the right spot |
| 8 | Turn corners | `turnCorners()` | Twists the last corners into place with repeated sexy moves |

**Making the output human-friendly.** Internally, the solver always works with yellow on the bottom, which keeps the logic simple. A post-processing step then rewrites the move list so a person can solve it in their hands:

- `reduceSolution()` merges adjacent turns (`R R` becomes `R2`, `R R'` disappears) and collapses repeated sexy moves into `S(R,U)x5`.
- `translateMove()` and `FrontTopRotation()` track which face is in front and on top, and relabel every move for the current hold.
- `format()` inserts the whole-cube rotations (`x`, `y`, `z`) needed between moves and groups algorithms in parentheses, with `[ ]` marking a short algorithm inside a bigger one.

Example output (one line per stage):

```
B2 R2 D2 R D B'
z2 y U2 F2 y' U2 F2 y' U2 F2 y' U2 F2
y2 U (L' U' L U) (R U R' U')x3 y2 (L' U' L U)x5 U (R U R' U')
y2 (U' [L' U' L U] y [R U R' U']) y U2 (U [R U R' U'] y' [L' U' L U]) y ...
y U (F [ R U R' U' ] F') (F [ R U R' U' ] F')
(R U R' U R U2 R') U' (R U R' U R U2 R') U2
(U R U' L' U R' U' L) (U R U' L' U R' U' L)
z2 S(R,U)x4 D S(R,U)x4 D2 S(R,U)x4 D
```

### 3. Turning solver output into a walkthrough

`rubiks_solver.py` parses that notation and turns it into screens a beginner can follow:

- **Parsing:** a small parser handles single moves, rotations, parenthesised algorithms, nested `[ ]` groups, `xN` repeats and the `S(a,b)` shorthand.
- **Named algorithms:** known sequences are labelled ("right sexy", "left sexy", "sune", "The Corners Algorithm"). Unnamed ones are labelled by stage, such as "Yellow Cross Algorithm", and second-layer ones are "F2L algorithm left" or "F2L algorithm right".
- **Orientation tracking:** the app tracks which colour is on top and in front, so every rotation says exactly where to end up ("rotate to (white) top and (green) front") and every turn names the face and its colour.
- **Cube replay:** the scanned cube is replayed move by move on a simulated cube (3D sticker geometry). Each stage screen lists exactly which edges and corners are still wrong, by colour and current position, so you know what to look for. If the replay doesn't end solved, the app warns that the hints may be unreliable.

## Project structure

```
.
├── rubiks_solver.py   # scanner, correction UI, solver menu, walkthrough viewer
├── jspSolver.py       # beginner-method solver (hand-written, no dependencies)
└── README.md
```

## Known limitations

- On a small fraction of scrambles (about 3 in 40 in random testing) `jspSolver` takes a very long time to finish. This needs investigating.
- Occasionally the second-layer line of the solver's output contains malformed brackets. The viewer shows that text as an unrecognised instruction instead of crashing.
- The beginner method is deliberately simple and long: roughly 150 to 250 turns, compared with around 20 for Kociemba. That is why the app offers both.
- Colour detection needs reasonably even lighting. The correction screen is there for the occasional misread sticker.

## What this project demonstrates

- **Algorithm design:** a full solver built from scratch, with index-based state modelling and reusable piece-finding logic
- **Computer vision:** OpenCV capture, colour spaces and noise-robust sampling
- **Software design:** clear module boundaries, typed and documented functions, and graceful handling of missing solvers or invalid cubes
- **Parsing and tooling:** a notation parser, a simulator and a verification step that checks solutions by replaying them
- **User-focused design:** correction tools, plain-English instructions and error messages
- **Working with AI tools responsibly:** clear separation between hand-written and AI-assisted code

## Credits

The beginner method follows a standard layer-by-layer tutorial. Kociemba solving uses the [`kociemba`](https://pypi.org/project/kociemba/) library. Move notation reference: [jperm.net/3x3/moves](https://jperm.net/3x3/moves).
