## 上下文

项目已有三个评估脚本（detect_eval.py、track_eval.py、eval_all.py）和辅助脚本（gen_mot_gt.py、gen_mot_pred.py）。当前 eval_all.py 每次运行会覆盖同一个 eval_result.txt，无图表，无法追溯历史。需要在不破坏现有辅助脚本的前提下，重写 eval_all.py 并增加图表和归档能力。

## 目标 / 非目标

**目标：**
- 每次运行生成独立的带时间戳目录（`evaluation/results/<timestamp>_<seq>/`）
- 支持 `--mode detect|track|both` 分模式运行
- 输出 summary.txt（含模型路径、时间戳、所有指标）+ 图表（PNG）
- 归档已有的 `evaluation/mot_data/MVI_20011/eval_result.txt`
- track_eval.py 增加 MT 指标（1行改动）

**非目标：**
- 不修改 detect_eval.py、gen_mot_gt.py、gen_mot_pred.py
- 不引入新的依赖（仅用 matplotlib，项目已有）
- 不实现 Web UI 或数据库存储

## 决策

**决策1：结果目录结构仿照 runs/detect/val/**
理由：用户明确要求"和 runs 目录下的文件一样"，保持一致的目录风格便于对比。
替代方案：单一 CSV 汇总文件 → 不直观，无法展示图表。

**决策2：时间戳格式 `YYYYMMDD_HHMMSS`**
理由：文件系统友好，按字母排序即按时间排序，无需解析。

**决策3：图表用 matplotlib 生成，不依赖 ultralytics 内置图表**
理由：ultralytics val 已生成自己的图表到 runs/，这里只需提取数值重新绘制汇总图，避免重复。
替代方案：直接复制 ultralytics 生成的图表 → 路径不稳定，难以定制。

**决策4：归档逻辑只执行一次（幂等）**
理由：避免重复归档覆盖。用 `if not os.path.exists(archive_path)` 保证幂等。

## 风险 / 权衡

- [matplotlib 未安装] → 图表生成失败但 summary.txt 仍正常写入，用 try/except 隔离
- [gen_mot_pred 耗时长] → track 模式需逐帧推理，长序列可能需要数分钟，属预期行为
- [detect 模式下 results.box.p/r 形状依赖 ultralytics 版本] → 用 `.mean()` 聚合，兼容不同形状
