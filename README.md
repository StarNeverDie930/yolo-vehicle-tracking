# 基于YOLO的车辆轨迹与目标检测系统

基于 YOLOv11 + Deep SORT 的车辆检测、跟踪与交通流量分析系统，提供 PySide6 图形界面。

## 功能

- 实时车辆检测（YOLOv11）
- 多目标跟踪与轨迹可视化（Deep SORT）
- 车辆计数：默认基于 `unique_track` 去重，也支持 `line_crossing` 越线统计
- 分车型统计：car / bus / van / truck 累计数量
- 按视频时间窗口统计交通流量
- 热力图生成与保存
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
4. 处理完成后可「保存热力图」、导出视频和查看分析结果目录

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
└── utils/                  # 视频读写、绘图工具
```

## 数据集

| 数据集 | 用途 |
|--------|------|
| UA-DETRAC | 交通监控场景，82,085 张 |
| KITTI | 车载视角，补充静止车辆场景，6,920 张 |

统一类别：`car(0)` / `bus(1)` / `van(2)` / `truck(3)`

## 更新日志

### 2026-03-26
- **新增** 多目标跟踪评测系统，支持检测和跟踪的统一评估
- **重写** `evaluation/eval_all.py`：统一评估入口，支持 `--mode detect|track|both` 模式
- **新增** 图表输出功能：PR 曲线、各类 mAP 柱状图、跟踪指标柱状图
- **修改** `evaluation/track_eval.py`：增加 MT（mostly_tracked）指标
- **归档** 历史测评文件，保证可回溯性
- **新增** openspec 作为项目的规范驱动工具，包含完整的变更设计文档
- **更新** 项目设置文件和技能文档

### 2026-03-25
- **新增** 检测结果的图表和数据文件

### 2026-03-24
- **修复** README.md 文档内容

### 2026-03-23
- **初始化** 项目仓库
