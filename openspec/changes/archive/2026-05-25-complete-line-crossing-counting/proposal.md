## 为什么

当前代码已经在 `VehicleCounter` 中保留了 `unique_track` 和 `line_crossing` 两种计数模式，`config.yaml` 也提供了 `counter.mode`、`line_position` 和 `direction` 配置。但 GUI 控制面板没有暴露计数模式切换、越线方向和越线位置入口，导致用户只能通过手改配置尝试越线计数。

同时，现有越线判定逻辑只做了中心点相对检测线的符号变化判断，缺少 GUI 状态同步、模式切换时的重置语义、结果面板文案区分和可验证的测试覆盖。用户从界面上看不到“当前是 ID 去重计数还是越线计数”，也无法直观调整虚拟检测线。

这次变更要把越线计数从“代码里有雏形”补完整为“界面可用、逻辑明确、结果可解释”的功能。

## 变更内容

- 在控制面板中新增计数模式入口，允许用户在 `按 ID 去重计数` 与 `越线计数` 之间切换。
- 在越线计数模式下暴露越线方向和越线位置配置，并让界面状态、运行配置和 `VehicleCounter` 实例保持同步。
- 完善越线判定逻辑，确保车辆中心点真正从检测线一侧移动到另一侧时才计数，同一个 `track_id` 只计一次。
- 在视频画面中绘制当前检测线，并在统计面板中区分累计车辆数和越线通过数的显示语义。
- 保持默认模式为 `unique_track`，避免影响现有累计计数行为。
- 补充轻量验证，覆盖 ID 去重、水平越线、垂直越线、未越线不计数、同一轨迹重复跨线不重复计数和 GUI 参数同步。

## 功能 (Capabilities)

### 新增功能

- `traffic-flow-and-heatmap`: 完整化 `line_crossing` 计数模式的判定、重置和可视化语义。
- `gui-processing-lifecycle`: 在 GUI 控制面板中暴露计数模式、越线方向和越线位置，并与后台处理状态互斥。

## 影响

- `analysis/counter.py`
- `core/pipeline.py`
- `utils/drawing.py`
- `app/control_panel.py`
- `app/main_window.py`
- `app/result_panel.py`
- `config.yaml`
- `tests/`
