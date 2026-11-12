#!/usr/bin/env python3
"""
Rubik's Cube scanner + solver (OpenCV + Kociemba + jspSolver).

Setup:
    pip install opencv-python numpy kociemba
    (jspSolver.py must sit in the same folder as this file)

Run:
    python rubiks_solver.py            # default webcam
    python rubiks_solver.py --camera 1 # another camera

How it works:
  1. You show the cube's six faces to the webcam, one at a time, lined up with
     the 3x3 grid on screen, and press SPACE to capture each one.
  2. Each sticker's colour is measured (median of a small patch, in LAB space)
     and matched to the nearest of the six CENTER stickers. Centers never move,
     so this works with any lighting or colour scheme.
  3. You get a review screen showing the unfolded cube. Click any sticker to
     cycle its colour if the camera got one wrong. Press ENTER to solve.
  4. A menu asks how you want to solve it:
        1 = fastest solve (Kociemba two-phase, fewest moves)
        2 = beginner walkthrough (jspSolver, layer by layer)
  5. The solution is shown step by step. For the beginner walkthrough:
        - turns in parentheses are shown together as one algorithm
        - well-known algorithms are called by name (right sexy, left sexy,
          sune, The Corners Algorithm)
        - x / y / z whole-cube rotations tell you which colour should end up
          on top and in front
        - the program keeps track of which colours are on top and in front, and
          names the colour of every face it tells you to turn
        - every stage has a name (Daisy, Cross, ...), and the screen lists the
          edges / corners (by colour, and where they currently sit) that are
          still wrong for that stage, so you know which pieces to look for.
        - every step has short directions, and the notation guide
          (https://jperm.net/3x3/moves) is linked on the solution screen
          (press O to open it).

MIRRORING: the live preview is mirrored by default so it behaves like a mirror
(move the cube left and it moves left on screen). The colours are still sampled
from the raw, un-mirrored frame, and the on-screen swatches are re-mapped to
match, so the faces are stored exactly as they look from the outside. Press M
while scanning (or pass --no-mirror) to switch the preview back.
"""

import argparse
import re
import sys
import textwrap
import webbrowser

import cv2
import numpy as np

try:
    import kociemba
except ImportError:
    kociemba = None

try:
    import jspSolver  # beginner-method solver: jspSolver.solve(facelets)
except ImportError:
    jspSolver = None

# Face letters in the order the Kociemba solver expects them.
LETTERS = "URFDLB"

# Scan order. Hold the cube with WHITE on top and GREEN in front as "home".
# Each face is shown with the orientation the solver expects (U edge at top of
# the image for F/R/B/L; blue-side at top for U; green-side at top for D).
STEPS = [
    ("F", "Front (green)",
     "Home position: WHITE center on top, GREEN center facing the camera."),
    ("R", "Right (red)",
     "Spin the whole cube so the RED center faces the camera. White stays on top."),
    ("B", "Back (blue)",
     "Spin the cube again so the BLUE center faces the camera. White stays on top."),
    ("L", "Left (orange)",
     "Spin the cube again so the ORANGE center faces the camera. White stays on top."),
    ("U", "Top (white)",
     "Go back to green-front, then tip the TOP toward the camera so WHITE faces it. "
     "The blue-side row should be at the top of the image."),
    ("D", "Bottom (yellow)",
     "Go back to green-front, then tip the BOTTOM toward the camera so YELLOW faces it. "
     "The green-side row should be at the top of the image."),
]

FACE_NAMES = {
    "U": "TOP", "D": "BOTTOM", "L": "LEFT",
    "R": "RIGHT", "F": "FRONT", "B": "BACK",
}

# Colour of each centre when the cube is held in the home position.
COLOR_NAMES = {
    "U": "white", "D": "yellow", "F": "green",
    "B": "blue", "R": "red", "L": "orange",
}

# The eight stages of the jspSolver walkthrough, one per line of its output.
STAGE_NAMES = ["Daisy", "Cross", "First Layer", "Second Layer", "Yellow Cross",
               "Orient Yellow Corners", "Orient Yellow Edges", "Solve Cube"]

# jspSolver's whole-cube rotations (x, y, z) turn the cube the OPPOSITE way to
# standard cube notation (checked against a sample solution: only with this
# setting does the daisy / cross / layers come out right at the end of each
# stage). Set to False if your solver ever uses the standard direction.
JSP_REVERSED_ROTATIONS = True

# Weight lightness less than colour so shadows/glare matter less.
LAB_WEIGHTS = np.array([0.6, 1.0, 1.0])


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------
def grid_cells(frame_shape):
    """Return 9 (x0, y0, x1, y1) boxes in reading order (left->right, top->bottom)."""
    h, w = frame_shape[:2]
    size = int(min(h, w) * 0.18)
    gap = size // 6
    total = 3 * size + 2 * gap
    ox = (w - total) // 2
    oy = (h - total) // 2 + 30  # leave room for the text banner
    cells = []
    for r in range(3):
        for c in range(3):
            x0 = ox + c * (size + gap)
            y0 = oy + r * (size + gap)
            cells.append((x0, y0, x0 + size, y0 + size))
    return cells


