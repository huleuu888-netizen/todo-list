# V15.13 多布水电站有限元模型工程对应性审计与修改方案

## 1. 审计对象

模型：`doub_hydropower_part25_geometric_solids_v15_13_S00_BASELINE_SEEPAGE.inp`

目标：根据多布水电站工程地质资料，对有限元模型的几何结构、材料分区和渗流体系进行一致性检查。

## 2. 已确认内容

- 模型采用砂砾石复合坝结构框架。
- 已建立坝体分区、反滤层、排水结构和防渗墙结构。
- 已包含 S00_BASELINE_SEEPAGE 渗流分析步骤。

## 3. 当前需要修改的问题

### 3.1 坝基覆盖层分层不足

工程实际坝基存在多层覆盖层，模型中的 FOUNDATION_GEOLOGY 需要进一步拆分。

建议建立：

- FOUNDATION_LAYER_01
- FOUNDATION_LAYER_02
- FOUNDATION_LAYER_03
- FOUNDATION_LAYER_04

分别对应不同覆盖层材料，并赋予对应的密度、弹性参数和渗透系数。

### 3.2 材料映射闭合检查

建立 Part-Section-Material 对照表：

|区域|材料|
|-|-|
|坝体砂砾料|DAM_SAND_GRAVEL|
|反滤层|DAM_FILTER|
|排水层|DAM_DRAINAGE|
|防渗墙|FANGSHENQIANG|
|坝基覆盖层|对应分层材料|

检查每个 Part 是否正确调用 Section 和 Material。

### 3.3 模型命名统一

当前模型名称包含 geometry-only 描述，但实际包含渗流分析步骤。

建议统一命名为：

`V15_13_BASELINE_SEEPAGE_MODEL`

### 3.4 渗流连续性检查

后续检查：

- C3D8P/C3D6P 孔压单元连续性；
- 防渗墙与坝基接触关系；
- 上下游水头边界；
- 排水出口边界。

## 4. 修改优先级

1. 完成坝基覆盖层分层；
2. 完成材料区域映射；
3. 校核渗流单元连续性；
4. 重新运行 S00_BASELINE_SEEPAGE。

## 5. Commit

Audit V15.13 Doubo hydropower model correspondence
