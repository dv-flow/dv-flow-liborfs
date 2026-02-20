import os

def dvfm_packages():
    liborfs_dir = os.path.dirname(os.path.abspath(__file__))
    return {
        'orfs': os.path.join(liborfs_dir, "flow.dv"),
    }
