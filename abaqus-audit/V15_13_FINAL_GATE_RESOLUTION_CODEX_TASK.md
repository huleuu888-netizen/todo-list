# V15.13 FINAL GATE RESOLUTION CODEX TASK

## 基准

基于当前模型：

Commit:

`53776cadf26aa06ba62383e0758eda4e02a936e2`

分支：

`abaqus-audit-task`

目标：

完成 V15.13 最终验收，不创建 V15.14。

禁止：

- 修改 main；
- force push；
- 重新建立主体模型；
- 重新设计已经通过验证的防渗体系。

---

# 当前已完成部分（禁止破坏）

以下内容已经通过：

## 防渗体系

- 左岸80 m防渗墙延伸；
- 左副坝防渗墙；
- 安装间/厂房防渗墙；
- 生态放水段连接；
- 泄洪闸防渗过渡；
- 主防渗墙；
- 土工膜连接。

不要重新修改。

---

# 第一项：基础13个Component最终判定

当前：

Foundation component count = 13

不要强行合并。

生成：
```text
v15_13_foundation_component_resolution.csv
```

每个Component输出：

- ID
- 元素数量
- 坐标范围
- 材料
- Section
- 是否属于连续渗流域
- 分类

分类必须为：

- INTENDED_SEPARATE_DOMAIN
- DIFFERENT_MATERIAL_CONFORMAL_INTERFACE
- EXTERNAL_BOUNDARY
- SAME_DOMAIN_MESH_DISCONNECT
- UNRESOLVED

如果：

SAME_DOMAIN_MESH_DISCONNECT

必须修复。

---

# 第二项：基础拓扑最终检查

生成：
```text
v15_13_foundation_topology_final.csv
```

重新计算：

- hanging nodes
- nonconforming faces
- duplicate nodes
- duplicate elements
- non-manifold faces
- positive-volume overlap

连续渗流区域要求：
```java
hanging nodes = 0

nonconforming faces = 0

duplicate elements = 0

positive-volume overlap = 0
```

禁止输出：

- NOT_COMPUTED
- NOT_PROVEN

---

# 第三项：右岸防渗帷幕处理

当前：

UNRESOLVED

不要随意创建混凝土墙。

生成：
```text
v15_13_right_bank_curtain_resolution.csv
```

明确：

- 是否采用等效低渗区域；
- 是否采用边界条件；
- 是否暂不进入当前模型。

---

# 第四项：泄洪闸—主坝过渡

当前：

重力挡墙缺少可靠尺寸。

生成：
```text
v15_13_spillway_transition_resolution.csv
```

要求：

检查：

- 是否已有模型部件；
- 是否缺失；
- 是否影响渗流计算。

禁止：

没有依据时自行生成挡墙尺寸。

---

# 第五项：岩体渗透参数整理

当前问题：

部分岩体没有可靠k值。

生成：
```text
v15_13_rock_hydraulic_parameter_basis.csv
```

分类：

## VERIFIED_SOURCE

有明确来源。

## ENGINEERING_ASSUMPTION

工程等效。

## CALIBRATION_REQUIRED

后续标定。

禁止：

- 随意给花岗岩k值；
- 随意将Lu转换成k；
- 全模型C3D8R转换C3D8P。

---

# 第六项：回填材料最终确认

当前：

Q3AL_III

生成：
```text
v15_13_backfill_material_final_basis.csv
```

状态：

- VERIFIED_SOURCE_MAPPING
- ENGINEERING_EQUIVALENT_ASSUMPTION
- UNRESOLVED

---

# 第七项：重新生成Pre-Data-Check Gate

生成：
```text
v15_13_pre_datacheck_gate.csv
```

分成：

## Geometry Solver Readiness

检查：

- 网格；
- 连通；
- 单元；
- Section；
- Material。

## Production Seepage Readiness

检查：

- 渗透参数；
- 水力模型。

不要混合。

---

# 第八项：Abaqus Data Check

只有：
```text
Geometry Solver Readiness = PASS
```

才允许运行。

输出：

- dat
- msg
- sta

生成：
```text
v15_13_datacheck_issue_register.csv
```

记录：

- ERROR
- WARNING
- 单元错误
- 材料错误
- 孔压问题

---

# 最终报告

更新：
```text
V15_13_FINAL_SEEPAGE_DOMAIN_RESULT.md
```

第一行必须：

以下之一：
```ini
FINAL_STATUS = GEOMETRY_READY_HYDRAULICS_UNRESOLVED
```

或
```ini
FINAL_STATUS = DATACHECK_COMPLETED_WITH_ISSUES
```

或
```ini
FINAL_STATUS = DATACHECK_CLEAN_SEEPAGE_READY
```

---

# 提交要求

提交：
```text
abaqus-audit-task
```

禁止：

- 修改main；
- force push。

返回：

1. commit SHA  
2. 修改文件列表  
3. FINAL_STATUS  
4. Geometry Solver Readiness  
5. Production Seepage Readiness  
6. Data Check结果  
7. 剩余问题
