## 1. 完善越线计数核心逻辑

- [x] 1.1 梳理 `VehicleCounter` 的 `unique_track` 与 `line_crossing` 状态字段，明确 `_seen`、`_flow_log`、上一帧中心点或上一侧别的职责
- [x] 1.2 优化水平线和垂直线的 crossing 判定，避免中心点贴线或抖动导致误计数
- [x] 1.3 保证同一 `track_id` 在 `line_crossing` 模式下只记录一次，未越线轨迹不计数
- [x] 1.4 为模式、方向和线位置变更提供清晰的状态同步或重置入口

## 2. 补齐 GUI 控制入口

- [x] 2.1 在 `ControlPanel` 中新增计数模式下拉框，并从 `config.yaml` 初始化
- [x] 2.2 在 `ControlPanel` 中新增越线方向控件和越线位置控件，并根据计数模式启用或禁用
- [x] 2.3 增加 `count_mode_changed`、`line_direction_changed` 等必要 signal，复用或修正现有 `line_pos_changed`
- [x] 2.4 在 `MainWindow` 中连接这些 signal，同步 `self.config["counter"]` 与 `self.pipeline.counter`
- [x] 2.5 保持处理或导出期间控制面板禁用，避免运行中改变计数语义

## 3. 调整展示与导出语义

- [x] 3.1 在 `ResultPanel` 中根据当前计数模式显示 `累计车辆数` 或 `越线车辆数`
- [x] 3.2 确认 `line_crossing` 模式下实时预览和导出视频都会绘制检测线
- [x] 3.3 确认分析导出的 `counter_mode`、分车型统计和流量窗口统计与当前模式一致

## 4. 验证

- [x] 4.1 为 `VehicleCounter` 增加确定性测试：ID 去重计数
- [x] 4.2 为 `VehicleCounter` 增加确定性测试：水平越线计数
- [x] 4.3 为 `VehicleCounter` 增加确定性测试：垂直越线计数
- [x] 4.4 为 `VehicleCounter` 增加确定性测试：未越线不计数、同一轨迹重复跨线不重复计数
- [x] 4.5 手工启动 GUI，确认计数模式、方向、位置控件可见且可切换
- [x] 4.6 使用短视频或构造帧验证两种模式下统计文案和计数结果符合预期
