## 上下文

当前 GUI 使用 `ProcessingWorker(QThread)` 执行视频处理和视频导出。worker 在 `run()` 中处理视频、导出分析结果，然后发出自定义 `finished(int, object)` 信号。主窗口的完成回调会调用 `_restore_idle_controls()`，该方法除了恢复按钮状态，还会将 `self.worker = None`。由于 worker 发出业务完成信号后还会执行 `finally` 释放视频资源，Qt 底层线程此时可能尚未完全结束，从而触发 `QThread: Destroyed while thread is still running`。

另一个问题是 GUI 只有零散按钮启停逻辑，没有明确的处理状态。普通处理完成、导出中、用户取消、错误退出、已处理但视频未导出等状态都混在 `self.worker`、`last_frame` 和 `last_result_dir` 上，导致打开新视频和导出视频时无法做可靠判断。

## 设计原则

- **线程生命周期和业务状态分离**：业务完成不等于 QThread 已结束，worker 引用必须由真实线程结束信号清理。
- **状态机驱动控件**：按钮启停由当前状态统一计算，不在多个回调里分散设置。
- **用户操作可恢复**：处理完成、取消、错误、导出完成后都必须回到可理解的界面状态。
- **不修改基线文档**：任务书和开题报告只作为验收参照，不纳入实现改动。

## GUI 状态模型

建议引入内部状态字段，至少区分以下状态：

- `idle_no_video`：未打开视频，只允许打开视频。
- `idle_video_loaded`：已打开视频但未处理，允许开始处理或打开另一个视频。
- `processing`：正在处理视频，允许停止，禁止打开、开始、导出和热力图操作。
- `stopping`：用户已请求停止，停止按钮置灰，等待后台线程退出。
- `processed_unsaved`：处理完成，分析结果和热力图数据可用，但处理后视频未导出。
- `processed_saved`：处理完成且用户已导出处理后视频。
- `exporting`：正在导出视频，禁止重复导出、打开新视频和热力图操作，可选择停止导出。
- `error`：处理或导出失败后恢复到可操作状态，并显示错误信息。

状态字段可以用字符串、枚举或小型辅助方法表达，但实现必须保证所有按钮状态来自同一套规则。

## Worker 信号设计

建议将业务信号从 `finished` 改名，避免覆盖或混淆 `QThread.finished`：

- `processing_completed(total_count, result_dir)`：正常处理或导出完成。
- `processing_cancelled(result_dir)`：用户主动停止后退出。
- `processing_failed(message)`：处理或导出异常。
- 保留 `QThread.finished`：仅用于 `deleteLater`、清理 `self.worker`、恢复最终线程状态。

主窗口不得在业务完成回调中销毁 worker。worker 清理应发生在 QThread 的真实 `finished` 信号之后，或在确认 `isRunning() == False` 后进行。

## 处理完成与未保存语义

本系统当前“处理完成”会自动保存分析结果包，但不会自动保存带标注的视频文件。因此“未保存视频”指的是 **处理完成后的视频导出文件未由用户保存**，不是分析结果未保存。

建议使用字段记录：

- `processing_completed: bool`
- `processed_video_saved: bool`
- `processed_output_path: str | None`
- `last_result_dir: str | None`

普通处理完成后：

- `processing_completed = True`
- `processed_video_saved = False`
- 可用：导出视频、打开视频、查看热力图、保存热力图
- 停止按钮置灰
- 弹窗提示处理完成，并显示分析结果目录

导出视频完成后：

- `processed_video_saved = True`
- `processed_output_path = 用户选择的输出路径`
- 弹窗提示导出完成

打开新视频前：

- 如果 `processing_completed == True` 且 `processed_video_saved == False`，弹窗提示：
  `您还有一个处理完成的视频未保存，是否要继续？`
- 用户选择“否”时不打开文件选择窗口。
- 用户选择“是”后再打开文件选择窗口，并清理旧处理状态。

## 停止和关闭

用户点击停止时，系统应进入 `stopping` 状态，禁用停止按钮，通知 worker 尽快退出。worker 退出后必须发出取消信号或失败信号，而不是误发正常完成信号。

关闭窗口时，如果 worker 仍在运行，系统必须弹窗确认。用户取消关闭时保持程序运行；用户确认关闭时请求 worker 停止，并等待线程安全退出。如果等待超时，应避免直接销毁仍运行的 QThread，并给出明确提示。

## 热力图交互

当前“保存热力图”会同时显示 overlay 并保存文件。为满足“查看热力图和保存热力图”两个动作，建议在工具栏中拆分为：

- `查看热力图`：只在界面显示叠加热力图，不写文件。
- `保存热力图`：保存原始热力图和 overlay 热力图到当前结果目录。

只有在处理完成且存在 `last_frame` / 热力图累积数据时，这两个动作才可用。

## 验证策略

验证应覆盖以下路径：

- 正常处理一个可读视频，进度到 100%，弹窗完成，终端不出现 QThread 错误。
- 处理完成后停止按钮置灰，导出、打开新视频、查看热力图、保存热力图可用。
- 处理完成但未导出视频时点击打开新视频，出现未保存确认弹窗。
- 导出视频期间无法重复点击导出、打开新视频或切换处理状态。
- 点击停止后显示取消语义，不误报处理完成。
- 处理或导出期间关闭窗口，会提示并安全退出。
