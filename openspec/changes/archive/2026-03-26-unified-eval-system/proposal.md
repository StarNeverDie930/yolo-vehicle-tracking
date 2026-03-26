## 为什么

现有评估脚本分散（detect_eval.py、track_eval.py、eval_all.py），输出仅为纯文本，无图表、无时间戳、无可回溯记录，无法满足毕设中对模型能力的系统性展示需求。

## 变更内容

- **重写** `evaluation/eval_all.py`：统一入口，支持 `--mode detect|track|both`，每次运行生成带时间戳的结果目录
- **修改** `evaluation/track_eval.py`：增加 MT（mostly_tracked）指标
- **新增** 图表输出：PR 曲线、各类 mAP 柱状图、跟踪指标柱状图
- **归档** 已有测评文件（`evaluation/mot_data/MVI_20011/eval_result.txt` → `evaluation/results/archive/`）
- 不修改：`detect_eval.py`、`gen_mot_gt.py`、`gen_mot_pred.py`

## 功能 (Capabilities)

### 新增功能

- `eval-runner`: 统一评估入口，支持分模式运行（检测/跟踪/联合），每次运行输出带时间戳的结果目录，包含 summary.txt 和图表
- `eval-charts`: 基于评估结果生成可视化图表（PR 曲线、mAP 柱状图、跟踪指标柱状图）
- `eval-archive`: 归档历史测评文件，保证可回溯性

### 修改功能

（无现有规范文件，不适用）

## 影响

- `evaluation/eval_all.py`：完全重写
- `evaluation/track_eval.py`：增加一个指标
- 新增输出目录：`evaluation/results/<timestamp>_<seq>/`
- 归档目录：`evaluation/results/archive/`
