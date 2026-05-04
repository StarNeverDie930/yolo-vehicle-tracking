## 为什么

任务书和开题报告已经明确了毕业设计的验收边界：基于 YOLOv11 + DeepSORT 的车辆检测、轨迹跟踪、交通流量统计、热力图和视频导出，并要求在公开数据集和自采视频上验证精度、稳定性和实时性。当前仓库的主干功能已经具备，但存在几类对照性问题：类别命名在转换、统计、绘制、配置和文档之间不一致；计数与热力图的语义和论文表述存在偏差；评估结果覆盖不足；README、代码与论文 markdown 的框架表述不一致；`docs/` 被整目录忽略，新的 markdown 文档不一定会进入版本控制；视频处理路径缺少显式异常反馈。

这些问题不影响“能跑”，但会直接影响毕业设计答辩时的可解释性和可信度。

## 变更内容

- 统一车辆类别 taxonomy，消除 detector、tracker、counter、drawing、dataset yaml、README 和论文文档中的多套类名定义。
- 明确车辆累计计数、越线流量统计与热力图的语义边界，并让流量窗口基于视频时间而不是系统壁钟。
- 增加热力图保存能力，支持保存原始热力图和叠加到视频帧上的可视化结果。
- 扩展除热力图外的交通分析结果，包括车型结构、分时段流量、轨迹摘要、热点区域排名和处理性能摘要。
- 扩展评估与报告输出，覆盖公开序列、自采视频、运行时长、FPS、模型路径和完整指标摘要。
- 同步 README 与 `docs/任务书.md`、`docs/开题报告.md` 中的框架名称、功能描述和验收表述。
- 调整仓库忽略规则，使 Markdown 版毕业设计文档可被版本化管理。
- 为视频读取、导出和处理线程增加可见错误处理与 UI 状态恢复。

## 功能 (Capabilities)

### 新增功能

- `vehicle-taxonomy`: 统一四类车辆 taxonomy 的来源、映射和展示
- `traffic-flow-and-heatmap`: 明确计数模式、流量统计窗口与热力图累计逻辑
- `analysis-outputs`: 保存热力图，并生成车型结构、流量趋势、轨迹摘要、热点区域和处理性能等分析结果
- `evaluation-and-reporting`: 扩展单序列/批量评估、摘要报告和运行时指标
- `documentation-sync`: 同步 README、任务书、开题报告与仓库忽略规则
- `processing-stability`: 视频处理和导出路径的异常处理、失败反馈与 UI 恢复

## 影响

- `core/detector.py`
- `core/tracker.py`
- `core/pipeline.py`
- `analysis/counter.py`
- `analysis/trajectory.py`
- `analysis/heatmap.py`
- `utils/drawing.py`
- `utils/video_io.py`
- `app/main_window.py`
- `app/control_panel.py`
- `app/result_panel.py`
- `config.yaml`
- `scripts/convert_detrac_to_yolo.py`
- `scripts/merge_datasets.py`
- `scripts/detrac.yaml`
- `scripts/merged.yaml`
- `evaluation/eval_all.py`
- `README.md`
- `.gitignore`
- `docs/任务书.md`
- `docs/开题报告.md`
