## 1. 归档已有测评文件

- [x] 1.1 将 `evaluation/mot_data/MVI_20011/eval_result.txt` 复制到 `evaluation/results/archive/MVI_20011/summary.txt`

## 2. 修改 track_eval.py

- [x] 2.1 在 `evaluate_tracking()` 的 metrics 列表中增加 `"mostly_tracked"`

## 3. 重写 eval_all.py

- [x] 3.1 增加 `--mode detect|track|both` 参数（默认 both）
- [x] 3.2 实现 `_archive_existing(seq)` — 归档旧 eval_result.txt（幂等）
- [x] 3.3 实现 `_run_detection(model_path)` — 调用 evaluate_detection()，返回指标 dict
- [x] 3.4 实现 `_run_tracking(seq, model_path)` — 确保 gt/pred 存在，调用 evaluate_tracking()，返回指标 dict
- [x] 3.5 实现 `_save_summary(out_dir, meta, det, trk)` — 写 summary.txt（含时间戳、模型路径、所有指标）
- [x] 3.6 实现 `_plot_detection(out_dir, results)` — 生成 map_bar.png，异常时仅打印警告
- [x] 3.7 实现 `_plot_tracking(out_dir, trk)` — 生成 tracking_bar.png，异常时仅打印警告
- [x] 3.8 实现 `main()` — 解析参数，创建时间戳目录，按 mode 调度各函数，打印结果路径
