"""评估论文中对比的两个模型，并保存表格与图表。

脚本刻意只比较以下两个权重：
  1. runs/merged_train_rtx6000_960/weights/best.pt
  2. runs/merged_train_rtx6000_1024_finetune15/weights/best.pt
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from evaluation.detect_eval import evaluate_detection as run_detection_eval
from evaluation.track_eval import evaluate_tracking as run_tracking_eval


DATA_YAML = BASE_DIR / "scripts" / "merged.yaml"
SEQ = "MVI_20011"
MOT_DIR = BASE_DIR / "evaluation" / "mot_data"
RESULTS_DIR = BASE_DIR / "evaluation" / "results"

MODELS = [
    {
        "label": "960",
        "display": "merged_train_rtx6000_960",
        "run_dir": BASE_DIR / "runs" / "merged_train_rtx6000_960",
        "weight": BASE_DIR / "runs" / "merged_train_rtx6000_960" / "weights" / "best.pt",
        "order": 1,
    },
    {
        "label": "1024_finetune15",
        "display": "merged_train_rtx6000_1024_finetune15",
        "run_dir": BASE_DIR / "runs" / "merged_train_rtx6000_1024_finetune15",
        "weight": BASE_DIR
        / "runs"
        / "merged_train_rtx6000_1024_finetune15"
        / "weights"
        / "best.pt",
        "order": 2,
    },
]


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _format_float(value: object, digits: int = 6) -> object:
    if isinstance(value, float):
        return round(value, digits)
    return value


def _copy_training_artifacts(model_info: dict, target_dir: Path) -> None:
    artifact_names = [
        "args.yaml",
        "results.csv",
        "results.png",
        "BoxF1_curve.png",
        "BoxPR_curve.png",
        "BoxP_curve.png",
        "BoxR_curve.png",
        "confusion_matrix.png",
        "confusion_matrix_normalized.png",
        "labels.jpg",
        "val_batch0_labels.jpg",
        "val_batch0_pred.jpg",
        "val_batch1_labels.jpg",
        "val_batch1_pred.jpg",
        "val_batch2_labels.jpg",
        "val_batch2_pred.jpg",
    ]
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in artifact_names:
        src = model_info["run_dir"] / name
        if src.exists():
            shutil.copy2(src, target_dir / name)


def evaluate_detection_model(model_info: dict, out_dir: Path, device: str | None) -> tuple[dict, list[dict]]:
    args_yaml = _read_yaml(model_info["run_dir"] / "args.yaml")
    imgsz = int(args_yaml.get("imgsz") or (1024 if "1024" in model_info["label"] else 960))

    start = time.perf_counter()
    val_kwargs = {
        "imgsz": imgsz,
        "project": str(out_dir),
        "name": f"{model_info['label']}_detect_val",
        "exist_ok": True,
        "plots": True,
        "verbose": True,
    }
    if device:
        val_kwargs["device"] = device
    results = run_detection_eval(str(model_info["weight"]), str(DATA_YAML), **val_kwargs)
    elapsed = time.perf_counter() - start

    class_indices = [int(i) for i in results.box.ap_class_index.tolist()]
    class_rows = []
    for offset, cls_idx in enumerate(class_indices):
        class_rows.append(
            {
                "model": model_info["display"],
                "class": results.names.get(cls_idx, str(cls_idx)),
                "precision": float(results.box.p[offset]),
                "recall": float(results.box.r[offset]),
                "ap50": float(results.box.ap50[offset]),
                "map50_95": float(results.box.ap[offset]),
            }
        )

    summary = {
        "model": model_info["display"],
        "model_order": model_info["order"],
        "weight": str(model_info["weight"]),
        "imgsz": imgsz,
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
        "map50": float(results.box.map50),
        "map50_95": float(results.box.map),
        "fitness": float(getattr(results, "fitness", 0.0)),
        "elapsed_sec": elapsed,
        "val_output_dir": str(Path(results.save_dir)),
    }
    return summary, class_rows


def evaluate_tracking_model(model_info: dict, out_dir: Path) -> dict:
    from evaluation.gen_mot_pred import generate

    seq_dir = MOT_DIR / SEQ
    gt_file = seq_dir / "gt.txt"
    pred_file = seq_dir / "pred.txt"
    if not gt_file.exists():
        from evaluation.gen_mot_gt import convert

        convert(SEQ)

    start = time.perf_counter()
    generate(SEQ, str(model_info["weight"]))
    pred_copy = out_dir / model_info["label"] / "pred.txt"
    pred_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pred_file, pred_copy)

    metrics = [
        "mota",
        "motp",
        "idf1",
        "idp",
        "idr",
        "precision",
        "recall",
        "num_frames",
        "num_objects",
        "num_predictions",
        "num_matches",
        "num_misses",
        "num_false_positives",
        "num_switches",
        "num_fragmentations",
        "mostly_tracked",
        "partially_tracked",
        "mostly_lost",
    ]
    summary = run_tracking_eval(str(gt_file), str(pred_file), metrics=metrics, name=model_info["label"])
    row = summary.iloc[0].to_dict()
    elapsed = time.perf_counter() - start

    row.update(
        {
            "model": model_info["display"],
            "model_order": model_info["order"],
            "sequence": SEQ,
            "gt_file": str(gt_file),
            "pred_file": str(pred_copy),
            "elapsed_sec": elapsed,
        }
    )
    return row


def collect_training_rows(model_infos: list[dict]) -> list[dict]:
    rows = []
    for info in model_infos:
        args_yaml = _read_yaml(info["run_dir"] / "args.yaml")
        row = {
            "model": info["display"],
            "model_order": info["order"],
            "imgsz": args_yaml.get("imgsz"),
            "epochs": args_yaml.get("epochs"),
            "batch": args_yaml.get("batch"),
            "optimizer": args_yaml.get("optimizer"),
            "lr0": args_yaml.get("lr0"),
            "lrf": args_yaml.get("lrf"),
            "momentum": args_yaml.get("momentum"),
            "weight_decay": args_yaml.get("weight_decay"),
            "freeze": args_yaml.get("freeze"),
            "mosaic": args_yaml.get("mosaic"),
            "fliplr": args_yaml.get("fliplr"),
            "source_model": args_yaml.get("model"),
            "data": args_yaml.get("data"),
        }
        rows.append(row)
    return rows


def plot_detection_summary(rows: list[dict], out_dir: Path) -> None:
    df = pd.DataFrame(rows).sort_values("model_order")
    metrics = ["precision", "recall", "map50", "map50_95"]
    ax = df.plot(x="model", y=metrics, kind="bar", figsize=(9, 5), rot=12)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("score")
    ax.set_title("Detection metrics on merged validation set")
    ax.grid(axis="y", alpha=0.25)
    for container in ax.containers:
        ax.bar_label(container, fmt="%.3f", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "detection_metrics_comparison.png", dpi=200)
    plt.close()


def plot_per_class(rows: list[dict], out_dir: Path) -> None:
    df = pd.DataFrame(rows)
    for metric, filename, title in [
        ("ap50", "per_class_ap50_comparison.png", "Per-class AP@0.5"),
        ("map50_95", "per_class_map50_95_comparison.png", "Per-class mAP@0.5:0.95"),
        ("precision", "per_class_precision_comparison.png", "Per-class precision"),
        ("recall", "per_class_recall_comparison.png", "Per-class recall"),
    ]:
        pivot = df.pivot(index="class", columns="model", values=metric)
        ax = pivot.plot(kind="bar", figsize=(9, 5), rot=0)
        ax.set_ylim(0, 1.0)
        ax.set_ylabel(metric)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
        for container in ax.containers:
            ax.bar_label(container, fmt="%.3f", fontsize=8)
        plt.tight_layout()
        plt.savefig(out_dir / filename, dpi=200)
        plt.close()


def plot_tracking(rows: list[dict], out_dir: Path) -> None:
    df = pd.DataFrame(rows).sort_values("model_order")
    ratio_metrics = ["mota", "idf1", "idp", "idr", "precision", "recall"]
    ax = df.plot(x="model", y=ratio_metrics, kind="bar", figsize=(11, 5), rot=12)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("score")
    ax.set_title(f"Tracking ratio metrics on {SEQ}")
    ax.grid(axis="y", alpha=0.25)
    for container in ax.containers:
        ax.bar_label(container, fmt="%.3f", fontsize=7)
    plt.tight_layout()
    plt.savefig(out_dir / "tracking_ratio_metrics_comparison.png", dpi=200)
    plt.close()

    count_metrics = [
        "num_misses",
        "num_false_positives",
        "num_switches",
        "num_fragmentations",
        "mostly_tracked",
        "mostly_lost",
    ]
    ax = df.plot(x="model", y=count_metrics, kind="bar", figsize=(11, 5), rot=12)
    ax.set_ylabel("count")
    ax.set_title(f"Tracking count metrics on {SEQ}")
    ax.grid(axis="y", alpha=0.25)
    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f", fontsize=7)
    plt.tight_layout()
    plt.savefig(out_dir / "tracking_count_metrics_comparison.png", dpi=200)
    plt.close()


def plot_training_curves(model_infos: list[dict], out_dir: Path) -> None:
    specs = [
        ("metrics/mAP50(B)", "training_map50_curve.png", "Validation mAP@0.5"),
        ("metrics/mAP50-95(B)", "training_map50_95_curve.png", "Validation mAP@0.5:0.95"),
        ("metrics/precision(B)", "training_precision_curve.png", "Validation precision"),
        ("metrics/recall(B)", "training_recall_curve.png", "Validation recall"),
        ("train/box_loss", "training_box_loss_curve.png", "Training box loss"),
        ("val/box_loss", "validation_box_loss_curve.png", "Validation box loss"),
    ]
    for column, filename, title in specs:
        plt.figure(figsize=(8, 4.5))
        any_plotted = False
        for info in model_infos:
            csv_path = info["run_dir"] / "results.csv"
            if not csv_path.exists():
                continue
            df = pd.read_csv(csv_path)
            df.columns = [c.strip() for c in df.columns]
            if column not in df.columns:
                continue
            x_col = "epoch" if "epoch" in df.columns else df.index
            x = df[x_col] if isinstance(x_col, str) else x_col
            plt.plot(x, df[column], marker="o", linewidth=1.6, label=info["display"])
            any_plotted = True
        if any_plotted:
            plt.title(title)
            plt.xlabel("epoch")
            plt.ylabel(column)
            plt.grid(alpha=0.25)
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_dir / filename, dpi=200)
        plt.close()


def write_markdown_report(
    out_dir: Path,
    training_rows: list[dict],
    detection_rows: list[dict],
    class_rows: list[dict],
    tracking_rows: list[dict],
) -> None:
    def table(rows: list[dict], columns: list[str]) -> str:
        lines = ["|" + "|".join(columns) + "|", "|" + "|".join(["---"] * len(columns)) + "|"]
        for row in rows:
            values = [_format_float(row.get(col, ""), 4) for col in columns]
            lines.append("|" + "|".join(str(v) for v in values) + "|")
        return "\n".join(lines)

    report = [
        "# Thesis model evaluation report",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Python: {sys.version.split()[0]}",
        f"- Platform: {platform.platform()}",
        f"- Detection data: {DATA_YAML}",
        f"- Tracking sequence: {SEQ}",
        "",
        "## Training configuration",
        table(training_rows, ["model", "imgsz", "epochs", "batch", "lr0", "lrf", "freeze", "data"]),
        "",
        "## Detection summary",
        table(detection_rows, ["model", "imgsz", "precision", "recall", "map50", "map50_95", "elapsed_sec"]),
        "",
        "## Detection per class",
        table(class_rows, ["model", "class", "precision", "recall", "ap50", "map50_95"]),
        "",
        "## Tracking summary",
        table(
            tracking_rows,
            [
                "model",
                "mota",
                "motp",
                "idf1",
                "idp",
                "idr",
                "precision",
                "recall",
                "num_misses",
                "num_false_positives",
                "num_switches",
                "mostly_tracked",
                "mostly_lost",
            ],
        ),
        "",
    ]
    (out_dir / "evaluation_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--device", default=None, help="Ultralytics device, e.g. 0, cpu")
    parser.add_argument("--output-name", default=None, help="Custom result directory name")
    args = parser.parse_args()

    os.environ.setdefault("YOLO_OFFLINE", "1")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = RESULTS_DIR / (args.output_name or f"thesis_two_models_{timestamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    for info in MODELS:
        if not info["weight"].exists():
            raise FileNotFoundError(info["weight"])
        _copy_training_artifacts(info, out_dir / "training_artifacts" / info["label"])

    training_rows = collect_training_rows(MODELS)
    detection_rows: list[dict] = []
    class_rows: list[dict] = []
    tracking_rows: list[dict] = []

    for info in MODELS:
        print(f"\n=== Detection: {info['display']} ===")
        detection_summary, per_class = evaluate_detection_model(info, out_dir, args.device)
        detection_rows.append(detection_summary)
        class_rows.extend(per_class)

        print(f"\n=== Tracking: {info['display']} ===")
        tracking_rows.append(evaluate_tracking_model(info, out_dir / "tracking_predictions"))

    detection_rows.sort(key=lambda r: r["model_order"])
    class_rows.sort(key=lambda r: (r["model"], r["class"]))
    tracking_rows.sort(key=lambda r: r["model_order"])

    _write_csv(
        out_dir / "training_config.csv",
        training_rows,
        [
            "model",
            "model_order",
            "imgsz",
            "epochs",
            "batch",
            "optimizer",
            "lr0",
            "lrf",
            "momentum",
            "weight_decay",
            "freeze",
            "mosaic",
            "fliplr",
            "source_model",
            "data",
        ],
    )
    _write_csv(
        out_dir / "detection_summary.csv",
        detection_rows,
        [
            "model",
            "model_order",
            "weight",
            "imgsz",
            "precision",
            "recall",
            "map50",
            "map50_95",
            "fitness",
            "elapsed_sec",
            "val_output_dir",
        ],
    )
    _write_csv(
        out_dir / "detection_per_class.csv",
        class_rows,
        ["model", "class", "precision", "recall", "ap50", "map50_95"],
    )
    _write_csv(
        out_dir / "tracking_summary.csv",
        tracking_rows,
        [
            "model",
            "model_order",
            "sequence",
            "mota",
            "motp",
            "idf1",
            "idp",
            "idr",
            "precision",
            "recall",
            "num_frames",
            "num_objects",
            "num_predictions",
            "num_matches",
            "num_misses",
            "num_false_positives",
            "num_switches",
            "num_fragmentations",
            "mostly_tracked",
            "partially_tracked",
            "mostly_lost",
            "elapsed_sec",
            "gt_file",
            "pred_file",
        ],
    )

    with (out_dir / "all_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "training": training_rows,
                "detection": detection_rows,
                "detection_per_class": class_rows,
                "tracking": tracking_rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    plot_detection_summary(detection_rows, out_dir)
    plot_per_class(class_rows, out_dir)
    plot_tracking(tracking_rows, out_dir)
    plot_training_curves(MODELS, out_dir)
    write_markdown_report(out_dir, training_rows, detection_rows, class_rows, tracking_rows)

    print(f"\nSaved thesis evaluation results to: {out_dir}")


if __name__ == "__main__":
    main()
