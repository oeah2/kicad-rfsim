"""F40: a drawn simulation boundary must give the same line as the full board.

The rig makes a 50 ohm microstrip on a large board. It draws one closed
rectangle on User.4 around the line, and runs the board twice: once with the
full board and once with the boundary. The two S21 traces and the Z0 of the
line must agree, and the cropped domain must be smaller.

The board is large enough that `boundary + margin + PML` stays inside the
board at every mesh preset. That is the case in which the substrate and the
copper continue into the absorber and the cut is a matched termination.

Run it with the python of KiCad 10:
    validation\\openems\\run_boundary_openems.py [coarse|medium|fine]
    validation\\emerge\\run_boundary_emerge.py [coarse|medium|fine]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rigsolve  # noqa: E402

import pcbnew  # noqa: E402
import board_reader  # noqa: E402
import make_test_board  # noqa: E402

# The line is at y=10, x=5..35. The board is 120 x 120 mm, with the line
# 30 mm from the top and left edges and 50 mm from the bottom and right.
# The boundary is 40 x 20 mm, and 30..50 mm of board remains around it.
BOARD_SIZE = (-30.0, -30.0, 90.0, 90.0)
BOUNDARY = (0.0, 0.0, 40.0, 20.0)     # KiCad coordinates
MARGIN = 4.0
F_START, F_STOP = 1e9, 6e9
# Start wide. The gap between a full ground plane and a truncated one is
# small, but a coarse FDTD mesh has its own spread. Tighten after the first
# real run.
MAX_DS21_DB = 0.3
MAX_DZ0 = 0.03


def _draw_boundary(board, rect):
    """Put one closed rectangle on User.4, in the coordinates of KiCad."""
    x0, y0, x1, y1 = rect
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    s.SetLayer(pcbnew.User_4)
    s.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)))
    s.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    board.Add(s)
    return s


def _model(board, pads, boundary, mesh):
    """Give the model that the solver runs."""
    m = board_reader.extract(board, pads, MARGIN, f_stop=F_STOP, mesh=mesh,
                             boundary=boundary)
    for p in m["ports"]:
        p["type"] = "msl"
    m["settings"] = {
        "f_start": F_START, "f_stop": F_STOP, "z0": 50.0,
        "margin_mm": MARGIN, "mesh": mesh, "n_freq": 201,
        "max_timesteps": 300000, "end_criteria": 1e-4,
    }
    return m


def _s21(path):
    """Give (frequency, S21 in dB) of a results file."""
    import numpy as np
    rows = np.loadtxt(path, comments=("!", "#"))
    s21 = 20.0 * np.log10(np.abs(rows[:, 3] + 1j * rows[:, 4]) + 1e-12)
    return rows[:, 0], s21


def _z0(lines):
    """Give the real Z0 of port 1, or None when the run wrote no line."""
    if not lines:
        return None
    p = lines.get("ports", {}).get("1")
    return p.get("Z0_real") if p else None


def main(mesh="coarse"):
    import numpy as np
    out = rigsolve.out("out_boundary_" + mesh)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "boundary_line.kicad_pcb")
    board, pads = make_test_board.make(path, size=BOARD_SIZE)
    _draw_boundary(board, BOUNDARY)
    pcbnew.SaveBoard(path, board)

    full = _model(board, pads, None, mesh)
    crop = _model(board, pads, "User.4", mesh)
    for name, m in (("full", full), ("crop", crop)):
        r = m["region"]
        print("%s: region %.1f x %.1f mm, %d F.Cu polys, %d B.Cu polys"
              % (name, r["x1"] - r["x0"], r["y1"] - r["y0"],
                 len(m["polygons"].get("F.Cu", [])),
                 len(m["polygons"].get("B.Cu", []))))
    assert crop["boundary"]["layer"] == "User.4"
    assert crop["region"]["x1"] - crop["region"]["x0"] < \
        full["region"]["x1"] - full["region"]["x0"]
    assert crop["region"]["y1"] - crop["region"]["y0"] < \
        full["region"]["y1"] - full["region"]["y0"]

    full_dir = os.path.join(out, "full")
    crop_dir = os.path.join(out, "crop")
    rigsolve.run(full, full_dir, "full")
    rigsolve.run(crop, crop_dir, "crop")

    f_full, s_full = _s21(os.path.join(full_dir, "results.s2p"))
    f_crop, s_crop = _s21(os.path.join(crop_dir, "results.s2p"))
    assert len(f_full) == len(f_crop), (len(f_full), len(f_crop))
    ds = np.abs(s_full - s_crop)
    print("S21 difference: max %.3f dB at %.2f GHz"
          % (ds.max(), f_full[int(np.argmax(ds))] / 1e9))
    assert ds.max() < MAX_DS21_DB, \
        "the crop changed S21 by %.3f dB" % ds.max()

    z_full, z_crop = _z0(rigsolve.lines(full_dir)), _z0(rigsolve.lines(crop_dir))
    if z_full and z_crop:
        z_full, z_crop = np.asarray(z_full), np.asarray(z_crop)
        dz = np.abs(z_crop - z_full) / np.maximum(np.abs(z_full), 1e-9)
        print("Z0 difference: max %.2f%%" % (100.0 * dz.max()))
        assert dz.max() < MAX_DZ0, \
            "the crop changed Z0 by %.2f%%" % (100.0 * dz.max())
    else:
        print("no lines.json: the Z0 check is skipped")
    print("PASS")


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["coarse"]))
