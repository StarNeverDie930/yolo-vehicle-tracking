# 建议命令

- 安装依赖：`pip install -r requirements.txt`
- 启动 GUI：`python main.py`
- 转换 KITTI 标注：`python kitti_to_yolo.py`
- 转换 UA-DETRAC：`python scripts/convert_detrac_to_yolo.py`
- 合并 UA-DETRAC 与 KITTI：`python scripts/merge_datasets.py`
- 训练模型：`python scripts/train.py --model runs/detrac_train/weights/best.pt --data scripts/merged.yaml --epochs 80 --name merged_train_v2`
- 统一评估：`python evaluation/eval_all.py --seq MVI_20011 --mode both --model weights/best.pt`
- Windows 文件检索优先用 Serena 或 `rg`；本项目用户规则要求文件与代码检索优先 Serena，文件创建/读取/编辑/删除优先 apply_patch 或 desktop-commander，禁止用 cmd、PowerShell 或 Python 做文件相关操作。