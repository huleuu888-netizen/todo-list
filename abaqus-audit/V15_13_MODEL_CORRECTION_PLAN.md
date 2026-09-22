# V15.13 多布水电站有限元模型修改方案

## 1. 修改目标

针对 `doub_hydropower_part25_geometric_solids_v15_13_S00_BASELINE_SEEPAGE.inp` 与多布水电站工程资料对应性检查结果，开展模型结构、材料和渗流计算闭合修正。

## 2. 主要修改内容

### 2.1 坝基深厚覆盖层分层优化

当前模型中的 `FOUNDATION_GEOLOGY` 需要进一步细化，避免将实际工程中的多层覆盖层简化为单一材料区域。

建议划分：

- FOUNDATION_LAYER_01：冲积含漂石砂卵砾石层
- FOUNDATION_LAYER_02：冲积含砾砂层
- FOUNDATION_LAYER_03：冲积中细、粉细砂层
- FOUNDATION_LAYER_04：冲积含块石砂卵砾石层

各层分别赋予对应的：

- 密度
- 弹性模量
- 泊松比
- 渗透系数

## 3. 材料映射闭合检查

建立 Part-Section-Material 对应表：

|工程区域|模型区域|材料|
|-|-|-|
|坝体砂砾料|DAM_SHELL|DAM_SAND_GRAVEL|
|坝体堆石区|ROCKFILL|DAM_ROCKFILL|
|反滤层|FILTER_LAYER|DAM_FILTER|
|排水层|DRAINAGE_LAYER|DAM_DRAINAGE|
|防渗墙|CUT_OFF_WALL|FANGSHENQIANG|
|坝基覆盖层|FOUNDATION_LAYER|对应地层材料|

## 4. 防渗体系检查

重点检查：

- 防渗墙是否贯穿坝体；
- 防渗墙与坝基是否连续连接；
- 接触区域是否存在渗流断点。

## 5. 渗流计算检查

检查：

- C3D8P、C3D6P 单元连续性；
- 孔压自由度是否覆盖计算区域；
- 上下游水头边界是否符合设计工况；
- 排水边界是否合理。

## 6. 修改顺序

1. 完成坝基覆盖层重新分区；
2. 完成材料参数重新映射；
3. 自动检查 Part-Section-Material 关系；
4. 重新运行 S00_BASELINE_SEEPAGE；
5. 输出模型一致性检查报告。

## 7. 后续版本目标

形成 V15.14 修正版模型，实现：

- 工程结构对应；
- 材料参数对应；
- 渗流路径连续；
- 计算状态可复核。
