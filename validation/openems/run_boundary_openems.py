"""Run `rig_boundary` with openEMS (F40).

The rig in `validation/common/rig_boundary.py` holds the board and the
checks. This file selects openEMS and puts the results into
`validation/openems/out_boundary_*`.

Start it with the python of KiCad 10:
    "%LOCALAPPDATA%\\Programs\\KiCad\\10.0\\bin\\python.exe" run_boundary_openems.py [coarse|medium|fine]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "common"))

import rigsolve  # noqa: E402

rigsolve.use("openems", HERE)

import rig_boundary  # noqa: E402

if __name__ == "__main__":
    rig_boundary.main(*(sys.argv[1:] or ["coarse"]))
