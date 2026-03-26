## 新增需求

### 需求:归档已有测评文件
系统必须在首次运行时将 `evaluation/mot_data/<seq>/eval_result.txt`（若存在）归档到 `evaluation/results/archive/<seq>/summary.txt`，且归档操作幂等（已存在则跳过）。

#### 场景:首次归档
- **当** `evaluation/mot_data/MVI_20011/eval_result.txt` 存在且 `evaluation/results/archive/MVI_20011/summary.txt` 不存在
- **那么** 系统将旧文件复制到归档路径

#### 场景:归档幂等
- **当** 归档文件已存在
- **那么** 系统跳过归档，不覆盖已有归档

### 需求:历史结果按时间戳目录可回溯
每次运行的结果目录必须永久保留，不被后续运行覆盖。

#### 场景:多次运行不覆盖
- **当** 用户对同一序列运行两次评估
- **那么** `evaluation/results/` 下存在两个不同时间戳的子目录，各自独立

## 修改需求

## 移除需求
