import os

def dvfm_packages():
    d = os.path.dirname(os.path.abspath(__file__))
    return {
        'orfs.nangate45': os.path.join(d, "flow.dv"),
    }
