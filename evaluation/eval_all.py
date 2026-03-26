import argparse
import os
import sys
import shutil
import pathlib
from datetime import datetime
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

CONFIG_PATH = "config.yaml"
DATA_YAML = "scripts/detrac.yaml"
MOT_DIR = "evaluation/mot_data"
RESULTS_DIR = "evaluation/results"


def _archive_existing(seq):
    old = os.path.join(MOT_DIR, seq, "eval_result.txt")
    archive = os.path.join(RESULTS_DIR, "archive", seq, "summary.txt")
    if os.path.exists(old) and not os.path.exists(archive):
        os.makedirs(os.path.dirname(archive), exist_ok=True)
        shutil.copy2(old, archive)
        print(f"已归档旧结果: {archive}")


def _run_detection(model_path):
    from evaluation.detect_eval import evaluate_detection
    print("=== Detection ===")
    r = evaluate_detection(model_path, DATA_YAML)
    return {
        "map50": r.box.map50,
        "map": r.box.map,
        "precision": float(r.box.mp),
        "recall": float(r.box.mr),
        "ap50_per_class": r.box.ap50.tolist(),
        "class_names": [r.names[i] for i in r.box.ap_class_index],
        "_raw": r,
    }


def _run_tracking(seq, model_path):
    gt_file = os.path.join(MOT_DIR, seq, "gt.txt")
    pred_file = os.path.join(MOT_DIR, seq, "pred.txt")
    if not os.path.exists(gt_file):
        from evaluation.gen_mot_gt import convert
        convert(seq)
    from evaluation.gen_mot_pred import generate
    generate(seq, model_path)
    print(f"\n=== Tracking ({seq}) ===")
    from evaluation.track_eval import evaluate_tracking
    summary = evaluate_tracking(gt_file, pred_file)
    row = summary.iloc[0]
    return {
        "mota": float(row["mota"]),
        "motp": float(row["motp"]),
        "idf1": float(row["idf1"]),
        "num_switches": int(row["num_switches"]),
        "mostly_tracked": int(row["mostly_tracked"]),
    }


def _save_summary(out_dir, meta, det, trk):
    lines = [
        f"timestamp:  {meta['timestamp']}",
        f"model:      {meta['model']}",
        f"sequence:   {meta['seq']}",
        f"mode:       {meta['mode']}",
        "",
    ]
    if det:
        lines += [
            "=== Detection ===",
            f"mAP@0.5:      {det['map50']:.4f}",
            f"mAP@0.5:0.95: {det['map']:.4f}",
            f"Precision:    {det['precision']:.4f}",
            f"Recall:       {det['recall']:.4f}",
            "",
        ]
    if trk:
        lines += [
            f"=== Tracking ({meta['seq']}) ===",
            f"MOTA:         {trk['mota']:.4f}",
            f"MOTP(dist):   {trk['motp']:.4f}  (越低越好，= 1 - IoU)",
            f"IDF1:         {trk['idf1']:.4f}",
            f"MT:           {trk['mostly_tracked']}",
            f"ID Switches:  {trk['num_switches']}",
        ]
    with open(os.path.join(out_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _plot_detection(out_dir, det):
    try:
        import matplotlib.pyplot as plt
        names = det["class_names"]
        ap50 = det["ap50_per_class"]
        _, ax = plt.subplots(figsize=(max(6, len(names) * 1.2), 4))
        bars = ax.bar(names, ap50, color="#4C72B0")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("mAP@0.5")
        ax.set_title(f"Per-class mAP@0.5  (mean={det['map50']:.4f})")
        for bar, v in zip(bars, ap50):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "map_bar.png"), dpi=150)
        plt.close()
    except Exception as e:
        print(f"[警告] 检测图表生成失败: {e}")


def _plot_tracking(out_dir, trk):
    try:
        import matplotlib.pyplot as plt
        _, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        ratio_metrics = {"MOTA": trk["mota"], "IDF1": trk["idf1"]}
        ax1.bar(ratio_metrics.keys(), ratio_metrics.values(), color=["#4C72B0", "#55A868"])
        ax1.set_ylim(0, 1.05)
        ax1.set_title("Tracking Ratio Metrics")
        for i, (_, v) in enumerate(ratio_metrics.items()):
            ax1.text(i, v + 0.01, f"{v:.4f}", ha="center", fontsize=9)
        count_metrics = {"MT": trk["mostly_tracked"], "ID Switch": trk["num_switches"]}
        ax2.bar(count_metrics.keys(), count_metrics.values(), color=["#C44E52", "#8172B2"])
        ax2.set_title("Tracking Count Metrics")
        for i, (_, v) in enumerate(count_metrics.items()):
            ax2.text(i, v + 0.05, str(v), ha="center", fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "tracking_bar.png"), dpi=150)
        plt.close()
    except Exception as e:
        print(f"[警告] 跟踪图表生成失败: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seq", required=True, help="序列名称，如 MVI_20011")
    parser.add_argument("--model", default=None)
    parser.add_argument("--mode", default="both", choices=["detect", "track", "both"])
    args = parser.parse_args()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    model_path = args.model or config["model"]["path"]

    _archive_existing(args.seq)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(RESULTS_DIR, f"{ts}_{args.seq}")
    os.makedirs(out_dir, exist_ok=True)

    meta = {"timestamp": ts, "model": model_path, "seq": args.seq, "mode": args.mode}
    det = _run_detection(model_path) if args.mode in ("detect", "both") else None
    trk = _run_tracking(args.seq, model_path) if args.mode in ("track", "both") else None

    _save_summary(out_dir, meta, det, trk)
    if det:
        _plot_detection(out_dir, det)
    if trk:
        _plot_tracking(out_dir, trk)

    print(f"\n结果已保存: {out_dir}/")


if __name__ == "__main__":
    main()
