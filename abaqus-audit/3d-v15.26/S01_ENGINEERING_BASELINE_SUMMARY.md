# S01 Engineering Baseline Summary

## Scope

This report defines the S01 intact-model engineering baseline for later S02-S07 comparisons. It is a read-only aggregation of the completed V15.24 S01 response and V15.25 gradient validation. No geometry, mesh, material, boundary condition, input deck, or Abaqus model was modified. S02-S07 were not run.

- V15.24 source report: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.24\V15.24_S01_BASELINE_RESULT_REPORT.md`
- V15.24 flow summary: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.24\S01\S01_flow_rate.csv`
- V15.25 regional gradient statistics: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.25\regional_gradient_statistics.csv`

## Baseline response

| 指标 | 区域 | 数值 | 单位 | 状态 |
|---|---|---:|---|---|
| 总渗流量 Q | 全模型 | `265.859330922` | model volume/time units | COMPUTED |
| 最大水头 | 全模型 | `3412.0875296` | model length units | COMPUTED |
| P95 水力梯度 | 防渗墙 | `21.9071698856` | model head/length units | COMPUTED |
| P95 水力梯度 | 坝基覆盖层 | `1.04567360088` | model head/length units | COMPUTED |
| P95 水力梯度 | 岩体 | `1.16710603126` | model head/length units | COMPUTED |
| P95 水力梯度 | 过滤层 | `344254.635291` | model head/length units | COMPUTED |

Q is the V15.24 `total_Q_magnitude`, obtained from the scoped downstream RVF integration. Maximum head is the V15.24 POR-derived hydraulic-head maximum. Regional P95 values are copied from the V15.25 computed-gradient population; unresolved local-geometry rows are excluded from each percentile and retained in the CSV audit columns.

## Engineering use and limitations

- Use this file as the intact S01 comparison baseline for later defect or degradation cases.
- The filter-layer P95 gradient is `344254.635291`; V15.25 classified the associated high-gradient cluster as a localized numerical peak, not a confirmed engineering control gradient.
- The baseline retains the V15.24 output limitations: gradient values were reconstructed from POR and mesh topology, not read from a native Abaqus hydraulic-gradient field; unresolved local-geometry rows remain documented.
- Do not compare later cases against a silently revised baseline. Any output-definition or mesh change requires a new explicitly labeled baseline.

Machine-readable summary: `D:\Backup\Documents\ChatGPT\多步水电站\todo-list\abaqus-audit\3d-v15.26\regional_hydraulic_response_baseline.csv`
