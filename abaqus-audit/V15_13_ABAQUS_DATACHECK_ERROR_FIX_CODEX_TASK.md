# V15.13 ABAQUS DATACHECK ERROR FIX CODEX TASK

## 1. 基准

当前模型：

Commit:

028e372114ca42ff3ebf3451f43bae5cf59c7d21

分支：

abaqus-audit-task

目标：

修复 Abaqus Data Check 阶段错误，使 V15.13 模型进入可计算状态。

禁止：

- 创建 V15.14；
- 修改 main；
- force push；
- 重新建立主体模型；
- 破坏已经通过验证的防渗体系和基础拓扑。

---

# 2. 当前已经通过部分（禁止破坏）

以下内容已经完成：

## 防渗体系

- 左岸80 m防渗延伸；
- 左副坝防渗墙；
- 安装间/厂房防渗墙；
- 生态放水连接；
- 泄洪闸过渡；
- 主防渗墙；
- 土工膜连接。

## 基础拓扑

当前：

- hanging nodes = 0
- nonconforming faces = 0
- duplicate nodes = 0
- duplicate elements = 0
- positive-volume overlap = 0

后续修改必须保持这些结果。

---

# 3. Task 1：修复异常单元

当前 Abaqus Data Check：

发现：

- zero volume elements；
- small volume elements；
- negative volume elements。

数量：

3042。

首先定位所有异常单元。

生成：

```text
v15_13_bad_element_location.csv
```

必须包含：

- Element label
- Part
- Instance
- Element set
- Material
- Section
- Coordinates
- Error type

分类：

- ZERO_VOLUME
- NEGATIVE_VOLUME
- COLLAPSED_ELEMENT
- EXTREME_DISTORTION

重点检查区域：

1. 土工膜—防渗墙连接区域；
2. 3011/3021高程过渡区域；
3. 左岸80 m延伸区域；
4. 回填—地质融合区域。

---

# 4. Task 2：局部网格修复

禁止：

- 全模型重新划网；
- 改变坝体总体尺寸；
- 修改防渗墙轴线。

允许：

- 局部分区；
- 局部partition；
- 局部seed调整；
- 局部remesh。

修复后生成：

```text
v15_13_mesh_quality_after_fix.csv
```

要求：

所有活动单元：

- volume > 0；
- 无负体积；
- 无退化单元。

---

# 5. Task 3：修复 Initial Condition Node Set

当前错误：

Initial condition Node Set missing。

检查：

- Initial Step；
- Predefined Field；
- pore pressure initial condition；
- Node Set。

恢复正确节点集合。

生成：

```text
v15_13_initial_condition_audit.csv
```

包含：

- Field name
- Node Set
- Node count
- Step
- Status

---

# 6. Task 4：修复材料渗透率定义

当前问题：

部分材料：

- permeability缺失；
- permeability错误。

生成：

```text
v15_13_permeability_material_audit.csv
```

逐材料检查：

- Material name
- Section
- Element set
- permeability value
- Unit
- Source

分类：

## VERIFIED_SOURCE

有可靠来源。

## ENGINEERING_ASSUMPTION

明确工程假设。

## CALIBRATION_REQUIRED

需要后续标定。

禁止：

- 随意给岩体编写k值；
- 无依据Lu转换k；
- 全模型统一赋值。

---

# 7. Task 5：重新生成 Abaqus 输入并运行 Data Check

修复后重新生成：

- CAE；
- INP。

运行：

Abaqus Data Check。

保存：

- .dat
- .msg
- .sta

生成：

```text
v15_13_datacheck_issue_register.csv
```

记录：

- Error；
- Warning；
- Element问题；
- Material问题；
- Initial condition问题。

---

# 8. Task 6：更新最终报告

更新：

```text
V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md
```

第一行必须填写：

以下之一：

```ini
FINAL_STATUS = DATACHECK_COMPLETED_WITH_ISSUES
```

或

```ini
FINAL_STATUS = DATACHECK_CLEAN_HYDRAULICS_UNRESOLVED
```

或

```ini
FINAL_STATUS = DATACHECK_CLEAN_SEEPAGE_READY
```

---

# 9. 提交要求

提交到：

```text
abaqus-audit-task
```

禁止：

- 修改 main；
- force push。

Commit message：

```text
audit: fix v15.13 abaqus datacheck errors
```

提交后返回：

1. commit SHA；
2. push结果；
3. 修改文件列表；
4. 异常单元修复前后数量；
5. Data Check结果；
6. 剩余问题。