def sample_face(frame):
    """Median colour of the middle of every cell -> (lab[9,3], bgr[9,3])."""
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    bgr = np.zeros((9, 3), np.uint8)
    for i, (x0, y0, x1, y1) in enumerate(grid_cells(frame.shape)):
        size = x1 - x0
        pad = int(size * 0.3)
        patch = blurred[y0 + pad:y1 - pad, x0 + pad:x1 - pad]
        bgr[i] = np.median(patch.reshape(-1, 3), axis=0)
    lab = cv2.cvtColor(bgr.reshape(1, 9, 3), cv2.COLOR_BGR2LAB).reshape(9, 3)
    return lab.astype(np.float32), bgr


def draw_banner(img, lines):
    h = 24 * len(lines) + 12
    cv2.rectangle(img, (0, 0), (img.shape[1], h), (30, 30, 30), -1)
    for i, line in enumerate(lines):
        cv2.putText(img, line, (10, 24 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 1, cv2.LINE_AA)


def capture_faces(cam_index, mirror=True):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        sys.exit(f"Could not open camera {cam_index}. Try --camera 1.")

    faces = {}
    i = 0
    while i < len(STEPS):
        ok, frame = cap.read()
        if not ok:
            sys.exit("Failed to read from the camera.")

        letter, title, hint = STEPS[i]
        # Only the DISPLAY is mirrored. Sampling always uses the raw frame, so the
        # stored sticker order is the true (un-mirrored) view of the face.
        view = cv2.flip(frame, 1) if mirror else frame.copy()
        _, live_bgr = sample_face(frame)
        if mirror:
            # Display column c corresponds to raw column 2 - c.
            live_bgr = live_bgr.reshape(3, 3, 3)[:, ::-1].reshape(9, 3)
        for cell, color in zip(grid_cells(frame.shape), live_bgr):
            x0, y0, x1, y1 = cell
            cv2.rectangle(view, (x0, y0), (x1, y1), (255, 255, 255), 2)
            # Live swatch of what the camera currently sees in that cell.
            cx, cy, r = (x0 + x1) // 2, (y0 + y1) // 2, (x1 - x0) // 6
            cv2.rectangle(view, (cx - r, cy - r), (cx + r, cy + r),
                          tuple(int(v) for v in color), -1)
            cv2.rectangle(view, (cx - r, cy - r), (cx + r, cy + r), (0, 0, 0), 1)

        wrapped = textwrap.wrap(hint, 70)
        draw_banner(view, [f"Face {i + 1}/6: {title}"] + wrapped +
                    ["SPACE = capture   B = back   M = mirror on/off   Q = quit"])
        cv2.imshow("Rubik's Cube Scanner", view)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)
        elif key == ord("m"):
            mirror = not mirror
        elif key == ord("b") and i > 0:
            i -= 1
        elif key == 32:  # SPACE
            faces[letter] = sample_face(frame)
            i += 1

    cap.release()
    cv2.destroyAllWindows()
    return faces


# --------------------------------------------------------------------------
# Colour classification
# --------------------------------------------------------------------------
def classify(faces):
    """Assign each sticker to the face whose center colour is closest."""
    centers = {f: faces[f][0][4] for f in LETTERS}
    stickers = {}
    for f in LETTERS:
        lab = faces[f][0]
        row = []
        for i in range(9):
            if i == 4:
                row.append(f)
                continue
            row.append(min(
                LETTERS,
                key=lambda c: float(np.sum((LAB_WEIGHTS * (lab[i] - centers[c])) ** 2)),
            ))
        stickers[f] = row
    display = {f: tuple(int(v) for v in faces[f][1][4]) for f in LETTERS}
    return stickers, display


# --------------------------------------------------------------------------
# Review / correction screen
# --------------------------------------------------------------------------
FACE_ORIGIN = {  # (column, row) of each face in the unfolded net, in sticker units
    "U": (3, 0), "L": (0, 3), "F": (3, 3), "R": (6, 3), "B": (9, 3), "D": (3, 6),
}
S = 36   # sticker size in pixels
M = 20   # margin


