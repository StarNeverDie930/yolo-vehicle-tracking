"""使用当前处理流水线生成 MOTChallenge 预测文件。"""

import os
import sys
import pathlib
import argparse
import cv2
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

IMG_DIR = "data/UA-DETRAC/Insight-MVT_Annotation_Train"
OUT_DIR = "evaluation/mot_data"
CONFIG_PATH = "config.yaml"


def generate(seq, model_path=None):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if model_path:
        config["model"]["path"] = model_path

    from core.pipeline import ProcessingPipeline
    pipeline = ProcessingPipeline(config)
    pipeline.reset()

    img_folder = os.path.join(IMG_DIR, seq)
    img_files = sorted(f for f in os.listdir(img_folder) if f.endswith(".jpg"))

    out_path = os.path.join(OUT_DIR, seq)
    os.makedirs(out_path, exist_ok=True)

    lines = []
    for fnum, fname in enumerate(img_files, start=1):
        frame = cv2.imread(os.path.join(img_folder, fname))
        if frame is None:
            continue
        _, tracks, _, _, _ = pipeline.process_frame(
            frame,
            frame_idx=fnum - 1,
            fps=config.get("video", {}).get("fallback_fps", 30),
        )
        for t in tracks:
            x1, y1, x2, y2 = t["bbox"]
            w, h = x2 - x1, y2 - y1
            lines.append(f"{fnum},{t['track_id']},{x1},{y1},{w},{h},1,-1,-1,-1")

    with open(os.path.join(out_path, "pred.txt"), "w") as f:
        f.write("\n".join(lines))
    print(f"Pred saved: {out_path}/pred.txt ({len(lines)} rows)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seq", required=True, help="序列名称，如 MVI_20011")
    parser.add_argument("--model", default=None, help="模型路径（默认使用 config.yaml）")
    args = parser.parse_args()
    generate(args.seq, args.model)
