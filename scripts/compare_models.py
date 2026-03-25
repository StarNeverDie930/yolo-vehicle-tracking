"""
对比训练前后模型在验证集上的检测效果。

用法:
  python scripts/compare_models.py
  python scripts/compare_models.py --before yolo11m.pt --after runs/detrac_train/weights/best.pt
"""

import argparse
import os

os.environ["YOLO_OFFLINE"] = "1"

from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def evaluate(model_path, data_yaml, imgsz=640):
    print(f"\n{'=' * 50}")
    print(f"评估模型: {model_path}")
    print(f"{'=' * 50}")
    model = YOLO(model_path)
    results = model.val(data=data_yaml, imgsz=imgsz, verbose=True)
    return {
        "mAP50": results.box.map50,
        "mAP50-95": results.box.map,
        "precision": results.box.mp,
        "recall": results.box.mr,
    }


def main():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--before", default=os.path.join(BASE_DIR, "yolo11m.pt"), help="训练前模型")
    p.add_argument("--after", default=os.path.join(BASE_DIR, "runs/detrac_train/weights/best.pt"), help="训练后模型")
    p.add_argument("--data", default=os.path.join(BASE_DIR, "scripts/detrac.yaml"), help="数据集配置")
    args = p.parse_args()

    before = evaluate(args.before, args.data)
    after = evaluate(args.after, args.data)

    print(f"\n{'=' * 50}")
    print("对比结果")
    print(f"{'=' * 50}")
    print(f"{'指标':<15} {'训练前':>10} {'训练后':>10} {'变化':>10}")
    print("-" * 50)
    for key in before:
        b, a = before[key], after[key]
        diff = a - b
        sign = "+" if diff > 0 else ""
        print(f"{key:<15} {b:>10.4f} {a:>10.4f} {sign + f'{diff:.4f}':>10}")


if __name__ == "__main__":
    main()