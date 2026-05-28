## 上下文

现状里越线计数已经有基本入口：

- `analysis/counter.py` 的 `VehicleCounter` 接收 `mode="unique_track" | "line_crossing"`。
- `core/pipeline.py` 会从 `config.yaml` 读取 `counter.mode`、`line_position` 和 `direction`。
- `core/pipeline.py` 在 `line_crossing` 模式下会绘制计数线。
- `app/main_window.py` 已连接 `line_pos_changed`，但 `app/control_panel.py` 没有创建对应控件。

这说明当前问题不是从零实现算法，而是把后端计数语义、GUI 操作入口和结果展示补成闭环。

## 目标 / 非目标

**目标：**

- 让用户能在 GUI 中切换 `unique_track` 和 `line_crossing`。
- 让用户能在 GUI 中配置水平/垂直检测线和检测线位置。
- 让越线计数只在车辆中心点跨过检测线时发生，并避免同一轨迹重复计数。
- 让统计面板和画面标注能反映当前计数模式。
- 保持原有默认 ID 去重计数行为不变。
- 为核心计数逻辑补充小型、确定性测试。

**非目标：**

- 不引入多条检测线。
- 不实现方向性车流统计，例如只统计从上到下或从左到右。
- 不做人机交互式拖拽画线。
- 不改动 YOLO、Deep SORT 或训练流程。
- 不引入新的 GUI 框架或外部依赖。

## 设计决策

### 决策 1: 保留单一 `VehicleCounter`，用模式区分语义

继续让 `VehicleCounter` 负责两种计数模式：

- `unique_track`：首次看到合法车辆 `track_id` 时计数。
- `line_crossing`：记录每个 `track_id` 的上一帧中心点，只有中心点从检测线一侧移动到另一侧时计数。

这样可以复用现有 `count`、`get_class_counts()`、`get_flow_rate()` 和分析导出逻辑，避免把统计状态拆散到 GUI 或 pipeline 层。

### 决策 2: 越线判定使用“跨越线段两侧”而不是“触线即计数”

当前实现使用：

```python
(previous - line_value) * (current - line_value) <= 0
```

这会把中心点刚好落在线上也视为 crossing，容易在抖动或连续贴线时产生误判。实现时应改成更明确的侧别变化：

- 根据 `direction` 取中心点的 x 或 y 坐标。
- 计算该坐标相对检测线的位置。
- 只有上一帧和当前帧处于检测线两侧时计数。
- 如果某一帧刚好在线上，可以记录当前位置，但不单独触发计数；下一帧进入另一侧时再根据最近有效侧别判断。
- `track_id` 一旦进入 `_seen`，后续重复跨线不再增加总数。

这会让越线计数更保守，但更符合“穿越虚拟检测线”的直觉。

### 决策 3: 模式和参数变更需要重置当前计数状态

计数模式、方向或检测线位置改变后，已经累计的数据不再具备同一语义。GUI 在空闲状态下允许用户修改这些参数，修改时应同步：

- `self.config["counter"]`
- `self.pipeline.counter.mode`
- `self.pipeline.counter.direction`
- `self.pipeline.counter.line_position`
- 必要时调用 `counter.reset()`，避免旧模式数据混入新模式结果。

处理或导出进行中沿用现有 busy 状态禁用控制面板，不允许运行中切换。

### 决策 4: GUI 控件放在现有 `ControlPanel`

在模型、置信度和 IoU 设置附近新增一组计数配置：

- `计数模式` 下拉框：`按 ID 去重计数`、`越线计数`。
- `越线方向` 下拉框：`水平线`、`垂直线`。
- `越线位置` 数值控件或滑块：范围建议为 `0.05` 到 `0.95`，默认读取 `config.yaml`。

当计数模式为 `unique_track` 时，越线方向和越线位置控件禁用；切到 `line_crossing` 时启用。控件通过 signal 通知 `MainWindow`，由 `MainWindow` 同步 pipeline。

### 决策 5: 统计面板文案跟随当前模式

`ResultPanel` 当前固定显示 `车辆总数`。实现时应支持模式文案：

- `unique_track`：显示 `车辆总数` 或 `累计车辆数`。
- `line_crossing`：显示 `越线车辆数` 或 `通过车辆数`。

流量窗口统计仍使用当前计数模式下的 `_flow_log`。因此在 `line_crossing` 模式下，流量窗口表示最近 N 秒越线车辆数；在 `unique_track` 模式下，表示最近 N 秒首次出现车辆数。

### 决策 6: 检测线可视化保持轻量

`core/pipeline.py` 已经在 `line_crossing` 模式调用 `draw_count_line()`。实现时应继续复用这个路径，并确保：

- 线的位置来自当前 counter 参数。
- 水平线和垂直线都能正确绘制。
- 导出视频与实时预览使用同一套标注。

如果需要更清楚的提示，可以在画面角落或线附近增加短文本，但不作为本次必要范围。

## 风险 / 权衡

- **贴线车辆的边界判定**：更保守的侧别变化可能不统计只触线但未穿过的轨迹，这是预期行为。
- **跟踪 ID 稳定性依赖**：越线计数仍依赖 Deep SORT 的 `track_id` 连续性，ID switch 可能导致重复计数。这是跟踪系统的固有限制，本次只保证同一 `track_id` 不重复计数。
- **运行中修改参数**：为避免统计语义混乱，处理期间禁用计数控件，延续现有控制面板 busy 规则。
- **测试环境缺少 GUI 自动化**：核心逻辑优先用纯 Python 单元测试覆盖，GUI 部分以信号连接和手工验证为主。
