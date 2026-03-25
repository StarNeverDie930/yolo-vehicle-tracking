import motmetrics as mm
import numpy as np


def evaluate_tracking(gt_file, pred_file):
    """
    评估跟踪性能 (MOTA, MOTP, IDF1)
    gt_file / pred_file: MOTChallenge 格式的文本文件
    每行: frame, id, bb_left, bb_top, bb_width, bb_height, conf, -1, -1, -1
    """
    gt = mm.io.loadtxt(gt_file, fmt="mot15-2D")
    pred = mm.io.loadtxt(pred_file, fmt="mot15-2D")

    acc = mm.utils.compare_to_groundtruth(gt, pred, "iou", distth=0.5)
    mh = mm.metrics.create()
    summary = mh.compute(acc, metrics=["mota", "motp", "idf1", "num_switches"], name="eval")

    print(summary.to_string())
    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python track_eval.py <gt_file> <pred_file>")
    else:
        evaluate_tracking(sys.argv[1], sys.argv[2])
