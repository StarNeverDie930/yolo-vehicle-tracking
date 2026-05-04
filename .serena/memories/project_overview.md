# 项目概览

- 项目目的：基于 YOLOv11 + Deep SORT 实现车辆目标检测、多目标跟踪、轨迹可视化、车辆计数、分车型统计、近 1 分钟流量统计、热力图和视频导出，并提供 PySide6 桌面 GUI。
- 主要技术栈：Python 3.10+、ultralytics/YOLO、torch、deep-sort-realtime、OpenCV、NumPy、PySide6、PyYAML、motmetrics、matplotlib。
- 主要结构：`main.py` 为 GUI 入口；`core/` 放检测器、跟踪器、处理流水线；`analysis/` 放计数、轨迹、热力图；`app/` 放 PySide6 界面；`utils/` 放视频读写与绘图；`scripts/` 放数据转换、合并、训练、模型比较；`evaluation/` 放检测与跟踪评估；`docs/` 包含毕业设计任务书、开题报告和中期答辩 PPT，但被 `.gitignore` 忽略。
- 当前文档注意：`docs/` 实际目录名是复数，不是 `doc/`。当前工具不能直接解析项目中的 `.docx/.doc` 内容。