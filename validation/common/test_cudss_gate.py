"""Tests of the cuDSS memory gate with the numbers of the 2026-11-07 runs.

**The gate compares the cuDSS estimate with the memory that is free after
the analysis, not with the memory at the start of the run.** The numbers
come from three real runs: the 111,917-tet bpf3 board (device only), the
138,354-tet WalkieTalkie board (hybrid), and the 160,919-tet board of the
pasted log (hybrid, host too large).

Run it with a python that has numpy and psutil:

    python test_cudss_gate.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # the repository
sys.path.insert(0, os.path.join(ROOT, "plugins"))

import emerge_runner as er  # noqa: E402

GIB = 1024**3


class Iface:
    pass


def estimates(device, host):
    est = np.zeros(16, dtype=np.int64)
    est[1] = int(device * GIB)
    est[3] = int(host * GIB)
    return est


def gate(device, host, limit, free, hybrid, available, cap):
    iface = Iface()
    iface._rfsim_estimates = estimates(device, host)
    iface._rfsim_device_limit = int(limit * GIB)
    iface._rfsim_device_free = int(free * GIB)
    iface._rfsim_device_total = int(7.53 * GIB)
    iface._rfsim_hybrid_state = "on" if hybrid else "off"
    er._cudss_host_budget = lambda: (
        min(int(cap * GIB), int(available * GIB) - GIB),
        int(available * GIB))
    old_cap = er.CUDSS_HOST_LIMIT_GB
    er.CUDSS_HOST_LIMIT_GB = cap
    try:
        er._cudss_gate(iface)
    finally:
        er.CUDSS_HOST_LIMIT_GB = old_cap


def fails(fn, text):
    try:
        fn()
    except SystemExit as e:
        assert text in str(e), str(e)
        return
    raise AssertionError("the gate did not stop")


# 111,917 tets: the factors fit in the 5.68 GiB budget of the free VRAM
# after the analysis, thus the device path is kept.
gate(5.51, 0.0, 5.68, 5.93, False, 17.0, 10.0)

# 138,354 tets: the old gate accepted 5.69 GiB against the stale 6.22 GiB
# budget, and the numeric phase failed. The new budget is 5.43 GiB.
fails(lambda: gate(5.69, 0.0, 5.43, 5.69, False, 17.0, 10.0),
      "device memory")

# The same board in hybrid mode moves the overflow to the host; it fits
# with the group of 4 matrices and a 12 GiB ceiling.
gate(5.43, 10.89, 5.43, 5.69, True, 13.8, 12.0)

# The 160,919-tet board needs 13.2 GiB of host RAM, above the 10 GiB cap.
fails(lambda: gate(5.43, 12.9, 5.43, 5.43, True, 17.0, 10.0),
      "cap of CUDSS_HOST_LIMIT_GB")

print("all cuDSS gate tests OK")
