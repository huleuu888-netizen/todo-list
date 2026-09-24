# S01 Final Design Correspondence Audit

FINAL_DESIGN_CORRESPONDENCE_STATUS = PARTIAL

## Scope

This is a read-only correspondence audit of the V15.26 S01 baseline against the eight final seepage-design requirements supplied for the 多布水电站. It uses the unchanged V15.24 S01 input retained as the V15.26 model-object source. No model, input deck, mesh, material, boundary condition, or Abaqus result was modified. Abaqus was not run.

- Source input: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.24\S01\v15_24_S01_BASELINE.inp`
- S01 baseline summary: `abaqus-audit/3d-v15.26/S01_ENGINEERING_BASELINE_SUMMARY.md`
- Prior study mapping: `abaqus-audit/study-design/case_parameter_mapping_v1.md`
- Machine-readable audit: `S01_FINAL_DESIGN_MAPPING.csv`

## Eight-item result

| Item | Requirement | Status |
|---:|---|---|
| 1 | 坝体采用复合土工膜防渗 | **PARTIAL** |
| 2 | 主河床及左岸覆盖层基础采用悬挂式混凝土防渗墙 | **PASS** |
| 3 | 左岸防渗墙延伸 80 m | **PASS** |
| 4 | 防渗墙厚度 1.0 m | **PASS** |
| 5 | 河床防渗墙墙底约 3021.00 m，最大施工深度约 49.10 m | **PARTIAL** |
| 6 | 右岸岩石基础采用灌浆帷幕 | **MISSING** |
| 7 | 右岸帷幕向岸内延伸 100 m | **MISSING** |
| 8 | 防渗墙与上部复合土工膜、右岸灌浆帷幕连续连接 | **PARTIAL** |

## Confirmed geometry and object evidence

### Main cutoff wall: V15_5_REFINED_P25_SOLID_CUTOFF_WALL_F13_1 / P25_SOLID_CUTOFF_WALL_F13-1

- Material: `P25_FANGSHENQIANG`; element set: `V15_5_ALL`; current scalar permeability: `1e-08`.
- global bbox min=(-35.99999999999999, 150.00003833060384, 3020.9999999999995); max=(-35.0, 445.00003899685333, 3073.510003742975); span=(x=1.000000, y=295.000001, z=52.510004); elements=31376; unique_nodes=48411.
- Global bottom elevation: `3021.000000 m`; current vertical z-span: `52.510004 m`; current longitudinal y-span: `295.000001 m`.
- The required 49.10 m maximum construction depth is not directly reproduced by the current S01 wall geometry. Item 5 is therefore PARTIAL, not PASS.

### Anti-seepage chain: V15_13_ANTI_SEEPAGE_CHAIN / V15_13_ANTI_SEEPAGE_CHAIN_I

- Material: `P25_FANGSHENQIANG`; aggregate set: `V15_13_ANTI_SEEPAGE_ALL`; global bbox min=(-64.0, -325.7, 3011.0); max=(-19.0, 150.0, 3073.51); span=(x=45.000000, y=475.700000, z=62.510000); elements=10; unique_nodes=44.
- Confirmed named subsets in the current input:

| Element Set | Meaning | Global span / range check |
|---|---|---|
| `V15_13_LEFT_BANK_ABUTMENT_EXTENSION` | Left-bank 80 m extension | `global bbox min=(-64.0, -325.7, 3021.0); max=(-63.0, -245.7, 3059.0); span=(x=1.000000, y=80.000000, z=38.000000); elements=1; unique_nodes=8` |
| `V15_13_LEFT_SUBDAM_CUTOFF` | Left subdam cutoff | `global bbox min=(-64.0, -325.7, 3021.0); max=(-63.0, -156.0, 3059.0); span=(x=1.000000, y=169.700000, z=38.000000); elements=2; unique_nodes=12` |
| `V15_13_INSTALLATION_POWERHOUSE_CUTOFF`; `V15_13_POWERHOUSE_CUTOFF` | Installation bay / powerhouse | `global bbox min=(-64.0, -245.7, 3011.0); max=(-29.0, -25.4, 3059.0); span=(x=35.000000, y=220.300000, z=48.000000); elements=4; unique_nodes=20`; `global bbox min=(-30.0, -122.0, 3011.0); max=(-29.0, -15.4, 3051.5); span=(x=1.000000, y=106.600000, z=40.500000); elements=2; unique_nodes=12` |
| `V15_13_ECOLOGICAL_RELEASE_CONNECTION` | Ecological-release connection | `global bbox min=(-30.0, -25.4, 3011.0); max=(-19.0, 6.85, 3051.5); span=(x=11.000000, y=32.250000, z=40.500000); elements=3; unique_nodes=16` |
| `V15_13_SPILLWAY_CUTOFF`; `V15_13_SPILLWAY_MAIN_TRANSITION` | Spillway transition | `global bbox min=(-35.5, -2.9, 3021.0); max=(-19.0, 150.0, 3073.51); span=(x=16.500000, y=152.900000, z=52.510000); elements=3; unique_nodes=16`; `global bbox min=(-35.5, 93.6, 3021.0); max=(-19.0, 150.0, 3073.51); span=(x=16.500000, y=56.400000, z=52.510000); elements=1; unique_nodes=8` |

### Upstream geomembrane: V15_5_REFINED_V12_UPSTREAM_GEOMEMBRANE_1 / V12_UPSTREAM_GEOMEMBRANE-1

- Material: `GEOMEMBRANE`; element set: `V15_5_ALL`; current scalar permeability: `4.5e-11`.
- global bbox min=(-90.5, 150.0, 3055.0); max=(-36.0, 445.0, 3073.51); span=(x=54.500000, y=295.000000, z=18.510000); elements=2400; unique_nodes=5050.
- The low-permeability object exists, but the input provides one homogenized material/solid representation rather than an explicit multi-layer composite stack. This is why item 1 is PARTIAL rather than PASS.

## Right-bank curtain finding

The right-bank curtain is not present as a model object. Right-bank geology sets are present in `V15_7_FOUNDATION_GEOLOGY_I`, but no right-bank curtain Part, Instance, Material, or Element Set was identified. The current model therefore cannot demonstrate either the required grouting curtain or its 100 m inland extension.

```text
RIGHT_BANK_CURTAIN = MISSING
RIGHT_BANK_CURTAIN_100M_EXTENSION = MISSING
RIGHT_BANK_CONNECTION = UNRESOLVED
```

## Required modification plan if the design is to be completed

No modification was made in this audit. Before any S02-S07 run or revised S01, the following controlled work is required:

1. Obtain source-backed right-bank curtain alignment in global Assembly coordinates, including the start point, the 100 m inland endpoint, bottom elevation, thickness or equivalent-zone width, and tie-in to the right-bank geology.
2. Create a dedicated right-bank curtain Part/Instance and element set, or an explicitly approved equivalent low-permeability geology domain. Assign a source-backed material and permeability; do not relabel existing geology as a curtain.
3. Define the upper curtain connection to the composite geomembrane and the lateral connection to the existing anti-seepage chain using conformal geometry/shared nodes where feasible. Do not use an unsupported Tie, fixed node, spring, or Encastre to hide a geometry gap.
4. Rebuild only the affected local mesh, then verify positive volume, duplicate elements, nonconforming faces, hanging nodes, and interface continuity. Preserve the V15.26 S01 baseline as an immutable comparison case.
5. Re-run the design-correspondence audit and only then decide whether a new analysis input is authorized.

The left-bank 80 m extension does not require this missing-geometry plan: its existing named set has a measured 80.000000 m global span and is marked PASS.

## Final readiness

The current S01 model contains the main cutoff, anti-seepage chain, left-bank 80 m extension, 1.0 m wall thickness, and a 3021.0 m wall-bottom datum. The current wall geometry does not directly reproduce the stated 49.10 m maximum construction depth. It also does not contain the right-bank curtain or a proven global three-way connection to the geomembrane and right-bank curtain. Therefore the final engineering design correspondence is PARTIAL, and no S02 run should start from this audit alone.
