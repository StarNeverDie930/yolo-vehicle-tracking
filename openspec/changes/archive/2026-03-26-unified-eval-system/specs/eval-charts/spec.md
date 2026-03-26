## 新增需求

### 需求:检测评估生成图表
系统必须在 detect 或 both 模式下，在结果目录中生成 `map_bar.png`（各类 mAP@0.5 柱状图）。

#### 场景:map_bar.png 生成
- **当** 检测评估完成后
- **那么** 结果目录中存在 `map_bar.png`，展示每个类别的 mAP@0.5 数值

### 需求:跟踪评估生成图表
系统必须在 track 或 both 模式下，在结果目录中生成 `tracking_bar.png`（MOTA/IDF1/MT/ID Switch 柱状图）。

#### 场景:tracking_bar.png 生成
- **当** 跟踪评估完成后
- **那么** 结果目录中存在 `tracking_bar.png`，展示 MOTA、IDF1、MT 和 ID Switch 指标

### 需求:图表生成失败不中断评估
若 matplotlib 不可用或图表生成出错，系统禁止因此中断评估流程，summary.txt 必须正常写入。

#### 场景:matplotlib 异常时降级
- **当** 图表生成抛出异常
- **那么** 系统捕获异常并打印警告，继续完成 summary.txt 写入

## 修改需求

## 移除需求
