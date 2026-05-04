"""Structured analysis result recording and export helpers."""

import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path

from utils.taxonomy import CLASS_IDS, class_percentages, get_class_name


class AnalysisRecorder:
    def __init__(self):
        self.tracks = {}

    def update(self, tracks, frame_idx, timestamp):
        for track in tracks:
            if not track.get("matched", True):
                continue
            class_id = int(track.get("class_id", -1))
            if class_id not in CLASS_IDS:
                continue

            track_id = track["track_id"]
            x1, y1, x2, y2 = track["bbox"]
            center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
            record = self.tracks.setdefault(track_id, {
                "track_id": track_id,
                "class_id": class_id,
                "first_frame": frame_idx,
                "last_frame": frame_idx,
                "first_timestamp": timestamp,
                "last_timestamp": timestamp,
                "points": 0,
                "pixel_path_length": 0.0,
                "_last_center": None,
            })

            record["class_id"] = class_id
            record["last_frame"] = frame_idx
            record["last_timestamp"] = timestamp
            record["points"] += 1
            previous = record["_last_center"]
            if previous is not None:
                record["pixel_path_length"] += math.dist(previous, center)
            record["_last_center"] = center

    def summaries(self):
        rows = []
        for record in sorted(self.tracks.values(), key=lambda item: item["track_id"]):
            duration = max(0.0, record["last_timestamp"] - record["first_timestamp"])
            rows.append({
                "track_id": record["track_id"],
                "class_id": record["class_id"],
                "class_name": get_class_name(record["class_id"]),
                "first_frame": record["first_frame"],
                "last_frame": record["last_frame"],
                "duration_sec": round(duration, 3),
                "point_count": record["points"],
                "pixel_path_length": round(record["pixel_path_length"], 2),
            })
        return rows

    def clear(self):
        self.tracks.clear()


def make_result_dir(base_dir, source_path=None, prefix="analysis"):
    stem = Path(source_path).stem if source_path else prefix
    safe_stem = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(base_dir, f"{timestamp}_{safe_stem}")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def export_analysis_results(output_dir, class_counts, flow_buckets, track_summaries,
                            hotspots, performance, heatmap_paths=None):
    os.makedirs(output_dir, exist_ok=True)
    heatmap_paths = heatmap_paths or {}
    _write_class_counts(output_dir, class_counts)
    _write_flow_buckets(output_dir, flow_buckets)
    _write_track_summary(output_dir, track_summaries)
    _write_hotspots(output_dir, hotspots)
    _write_json(os.path.join(output_dir, "performance.json"), performance)
    _write_summary(output_dir, class_counts, flow_buckets, track_summaries,
                   hotspots, performance, heatmap_paths)
    return output_dir


def _write_class_counts(output_dir, counts):
    percentages = class_percentages(counts)
    rows = []
    for class_id in CLASS_IDS:
        rows.append({
            "class_id": class_id,
            "class_name": get_class_name(class_id),
            "count": counts.get(class_id, 0),
            "percentage": round(percentages[class_id] * 100, 2),
        })
    _write_csv(os.path.join(output_dir, "class_counts.csv"), rows,
               ["class_id", "class_name", "count", "percentage"])
    _write_json(os.path.join(output_dir, "class_counts.json"), rows)


def _write_flow_buckets(output_dir, buckets):
    fieldnames = ["start_sec", "end_sec", "total"] + [get_class_name(cid) for cid in CLASS_IDS]
    rows = []
    for bucket in buckets:
        row = {
            "start_sec": bucket["start_sec"],
            "end_sec": bucket["end_sec"],
            "total": bucket["total"],
        }
        for class_id in CLASS_IDS:
            row[get_class_name(class_id)] = bucket.get(class_id, 0)
        rows.append(row)
    _write_csv(os.path.join(output_dir, "flow_by_time.csv"), rows, fieldnames)


def _write_track_summary(output_dir, rows):
    fieldnames = [
        "track_id", "class_id", "class_name", "first_frame", "last_frame",
        "duration_sec", "point_count", "pixel_path_length",
    ]
    _write_csv(os.path.join(output_dir, "track_summary.csv"), rows, fieldnames)


def _write_hotspots(output_dir, rows):
    fieldnames = ["rank", "grid_row", "grid_col", "x1", "y1", "x2", "y2", "intensity"]
    _write_csv(os.path.join(output_dir, "hotspots.csv"), rows, fieldnames)


def _write_summary(output_dir, class_counts, flow_buckets, track_summaries,
                   hotspots, performance, heatmap_paths):
    percentages = class_percentages(class_counts)
    lines = [
        "车辆检测与交通分析结果摘要",
        "",
        f"视频路径: {performance.get('video_path', '')}",
        f"模型路径: {performance.get('model_path', '')}",
        f"设备: {performance.get('device', '')}",
        f"计数模式: {performance.get('counter_mode', '')}",
        f"处理帧数: {performance.get('frame_count', 0)}",
        f"处理耗时: {performance.get('elapsed_sec', 0):.3f}s",
        f"平均FPS: {performance.get('average_fps', 0):.3f}",
        "",
        "车型结构:",
    ]
    for class_id in CLASS_IDS:
        lines.append(
            f"- {get_class_name(class_id)}: {class_counts.get(class_id, 0)} "
            f"({percentages[class_id] * 100:.2f}%)"
        )

    lines += ["", "分时段流量:"]
    for bucket in flow_buckets[:10]:
        lines.append(f"- {bucket['start_sec']}s-{bucket['end_sec']}s: {bucket['total']} 辆")
    if len(flow_buckets) > 10:
        lines.append(f"- 其余 {len(flow_buckets) - 10} 个时间段见 flow_by_time.csv")

    lines += ["", "热点区域Top:"]
    for hotspot in hotspots:
        lines.append(
            f"- #{hotspot['rank']} row={hotspot['grid_row']} col={hotspot['grid_col']} "
            f"intensity={hotspot['intensity']:.2f}"
        )

    lines += [
        "",
        f"轨迹摘要记录数: {len(track_summaries)}",
        f"原始热力图: {heatmap_paths.get('heatmap', '')}",
        f"叠加热力图: {heatmap_paths.get('overlay', '')}",
    ]

    with open(os.path.join(output_dir, "summary.txt"), "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def _write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
