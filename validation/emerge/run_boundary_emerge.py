"""Run `rig_boundary` with EMerge (F40).

The rig in `validation/common/rig_boundary.py` holds the board and the
checks. This file selects EMerge and puts the results into
`validation/emerge/out_boundary_*`.

Start it with the python of KiCad 10:
    "%LOCALAPPDATA%\\Programs\\KiCad\\10.0\\bin\\python.exe" run_boundary_emerge.py [coarse|medium|fine]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "common"))

import rigsolve  # noqa: E402

rigsolve.use("emerge", HERE)

import rig_boundary  # noqa: E402

if __name__ == "__main__":
    rig_boundary.main(*(sys.argv[1:] or ["coarse"]))
