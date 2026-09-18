# V15 appurtenance rebuild scope

- Read-only mechanical baseline: `3d-v14/doub_hydropower_part25_geometric_solids_v14_design_aligned.inp`.
- v12/v13/v14 files are not overwritten; all new outputs are under `3d-v15/`.
- Legacy parts were inventoried from v12; v14 retained their Part definitions but suppressed their Instances.
- Rebuilt active systems: four bulb powerhouse units, installation bay, tailwater channel, eight spillway bays plus walls/basin, and two ecological-release bays.
- Geometry is structured C3D8R concrete and documents the source dimensions. Detailed reinforcement, gates, internal water passages and exact surveyed excavation surfaces were not present in the available deck; those details remain explicitly unresolved.
- Support is surface-based Tie only where an existing left-bank geology face was selected by footprint/elevation. No artificial nodal restraint, Encastre or spring was generated.
- The required order is preserved in global Y: spillway (20..129) -> ecological release (-15..10) -> powerhouse (-122..-15.4), with installation bay to the left and tailwater downstream in X.
- Source: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v14\doub_hydropower_part25_geometric_solids_v14_design_aligned.inp`; source active instances: 48; new active instances: 19.
