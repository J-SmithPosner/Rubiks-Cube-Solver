#!/usr/bin/env python3
JSP = False
"""
Rubik's Cube scanner + solver (OpenCV + Kociemba).

Setup:
    pip install opencv-python numpy kociemba

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
  4. The Kociemba two-phase algorithm finds a short solution, which is shown
     step by step with plain-English instructions.

MIRRORING: the live preview is mirrored by default so it behaves like a mirror
(move the cube left and it moves left on screen). The colours are still sampled
from the raw, un-mirrored frame, and the on-screen swatches are re-mapped to
match, so the faces are stored exactly as they look from the outside. Press M
while scanning (or pass --no-mirror) to switch the preview back.
"""

import argparse
import sys
import textwrap
import time

import cv2
import numpy as np
import jspSolver

try:
    import kociemba
except ImportError:
    kociemba = None

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
            try:
                if JSP:
                    solution = jspSolver.solve(facelets)
                else:
                    solution = kociemba.solve(facelets)
                    print(facelets)
            except Exception as exc:  # kociemba raises ValueError on impossible cubes
                state["status"] = "Invalid cube - fix a sticker (twisted/swapped?)."
                print("Solver error:", exc)
                continue
            cv2.destroyAllWindows()
            return solution.split()


# --------------------------------------------------------------------------
# Solution viewer
# --------------------------------------------------------------------------
def describe(move):
    name = FACE_NAMES[move[0]]
    mod = move[1:]
    if mod == "":
        return f"Turn the {name} face clockwise 90 degrees"
    if mod == "'":
        return f"Turn the {name} face counter-clockwise 90 degrees"
    return f"Turn the {name} face 180 degrees"


def show_solution(moves):
    print(f"\nSolution ({len(moves)} moves):")
    print(" ".join(moves))
    for n, m in enumerate(moves, 1):
        print(f"{n:>2}. {m:<3} {describe(m)}")

    if not moves:
        print("The cube is already solved!")
        return

    i = 0
    while True:
        img = np.full((360, 900, 3), 35, np.uint8)
        move = moves[i]
        cv2.putText(img, f"Step {i + 1} / {len(moves)}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2, cv2.LINE_AA)
        cv2.putText(img, move, (30, 180), cv2.FONT_HERSHEY_SIMPLEX,
                    4, (0, 220, 255), 8, cv2.LINE_AA)
        cv2.putText(img, describe(move), (30, 245), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "Keep WHITE center on top and GREEN center facing you.",
                    (30, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1, cv2.LINE_AA)
        cv2.putText(img, "Clockwise = as if looking straight at that face.   "
                         "N/SPACE = next   P = previous   Q = quit",
                    (30, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1, cv2.LINE_AA)
        if i == len(moves) - 1:
            cv2.putText(img, "Last move!", (600, 50), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 200, 0), 2, cv2.LINE_AA)
        cv2.imshow("Solution", img)

        key = cv2.waitKey(0) & 0xFF
        if key == ord("q"):
            break
        if key in (ord("n"), 32, 13):
            if i >= len(moves)-1:
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

    if kociemba is None:
        sys.exit("Missing dependency. Install it with:  pip install kociemba")

    faces = capture_faces(args.camera, mirror=not args.no_mirror)
    stickers, display = classify(faces)
    moves = review(stickers, display)
    show_solution(moves)


if __name__ == "__main__":
    main()
