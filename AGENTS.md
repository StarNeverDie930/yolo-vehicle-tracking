# Repository Guidelines

## 项目结构与模块组织

本仓库是基于 YOLOv11 + Deep SORT 的车辆检测、跟踪与交通流量分析系统，并提供 PySide6 桌面界面。代码调整应保持现有职责边界清晰：

- `main.py`：应用入口，启动 GUI 并读取 `config.yaml`。
- `core/`：检测器、跟踪器与处理流水线。
- `analysis/`：车辆计数、轨迹存储、热力图生成。
- `app/`：PySide6 主窗口、控件、结果面板与 `app/resources/style.qss`。
- `utils/`：视频读写、绘图等通用工具。
- `scripts/`：数据集转换、合并、训练与模型比较脚本。
- `evaluation/`：检测和跟踪评估脚本、MOT 数据与评估结果。
- `weights/`、`runs/` 和数据集目录通常体积较大，避免提交生成模型、原始数据或临时输出。

## 构建、测试与开发命令

- `pip install -r requirements.txt`：安装项目运行依赖。
- `python main.py`：启动本地桌面应用。
- `python kitti_to_yolo.py`：将 KITTI 标注转换为 YOLO 格式。
- `python scripts/merge_datasets.py`：合并 UA-DETRAC 与 KITTI 数据集。
- `python scripts/train.py --model runs/detrac_train/weights/best.pt --data scripts/merged.yaml --epochs 80 --name merged_train_v2`：训练自定义检测模型。
- `python evaluation/eval_all.py --seq MVI_20011 --mode both --model weights/best.pt`：运行检测与跟踪评估。

## 编码风格与命名规范

使用 Python 3.10+，遵循 PEP 8，统一使用 4 空格缩进。函数、变量和模块使用 `snake_case`，类名使用 `PascalCase`，内部辅助方法可使用前导下划线。GUI 代码放在 `app/`，核心处理逻辑放在 `core/`，统计与评估逻辑放在 `analysis/` 或 `evaluation/`。复杂处理步骤应补充简短 docstring，避免把业务逻辑混入界面层。

## 测试指南

当前仓库尚未配置独立单元测试套件。提交前应使用评估脚本和代表性视频或 MOT 序列验证行为。若新增测试，请放入 `tests/`，文件命名为 `test_*.py`，优先使用小型、确定性的 fixture，避免提交大型媒体文件。新增测试依赖需同步写入 `requirements.txt`。

## 提交与 Pull Request 规范

现有提交历史以简短中文说明为主，偶尔使用 Conventional Commit 前缀，例如 `fix:`。提交信息应简洁、动作明确，例如 `fix: 修正README说明` 或 `新增跟踪评估图表`。PR 应说明目的、关键改动、已运行命令、影响到的配置或模型路径；涉及 UI 的改动请附截图或短视频。若改动关联 OpenSpec，请在 PR 中链接对应变更。

## 安全与配置建议

将本机路径、模型位置和运行参数集中放在 `config.yaml` 中维护。不要提交密钥、本地数据集、导出视频、训练中间产物或模型权重文件（如 `*.pt`、`*.pth`）。训练新模型后，确认 `config.yaml` 中的 `model.path` 指向目标 checkpoint。
