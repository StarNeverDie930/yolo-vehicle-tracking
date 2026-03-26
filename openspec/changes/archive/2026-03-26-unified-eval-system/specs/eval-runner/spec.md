## 新增需求

### 需求:支持分模式评估
系统必须通过 `--mode` 参数支持三种运行模式：`detect`（仅检测）、`track`（仅跟踪）、`both`（联合，默认）。

#### 场景:仅检测模式
- **当** 用户运行 `python evaluation/eval_all.py --seq MVI_20011 --mode detect`
- **那么** 系统仅执行检测评估，输出 mAP50 和 mAP50-95，不运行跟踪推理

#### 场景:仅跟踪模式
- **当** 用户运行 `python evaluation/eval_all.py --seq MVI_20011 --mode track`
- **那么** 系统仅执行跟踪评估，输出 MOTA/MOTP/MT/IDF1/ID Switch，不运行 ultralytics val

#### 场景:联合模式（默认）
- **当** 用户运行 `python evaluation/eval_all.py --seq MVI_20011`（不指定 --mode）
- **那么** 系统依次执行检测评估和跟踪评估，输出所有指标

### 需求:每次运行生成独立结果目录
系统必须为每次运行在 `evaluation/results/` 下创建格式为 `<YYYYMMDD_HHMMSS>_<seq>/` 的独立目录。

#### 场景:目录自动创建
- **当** 评估开始时
- **那么** 系统自动创建 `evaluation/results/<timestamp>_<seq>/` 目录，其中包含 summary.txt

### 需求:summary.txt 包含完整元信息
summary.txt 必须包含：时间戳、模型路径、序列名、运行模式，以及所有已执行的评估指标。

#### 场景:summary.txt 内容完整
- **当** 评估完成后
- **那么** summary.txt 第一部分为元信息（timestamp/model/sequence/mode），后续各节列出对应指标数值

## 修改需求

## 移除需求
