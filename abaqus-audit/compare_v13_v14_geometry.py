"""Compare v13 and v14 mesh coordinates without modifying either input deck."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "abaqus-audit"))
from repair_v12_3d import parse_deck  # noqa: E402

V13 = ROOT / "abaqus-audit" / "3d-v13" / "doub_hydropower_part25_geometric_solids_v13_rigidbody_geostatic_fixed.inp"
V14 = ROOT / "abaqus-audit" / "3d-v14" / "doub_hydropower_part25_geometric_solids_v14_design_aligned.inp"
OUT = ROOT / "abaqus-audit" / "3d-v14" / "v14_geometry_coordinate_compare.txt"


def bbox(nodes):
    xyz = [tuple(float(v) for v in n[0:3]) for n in nodes.values()]
    return tuple(min(p[i] for p in xyz) for i in range(3)) + tuple(max(p[i] for p in xyz) for i in range(3))


def main():
    _, parts13, _, _ = parse_deck(V13)
    _, parts14, _, _ = parse_deck(V14)
    parts = sorted(set(parts13) & set(parts14))
    changed = []
    rows = []
    for name in parts:
        n13 = parts13[name]["nodes"]
        n14 = parts14[name]["nodes"]
        labels = sorted(set(n13) | set(n14))
        local_changes = [label for label in labels if n13.get(label) != n14.get(label)]
        if local_changes:
            changed.append((name, local_changes))
        if name.startswith("P25_"):
            rows.append((name, len(n13), bbox(n13), len(n14), bbox(n14)))
    lines = [
        "V14_GEOMETRY_COORDINATE_COMPARE",
        f"V13_INPUT={V13}",
        f"V14_INPUT={V14}",
        f"COMMON_PARTS={len(parts)}",
        f"CHANGED_PARTS={len(changed)}",
        f"CHANGED_NODE_COORDINATES={sum(len(v) for _, v in changed)}",
        "GEOMETRY_COORDINATE_EDITS=0" if not changed else "GEOMETRY_COORDINATE_EDITS=1",
    ]
    if changed:
        for name, labels in changed:
            lines.append(f"CHANGED_PART={name};NODE_COUNT={len(labels)}")
    else:
        lines.append("CHANGED_PARTS_DETAIL=NONE")
    lines.append("P25_PART_BBOXES_LOCAL_XYZ_MINMAX:")
    for name, c13, b13, c14, b14 in rows:
        lines.append(f"{name};V13_NODES={c13};V13_BBOX={b13};V14_NODES={c14};V14_BBOX={b14}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OUTPUT={OUT}")
    print(f"CHANGED_PARTS={len(changed)}")
    print(f"CHANGED_NODE_COORDINATES={sum(len(v) for _, v in changed)}")


if __name__ == "__main__":
    main()