def render_net(stickers, display, status):
    w, h = 12 * S + 2 * M, 9 * S + 2 * M + 70
    img = np.full((h, w, 3), 40, np.uint8)
    for f, (fc, fr) in FACE_ORIGIN.items():
        for i in range(9):
            x = M + (fc + i % 3) * S
            y = M + (fr + i // 3) * S
            cv2.rectangle(img, (x, y), (x + S - 2, y + S - 2),
                          display[stickers[f][i]], -1)
            cv2.rectangle(img, (x, y), (x + S - 2, y + S - 2), (0, 0, 0), 1)
            if stickers[f][i] != f or i == 4:
                cv2.putText(img, stickers[f][i], (x + 11, y + 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2, cv2.LINE_AA)

    all_text = "".join("".join(v) for v in stickers.values())
    x = M
    for f in LETTERS:
        n = all_text.count(f)
        color = (0, 200, 0) if n == 9 else (0, 0, 255)
        cv2.putText(img, f"{f}:{n}", (x, h - 45), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, color, 2, cv2.LINE_AA)
        x += 70
    cv2.putText(img, status or "Click=recolor  U/D/L/R/F/B=rotate face  ENTER=solve",
                (M, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def rotate_cw(face):
    """Rotate a face's 9 stickers 90 degrees clockwise (fixes a mis-oriented scan)."""
    return [face[3 * (2 - c) + r] for r in range(3) for c in range(3)]


def choose_method():
    """Menu shown when the user presses ENTER to solve.

    Returns "fast" (Kociemba), "beginner" (jspSolver), or None to go back.
    """
    win = "Choose solve method"
    status = ""
    fast_note = "" if kociemba else "   (kociemba not installed)"
    beg_note = "" if jspSolver else "   (jspSolver.py not found)"
    while True:
        img = np.full((330, 900, 3), 35, np.uint8)
        cv2.putText(img, "How do you want to solve it?", (30, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "1  Fastest solve (Kociemba)" + fast_note, (30, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "Fewest possible moves, no explanations.", (65, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (170, 170, 170), 1, cv2.LINE_AA)
        cv2.putText(img, "2  Beginner walkthrough (jspSolver)" + beg_note, (30, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "Layer by layer, with named algorithms and rotation help.",
                    (65, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (170, 170, 170), 1, cv2.LINE_AA)
        cv2.putText(img, status or "B = back to review   Q = quit", (30, 295),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(win, img)

        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            cv2.destroyAllWindows()
            sys.exit(0)
        if key == ord("b"):
            choice = None
            break
        if key == ord("1"):
            if kociemba:
                choice = "fast"
                break
            status = "Kociemba isn't installed:  pip install kociemba"
        elif key == ord("2"):
            if jspSolver:
                choice = "beginner"
                break
            status = "Couldn't import jspSolver - put jspSolver.py next to this file."

    cv2.destroyWindow(win)
    cv2.waitKey(1)
    return choice


def run_solver(method, facelets):
    """Return the solver's raw text output (one or more lines)."""
    if method == "fast":
        return kociemba.solve(facelets)
    out = jspSolver.solve(facelets)
    return out if isinstance(out, str) else "\n".join(str(line) for line in out)


def review(stickers, display):
    state = {"status": ""}

    def on_mouse(event, mx, my, *_):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        for f, (fc, fr) in FACE_ORIGIN.items():
            for i in range(9):
                if i == 4:
                    continue  # centers define the colours; don't change them
                x = M + (fc + i % 3) * S
                y = M + (fr + i // 3) * S
                if x <= mx < x + S and y <= my < y + S:
                    nxt = (LETTERS.index(stickers[f][i]) + 1) % 6
                    stickers[f][i] = LETTERS[nxt]
                    state["status"] = ""
                    return

    win = "Review cube (letters = which face's colour)"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_mouse)

    while True:
        cv2.imshow(win, render_net(stickers, display, state["status"]))
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            cv2.destroyAllWindows()
            sys.exit(0)
        if key < 128 and chr(key).upper() in LETTERS:
            # Press a face letter (U/R/F/D/L/B) to rotate that face 90 deg clockwise.
            face = chr(key).upper()
            stickers[face] = rotate_cw(stickers[face])
            state["status"] = ""
        if key in (13, 10):  # ENTER
            facelets = "".join("".join(stickers[f]) for f in LETTERS)
            counts_ok = all(facelets.count(f) == 9 for f in LETTERS)
            if not counts_ok:
                state["status"] = "Each colour must appear exactly 9 times (see counts)."
                continue

            method = choose_method()
            if method is None:  # user went back to the review screen
                state["status"] = ""
                continue

            print(facelets)
            try:
                text = run_solver(method, facelets)
            except Exception as exc:  # solvers raise on impossible cubes
                state["status"] = "Invalid cube - fix a sticker (twisted/swapped?)."
                print("Solver error:", exc)
                continue
            cv2.destroyAllWindows()
            return method, text, facelets


# --------------------------------------------------------------------------
# Whole-cube orientation tracking
# --------------------------------------------------------------------------
# orientation maps a position (U/D/L/R/F/B) -> the centre sitting there
# (named by its home position, so COLOR_NAMES gives its colour).
IDENTITY = {p: p for p in "UDLRFB"}


def turn_cube(o, axis):
    """Rotate the whole cube one quarter turn clockwise about x, y or z."""
    n = dict(o)
    if axis == "x":    # like an R turn: front goes up
        n["U"], n["F"], n["D"], n["B"] = o["F"], o["D"], o["B"], o["U"]
    elif axis == "y":  # like a U turn: front goes left
        n["F"], n["R"], n["B"], n["L"] = o["R"], o["B"], o["L"], o["F"]
    elif axis == "z":  # like an F turn: top goes right
        n["U"], n["R"], n["D"], n["L"] = o["L"], o["U"], o["R"], o["D"]
    return n


def apply_rotation(o, tok):
    """Apply a rotation token such as x, y', z2."""
    times = 2 if tok.endswith("2") else 3 if tok.endswith("'") else 1
    for _ in range(times):
        o = turn_cube(o, tok[0])
    return o


def hold_text(o):
    return f"({COLOR_NAMES[o['U']]}) on top and ({COLOR_NAMES[o['F']]}) in front"


# --------------------------------------------------------------------------
# Cube simulation (works out which pieces are still wrong at every step)
# --------------------------------------------------------------------------
# Every sticker is (position, normal, colour) in the frame of the person
# holding the cube: x = right, y = up, z = toward you. Rotating the whole cube
# moves every sticker, so "TOP" / "FRONT" always mean the current hold.
FACE_NORMAL = {"U": (0, 1, 0), "D": (0, -1, 0), "R": (1, 0, 0),
               "L": (-1, 0, 0), "F": (0, 0, 1), "B": (0, 0, -1)}
NORMAL_FACE = {v: k for k, v in FACE_NORMAL.items()}
ROT_AXIS = {"x": FACE_NORMAL["R"], "y": FACE_NORMAL["U"], "z": FACE_NORMAL["F"]}
COLOR_ORDER = "UDFBRL"  # white, yellow, green, blue, red, orange


def facelet_geometry(face, i):
    """Position and outward normal of sticker i of a face (Kociemba ordering)."""
    r, c = divmod(i, 3)
    if face == "U":
        return (c - 1, 1, r - 1), (0, 1, 0)
    if face == "R":
        return (1, 1 - r, 1 - c), (1, 0, 0)
    if face == "F":
        return (c - 1, 1 - r, 1), (0, 0, 1)
    if face == "D":
        return (c - 1, -1, 1 - r), (0, -1, 0)
    if face == "L":
        return (-1, 1 - r, c - 1), (-1, 0, 0)
    return (1 - c, 1 - r, -1), (0, 0, -1)  # B


def initial_state(facelets):
    state = []
    for fi, face in enumerate(LETTERS):
        for i in range(9):
            pos, nrm = facelet_geometry(face, i)
            state.append((pos, nrm, facelets[fi * 9 + i]))
    return state


def _rot90cw(v, n):
    """Rotate vector v a quarter turn clockwise when looking at the tip of n."""
    dot = sum(a * b for a, b in zip(v, n))
    cross = (n[1] * v[2] - n[2] * v[1],
             n[2] * v[0] - n[0] * v[2],
             n[0] * v[1] - n[1] * v[0])
    return tuple(n[k] * dot - cross[k] for k in range(3))


def sim_move(state, tok):
    """Apply a face turn (R, U', F2 ...) or whole-cube rotation (x, y', z2 ...)."""
    face = tok[0]
    whole = face in ROT_AXIS
    n = ROT_AXIS[face] if whole else FACE_NORMAL[face]
    turns = 2 if tok.endswith("2") else 3 if tok.endswith("'") else 1
    out = []
    for pos, nrm, col in state:
        if whole or sum(a * b for a, b in zip(pos, n)) == 1:
            for _ in range(turns):
                pos, nrm = _rot90cw(pos, n), _rot90cw(nrm, n)
        out.append((pos, nrm, col))
    return out


def analyze(state):
    """Return (centers {normal: colour}, edges, corners); a piece is
    (position, [(normal, colour), ...])."""
    by_pos, centers, edges, corners = {}, {}, [], []
    for pos, nrm, col in state:
        by_pos.setdefault(pos, []).append((nrm, col))
    for pos, stickers in by_pos.items():
        zeros = sum(1 for v in pos if v == 0)
        if zeros == 2:
            centers[stickers[0][0]] = stickers[0][1]
        elif zeros == 1:
            edges.append((pos, stickers))
        else:
            corners.append((pos, stickers))
    return centers, edges, corners


def _has(piece, col):
    return any(c == col for _, c in piece[1])


def _solved(piece, centers):
    return all(centers[n] == c for n, c in piece[1])


def _right_spot(piece, centers):
    """True if the piece sits where its colours belong (it may be twisted)."""
    pos, stickers = piece
    here = {centers[n] for n in FACE_NORMAL.values()
            if sum(a * b for a, b in zip(pos, n)) == 1}
    return here == {c for _, c in stickers}


STAGE_GOALS = [
    "the 4 white edges around the yellow center, white side facing the yellow center",
    "the 4 white edges on the white center, each matching its side center",
    "the 4 white corners in place, finishing the white layer",
    "the 4 middle-layer edges (no white, no yellow) in place",
    "the 4 yellow edges with their yellow side facing the yellow center",
    "every remaining edge and corner in its right spot",
    "every remaining edge and corner in its right spot",
    "every piece solved",
]


def piece_line(piece, centers, detail):
    kind = "edge" if len(piece[1]) == 2 else "corner"
    ordered = sorted(piece[1], key=lambda s: COLOR_ORDER.index(s[1]))
    name = "-".join(COLOR_NAMES[c] for _, c in ordered)
    where = ", ".join(f"{COLOR_NAMES[c]} on {FACE_NAMES[NORMAL_FACE[n]]}"
                      for n, c in ordered)
    line = f"{name} {kind}: {where}"
    if detail:
        if _right_spot(piece, centers):
            line += " (right spot, " + ("flipped" if kind == "edge" else "twisted") + ")"
        else:
            line += " (wrong spot)"
    return line


def stage_hint(stage, state):
    """(goal, [lines]) for walkthrough stage 0-7: the edges/corners that are
    still wrong for that stage, with their colours and where they sit now."""
    centers, edges, corners = analyze(state)
    ny = next(n for n, c in centers.items() if c == "D")  # yellow-center side

    def facing(p, col):
        return any(c == col and n == ny for n, c in p[1])

    def unsolved(ps):
        return [p for p in ps if not _solved(p, centers)]

    if stage == 0:    # daisy: white edges not yet next to the yellow center
        wrong = [p for p in edges if _has(p, "U") and not facing(p, "U")]
    elif stage == 1:  # cross
        wrong = unsolved([p for p in edges if _has(p, "U")])
    elif stage == 2:  # first layer
        wrong = (unsolved([p for p in corners if _has(p, "U")]) +
                 unsolved([p for p in edges if _has(p, "U")]))
    elif stage == 3:  # second layer
        wrong = unsolved([p for p in edges if not _has(p, "U") and not _has(p, "D")])
    elif stage == 4:  # yellow cross
        wrong = [p for p in edges if _has(p, "D") and not facing(p, "D")]
    else:             # yellow layer / final: everything still unsolved
        wrong = unsolved(edges) + unsolved(corners)
    return STAGE_GOALS[stage], [piece_line(p, centers, stage >= 5) for p in wrong]


# --------------------------------------------------------------------------
# Parsing solver output
# --------------------------------------------------------------------------
# Named algorithms, matched on the exact move sequence.
ALG_NAMES = {
    "R U R' U'": "right sexy",
    "L' U' L U": "left sexy",
    "R U R' U R U2 R'": "sune",
    "U R U' L' U R' U' L": "The Corners Algorithm",
    "U R U' L' U R' U' L'": "The Corners Algorithm",
}

# What each (effective, standard-direction) whole-cube rotation looks like.
ROT_NOTES = {
    "x": "the front face tips up",
    "x'": "the front face tips down",
    "x2": "half turn: flip the cube end over end",
    "y": "the front face swings left",
    "y'": "the front face swings right",
    "y2": "half turn: the front face goes to the back",
    "z": "the top face tips right",
    "z'": "the top face tips left",
    "z2": "half turn: turn the cube upside down",
}

MOVE_RE = r"[URFDLBxyz][2']?"
TOKEN = re.compile(
    r"\((?P<inner>[^)]*)\)(?:x(?P<grep>\d+))?"                      # (R U R' U')x5, may hold [..] groups
    r"|\[(?P<binner>[^\]]*)\](?:x(?P<brep>\d+))?"                   # [R U R' U'] on its own
    r"|S\(\s*(?P<a>[URFDLB][2']?)\s*,\s*(?P<b>[URFDLB][2']?)\s*\)"  # S(R,U)x2
    r"(?:x(?P<srep>\d+))?"
    r"|(?P<move>" + MOVE_RE + ")"                                   # R  U'  y2
)
INNER = re.compile(r"\[(?P<sub>[^\]]*)\](?:x(?P<n>\d+))?|(?P<mv>" + MOVE_RE + ")")


def invert(move):
    if move.endswith("2"):
        return move
    if move.endswith("'"):
        return move[:-1]
    return move + "'"


def parse_inner(inner):
    """Split the inside of ( ... ) into flat moves, display text, and [..] sub-algorithms."""
    moves, parts, subs = [], [], []
    for m in INNER.finditer(inner):
        if m.group("sub") is not None:
            sub = re.findall(MOVE_RE, m.group("sub"))
            n = int(m.group("n") or 1)
            if sub:
                moves += sub * n
                subs.append(sub)
                parts.append("[" + " ".join(sub) + "]" + (f"x{n}" if n > 1 else ""))
        else:
            moves.append(m.group("mv"))
            parts.append(m.group("mv"))
    return moves, " ".join(parts), subs


def parse_line(line):
    """Turn one line of solver output into a list of instruction items.

    Items are ("move", tok), ("rot", tok), ("raw", text) or
    ("alg", [flat moves], repeat, display text, [sub-algorithms in brackets]).
    S(a,b) is the "sexy move" shorthand: a b a' b'. A stray backslash is ignored.
    """
    line = line.replace("\\", " ")
    items, pos = [], 0
    for m in TOKEN.finditer(line):
        gap = line[pos:m.start()].strip()
        if gap:
            items.append(("raw", gap))
        pos = m.end()
        if m.group("inner") is not None:
            moves, display, subs = parse_inner(m.group("inner"))
            if moves:
                items.append(("alg", moves, int(m.group("grep") or 1), display, subs))
        elif m.group("binner") is not None:
            moves = re.findall(MOVE_RE, m.group("binner"))
            if moves:
                items.append(("alg", moves, int(m.group("brep") or 1), " ".join(moves), []))
        elif m.group("a"):
            a, b = m.group("a"), m.group("b")
            moves = [a, b, invert(a), invert(b)]
            items.append(("alg", moves, int(m.group("srep") or 1), " ".join(moves), []))
        else:
            tok = m.group("move")
            items.append(("rot" if tok[0] in "xyz" else "move", tok))
    tail = line[pos:].strip()
    if tail:
        items.append(("raw", tail))
    return items


def build_steps(text, facelets=None, beginner=False):
    """Parse solver output (one stage per line) into a flat list of steps.

    Each step remembers the whole-cube orientation before and after it. For the
    beginner walkthrough (8 stage lines) it also gets a stage name and a list of
    the pieces still wrong for that stage.
    """
    raw = text.splitlines()
    while raw and not raw[-1].strip():
        raw.pop()
    guided = beginner and len(raw) == len(STAGE_NAMES)
    flip = (lambda t: invert(t)) if beginner and JSP_REVERSED_ROTATIONS else (lambda t: t)

    steps, orient = [], dict(IDENTITY)
    state = initial_state(facelets) if guided and facelets else None
    for stage, line in enumerate(raw, 1):
        for item in parse_line(line):
            step = {"kind": item[0], "stage": stage, "stages": len(raw),
                    "stage_name": STAGE_NAMES[stage - 1] if guided else "",
                    "before": orient, "repeat": 1, "moves": [], "eff": "",
                    "text": "", "hint": None, "display": "", "subs": [],
                    "reversed": beginner and JSP_REVERSED_ROTATIONS}
            after, state_after = orient, state
            if item[0] in ("move", "rot"):
                step["moves"] = [item[1]]
                if item[0] == "rot":
                    step["eff"] = flip(item[1])
                    after = apply_rotation(orient, step["eff"])
                    if state is not None:
                        state_after = sim_move(state, step["eff"])
                elif state is not None:
                    state_after = sim_move(state, item[1])
            elif item[0] == "alg":
                step["moves"], step["repeat"] = item[1], item[2]
                step["display"], step["subs"] = item[3], item[4]
                for _ in range(step["repeat"]):
                    for t in step["moves"]:
                        eff = flip(t) if t[0] in "xyz" else t
                        if t[0] in "xyz":
                            after = apply_rotation(after, eff)
                        if state_after is not None:
                            state_after = sim_move(state_after, eff)
            else:
                step["text"] = item[1]
            step["after"] = after
            if state is not None:
                # For a rotation, show the pieces as they will look once rotated.
                goal, lines = stage_hint(stage - 1, state_after if item[0] == "rot" else state)
                step["hint"] = (goal, lines, item[0] == "rot")
            orient, state = after, state_after
            steps.append(step)
    return steps


# --------------------------------------------------------------------------
# Solution viewer
# --------------------------------------------------------------------------
NOTATION_URL = "https://jperm.net/3x3/moves"
LEFT_SEXY = ["L'", "U'", "L", "U"]
RIGHT_SEXY = ["R", "U", "R'", "U'"]

# One short sentence per stage, shown as the last small direction on each step.
STAGE_TIPS = {
    "Daisy": "Daisy: bring the 4 white edges around the yellow center, white stickers facing the yellow face.",
    "Cross": "Cross: line a white edge's side color up with its matching center, then turn that face 180 degrees to drop it onto the white center.",
    "First Layer": "First Layer: park a white corner above its slot, then repeat the sexy move until it drops in with white on the white face.",
    "Second Layer": "Second Layer: slide each middle edge into the gap between its two matching centers.",
    "Yellow Cross": "Yellow Cross: repeat this until the yellow edges form a cross on the yellow face.",
    "Orient Yellow Corners": "Orient Yellow Corners: keep going until all 4 corners show yellow on the yellow face.",
    "Orient Yellow Edges": "Orient Yellow Edges: line the yellow edges up with their matching side centers.",
    "Solve Cube": "Solve Cube: twist the last corners until every piece is home.",
}


def alg_name(moves):
    return ALG_NAMES.get(" ".join(moves))


def f2l_side(step):
    """'left' or 'right' for a second-layer (F2L) algorithm."""
    for sub in step["subs"]:
        if sub == LEFT_SEXY:
            return "left"
        if sub == RIGHT_SEXY:
            return "right"
    moves = step["moves"]
    return "left" if sum(m[0] == "L" for m in moves) > sum(m[0] == "R" for m in moves) else "right"


def alg_label(step):
    """Known name, else 'F2L algorithm left/right' (second layer), else '<Stage> Algorithm'."""
    name = alg_name(step["moves"])
    if name:
        return name
    stage = step.get("stage_name") or ""
    if stage == "Second Layer":
        return f"F2L algorithm {f2l_side(step)}"
    return f"{stage} Algorithm" if stage else "Algorithm"


def step_title(step):
    """Short text for a step, e.g. R', y2, (R U R' U') x5."""
    if step["kind"] == "alg":
        title = "(" + (step.get("display") or " ".join(step["moves"])) + ")"
        if step["repeat"] > 1:
            title += f" x{step['repeat']}"
        return title
    if step["kind"] == "raw":
        return step["text"]
    return step["moves"][0]


def short_move(move, orient):
    how = {"": "clockwise", "'": "counter-clockwise"}.get(move[1:], "180 degrees")
    return f"{FACE_NAMES[move[0]]} ({COLOR_NAMES[orient[move[0]]]}) face, {how}"


def describe_move(move, orient):
    face = move[0]
    label = f"{FACE_NAMES[face]} ({COLOR_NAMES[orient[face]]}) face"
    mod = move[1:]
    if mod == "":
        return f"Turn the {label} clockwise 90 degrees"
    if mod == "'":
        return f"Turn the {label} counter-clockwise 90 degrees"
    return f"Turn the {label} 180 degrees"


def move_breakdown(step):
    """One short line per turn of an algorithm (one pass), following any
    rotation inside it, so every turn names the face and colour to use."""
    orient, out = step["before"], []
    for n, t in enumerate(step["moves"], 1):
        if t[0] in "xyz":
            eff = invert(t) if step.get("reversed") else t
            orient = apply_rotation(orient, eff)
            out.append(f"{n}. {t}: rotate the whole cube to ({COLOR_NAMES[orient['U']]}) top, "
                       f"({COLOR_NAMES[orient['F']]}) front")
        else:
            out.append(f"{n}. {t}: {short_move(t, orient)}")
    return out


def describe_step(step):
    """Return (main_lines, small_direction_lines) of plain-English instructions."""
    before, after, kind = step["before"], step["after"], step["kind"]
    hold = f"Hold the cube with {hold_text(before)}."
    tip = STAGE_TIPS.get(step.get("stage_name"))
    small = []

    if kind == "move":
        mod = step["moves"][0][1:]
        small.append({"": "Clockwise means as if you were looking straight at that face.",
                      "'": "Counter-clockwise: the opposite way (the ' is read 'prime')."}
                     .get(mod, "Half turn: either direction gives the same result."))
        small.append(hold)
        main = [describe_move(step["moves"][0], before)]

    elif kind == "rot":
        top, front = COLOR_NAMES[after["U"]], COLOR_NAMES[after["F"]]
        main = [f"Rotate the whole cube to ({top}) top and ({front}) front"]
        small.append(f"{step['moves'][0]}: {ROT_NOTES[step['eff']]}.")
        small.append("Only reorient the cube in your hands; no layer turns.")

    elif kind == "alg":
        label = alg_label(step)
        what = label if label.lower().startswith("the ") else f"the {label}"
        main = [f"Do {what}" + (f" {step['repeat']} times in a row" if step["repeat"] > 1 else "")]
        small.append("Do the turns in order, left to right, without pausing.")
        if step["repeat"] > 1:
            small.append(f"Repeat the whole sequence {step['repeat']} times in a row.")
        if step["subs"]:
            seen = []
            for sub in step["subs"]:
                text = " ".join(sub)
                if text not in seen:
                    seen.append(text)
            small.append("[ ] marks a short algorithm: " + "; ".join(
                f"[{t}] = {ALG_NAMES.get(t, 'short algorithm')}" for t in seen) + ".")
        if any(t[0] in "xyz" for t in step["moves"]):
            small.append("After a rotation (x/y/z) the later turns use the new hold; see the list below.")
        small.append(hold)

    else:
        return [f"Unrecognised instruction, do it as written: {step['text']}"], []

    if tip:
        small.append(tip)
    return main, small


FONT = cv2.FONT_HERSHEY_SIMPLEX


def put(img, text, y, scale, color, thick, x=30):
    cv2.putText(img, text, (x, y), FONT, scale, color, thick, cv2.LINE_AA)


def wrap_px(text, scale, thick, max_w):
    """Split text into lines that fit max_w pixels."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and cv2.getTextSize(trial, FONT, scale, thick)[0][0] > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def put_wrapped(img, text, y, scale, color, thick, x, max_w, step_h):
    """Draw wrapped text; returns the y for whatever comes next."""
    for line in wrap_px(text, scale, thick, max_w):
        put(img, line, y, scale, color, thick, x=x)
        y += step_h
    return y


GREY, WHITE = (170, 170, 170), (255, 255, 255)
YELLOW, CYAN, GREEN = (0, 220, 255), (255, 200, 0), (0, 200, 0)


def render_step(steps, i):
    s = steps[i]
    w, h = 1200, 720
    LX, LW = 30, 630            # left column: what to do
    RX = 700                    # right column: which pieces to look for
    RW = w - RX - 30
    img = np.full((h, w, 3), 35, np.uint8)

    head = f"Step {i + 1} / {len(steps)}"
    if s["stages"] > 1:
        head += f"      Stage {s['stage']} / {s['stages']}"
        if s["stage_name"]:
            head += f": {s['stage_name']}"
    put(img, head, 45, 0.9, (200, 200, 200), 2)
    if i == len(steps) - 1:
        put(img, "Last step!", 45, 0.9, GREEN, 2, x=1030)
    cv2.line(img, (680, 70), (680, h - 75), (70, 70, 70), 1)

    # ---- left column: the instruction -------------------------------------
    if s["kind"] in ("move", "rot"):
        put(img, step_title(s), 175, 4, YELLOW if s["kind"] == "move" else CYAN, 8)
        y = 250
    elif s["kind"] == "alg":
        label = alg_label(s)
        y = put_wrapped(img, label[0].upper() + label[1:], 105, 1.3, YELLOW, 3, LX, LW, 46)
        y = put_wrapped(img, step_title(s), y, 1.0, WHITE, 2, LX, LW, 38)
        y += 16
    else:
        put(img, "?", 175, 4, YELLOW, 8)
        y = 250

    main, small = describe_step(s)
    for text in main:
        y = put_wrapped(img, text, y, 0.8, WHITE, 2, LX, LW, 34)
    y += 8
    for text in small:
        y = put_wrapped(img, text, y, 0.55, GREY, 1, LX, LW, 24)

    if s["kind"] == "alg" and len(s["moves"]) > 1:
        y += 10
        put(img, "Move by move:", y, 0.6, CYAN, 1)
        y += 26
        for text in move_breakdown(s):
            if y > h - 100:
                put(img, "...", y, 0.5, GREY, 1)
                break
            y = put_wrapped(img, text, y, 0.5, WHITE, 1, LX, LW, 22)

    # ---- right column: pieces still wrong ---------------------------------
    ry = 100
    if s["hint"]:
        goal, lines, after_rot = s["hint"]
        ry = put_wrapped(img, "Stage goal: " + goal, ry, 0.6, CYAN, 1, RX, RW, 26)
        if after_rot:
            ry = put_wrapped(img, "(positions below are as the cube will look after you rotate it)",
                             ry, 0.5, GREY, 1, RX, RW, 24)
        ry += 8
        if lines:
            put(img, f"Pieces still wrong ({len(lines)}) - look for:", ry, 0.6, YELLOW, 1, x=RX)
            ry += 28
            for text in lines[:8]:
                ry = put_wrapped(img, "- " + text, ry, 0.5, WHITE, 1, RX, RW, 22)
                ry += 4
            if len(lines) > 8:
                put(img, f"- ... and {len(lines) - 8} more", ry, 0.5, GREY, 1, x=RX)
        else:
            put(img, "Nothing left to fix for this stage.", ry, 0.6, GREEN, 1, x=RX)
    else:
        put_wrapped(img, "Follow the steps in order. If a symbol is unfamiliar, "
                         "see the notation guide below.", ry, 0.6, GREY, 1, RX, RW, 26)

    put(img, "N/SPACE = next   P = previous   O = open notation guide in browser   Q = quit",
        h - 45, 0.5, GREY, 1)
    put(img, "Notation guide: " + NOTATION_URL, h - 18, 0.6, CYAN, 1)
    return img


def show_solution(steps):
    print(f"\nNotation guide: {NOTATION_URL}")
    print(f"\nSolution ({len(steps)} steps):")
    stage = None
    for n, s in enumerate(steps, 1):
        if s["stage"] != stage:
            stage = s["stage"]
            if s["stages"] > 1:
                label = f": {s['stage_name']}" if s["stage_name"] else ""
                print(f"\n-- Stage {stage}/{s['stages']}{label} --")
        print(f"{n:>3}. {step_title(s):<34} {describe_step(s)[0][0]}")

    if not steps:
        print("The cube is already solved!")
        return

    i = 0
    while True:
        cv2.imshow("Solution", render_step(steps, i))
        key = cv2.waitKey(0) & 0xFF
        if key == ord("q"):
            break
        if key == ord("o"):
            try:
                webbrowser.open(NOTATION_URL)
            except Exception:
                pass
        elif key in (ord("n"), 32, 13):
            if i >= len(steps) - 1:
                break
            i += 1
        elif key == ord("p") and i > 0:
            i -= 1
    cv2.destroyAllWindows()
    cv2.waitKey(1)


# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Scan and solve a Rubik's Cube.")
    parser.add_argument("--camera", type=int, default=0, help="camera index (default 0)")
    parser.add_argument("--no-mirror", action="store_true",
                        help="show the raw (non-mirrored) camera preview")
    args = parser.parse_args()

    if kociemba is None and jspSolver is None:
        sys.exit("No solver found. Install kociemba (pip install kociemba) "
                 "and/or put jspSolver.py next to this file.")

    faces = capture_faces(args.camera, mirror=not args.no_mirror)
    stickers, display = classify(faces)
    method, text, facelets = review(stickers, display)
    show_solution(build_steps(text, facelets, beginner=(method == "beginner")))


if __name__ == "__main__":
    main()
