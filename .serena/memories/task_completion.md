# 完成任务前检查

- 若修改代码，优先运行与改动相关的脚本或评估流程；当前仓库没有独立单元测试套件，也没有 `pytest.ini` / `pyproject.toml`。
- 对 GUI/视频处理改动，至少需要用代表性视频手动启动 `python main.py` 验证打开视频、开始处理、停止、热力图和导出视频。
- 对检测/跟踪算法或配置改动，建议运行 `python evaluation/eval_all.py --seq MVI_20011 --mode both --model <模型路径>`。
- 不提交本地数据集、导出视频、模型权重、中间训练产物或密钥；`.gitignore` 已忽略 `data/`、`runs/**/weights/`、`*.pt`、`*.pth`、`output/`、`docs/`。