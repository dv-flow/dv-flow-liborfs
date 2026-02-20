.. DV Flow LibORFS documentation master file

###############
DV Flow LibORFS
###############

LibORFS is a DV-Flow library that wraps each stage of the OpenROAD RTL-to-GDSII flow
as cacheable, composable DFM tasks.  Each stage — synthesis, floorplan, placement,
CTS, global routing, detailed routing, and sign-off — is a separate task node so that
DFM can cache per-stage outputs and re-run only what has changed.

.. contents::
    :depth: 2

.. mdinclude:: Tasks.md
