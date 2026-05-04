# 基于YOLO的车辆轨迹与目标检测系统

基于 YOLOv11 + Deep SORT 的车辆检测、跟踪与交通流量分析系统，提供 PySide6 图形界面。

## 功能

- 实时车辆检测（YOLOv11）
- 多目标跟踪与轨迹可视化（Deep SORT）
- 车辆计数：默认基于 `unique_track` 去重，也支持 `line_crossing` 越线统计
- 分车型统计：car / bus / van / truck 累计数量
- 按视频时间窗口统计交通流量
- 热力图查看与保存，支持原始热力图和 overlay 叠加图输出
- 分析结果导出：车型结构、分时段流量、轨迹摘要、热点区域和处理性能摘要
- 视频导出

## 环境要求

- Python 3.10+
- CUDA（推荐，CPU 也可运行）

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
python main.py
```

1. 点击「打开视频」选择视频文件
2. 点击「开始处理」开始检测与跟踪
3. 右侧面板实时显示车辆总数、分车型统计和流量窗口统计
4. 处理完成后可「查看热力图」「保存热力图」、导出标注视频和查看分析结果目录
5. 若处理完成但尚未导出视频，打开新视频前系统会弹窗确认是否继续

## 训练自定义模型

**1. 转换 KITTI 数据集**
```bash
python kitti_to_yolo.py
```

**2. 合并 UA-DETRAC + KITTI 数据集**
```bash
python scripts/merge_datasets.py
```

**3. 训练**
```bash
python scripts/train.py \
  --model runs/detrac_train/weights/best.pt \
  --data scripts/merged.yaml \
  --epochs 80 \
  --lr0 0.0005 \
  --cos-lr \
  --name merged_train_v2
```

训练完成后修改 `config.yaml` 中的 `model.path` 指向新模型。

## 项目结构

```
├── main.py                 # 程序入口
├── config.yaml             # 运行配置
├── docs/                   # 毕业设计任务书、开题报告等 markdown 基线材料
├── openspec/               # 项目规范和已归档变更，建议纳入版本控制
├── core/
│   ├── detector.py         # YOLOv11 检测
│   ├── tracker.py          # Deep SORT 跟踪
│   └── pipeline.py         # 处理流水线
├── analysis/
│   ├── counter.py          # 车辆计数与流量统计
│   ├── trajectory.py       # 轨迹存储
│   ├── heatmap.py          # 热力图生成与保存
│   └── results.py          # 分析结果导出
├── app/                    # PySide6 界面
├── scripts/
│   ├── train.py            # 训练脚本
│   ├── merge_datasets.py   # 数据集合并
│   └── merged.yaml         # 合并数据集配置
├── evaluation/             # 检测与跟踪评估
├── utils/                  # 视频读写、绘图工具
├── data/                   # 本地数据集与测试视频，默认不提交
├── runs/                   # 训练输出，默认不提交
├── weights/                # 模型权重，默认不提交
└── output/                 # 导出视频，默认不提交
```

## 数据集

| 数据集 | 用途 |
|--------|------|
| UA-DETRAC | 交通监控场景，82,085 张 |
| KITTI | 车载视角，补充静止车辆场景，6,920 张 |

统一类别：`car(0)` / `bus(1)` / `van(2)` / `truck(3)`

## 版本管理建议

建议纳入版本控制的内容：

- 源码目录：`app/`、`core/`、`analysis/`、`evaluation/`、`scripts/`、`utils/`
- 项目入口与配置：`main.py`、`config.yaml`、`requirements.txt`、`README.md`
- 毕业设计基线材料：`docs/*.md`，其中任务书和开题报告是项目基本依据，不随实现过程随意修改正文
- OpenSpec 项目规范：`openspec/config.yaml`、`openspec/specs/`、`openspec/changes/archive/`

不建议纳入版本控制的内容：

- 本地 AI/IDE/索引工具目录：`.agents/`、`.claude/`、`.serena/`、`.vscode/`、`.idea/`
- 本地 OpenSpec/Codex 技能缓存：`.agents/skills/`、`.claude/skills/`
- 数据集、权重和训练产物：`data/`、`weights/`、`runs/`、`*.pt`、`*.pth`、`*.onnx`
- 运行输出和导出文件：`output/`、`analysis/results/`、`evaluation/results/`、常见视频文件
- 二进制文档源文件：`docs/*.doc`、`docs/*.docx`、`docs/*.pptx`

说明：`openspec/` 目录保存的是项目需求、设计和归档变更，建议保留；需要忽略的是 `.agents/`、`.claude/` 中的本地技能文件，它们属于个人工具环境，不属于毕业设计交付内容。

## 更新日志

### 2026-05-04
- **修复** GUI 后台线程生命周期，避免处理完成后出现 `QThread` 提前销毁问题
- **新增** 处理完成后的未导出视频提醒、关闭保护和导出 busy 状态
- **调整** 热力图功能为「查看热力图」和「保存热力图」两个独立操作
- **更新** 版本管理规则，忽略本地 AI/IDE 缓存、大文件和运行输出

### 2026-03-26
- **新增** 多目标跟踪评测系统，支持检测和跟踪的统一评估
- **重写** `evaluation/eval_all.py`：统一评估入口，支持 `--mode detect|track|both` 模式
- **新增** 图表输出功能：PR 曲线、各类 mAP 柱状图、跟踪指标柱状图
- **修改** `evaluation/track_eval.py`：增加 MT（mostly_tracked）指标
- **归档** 历史测评文件，保证可回溯性
- **新增** openspec 作为项目的规范驱动工具，包含完整的变更设计文档
- **更新** 项目规范文档；本地技能目录不纳入版本控制

### 2026-03-25
- **新增** 检测结果的图表和数据文件

### 2026-03-24
- **修复** README.md 文档内容

### 2026-03-23
- **初始化** 项目仓库
