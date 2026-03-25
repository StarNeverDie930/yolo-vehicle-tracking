from ultralytics import YOLO


def evaluate_detection(model_path="yolo11n.pt", data_yaml=None):
    """使用 ultralytics 内置验证计算 mAP"""
    model = YOLO(model_path)
    if data_yaml:
        results = model.val(data=data_yaml)
    else:
        results = model.val()

    print(f"mAP@0.5:     {results.box.map50:.4f}")
    print(f"mAP@0.5:0.95: {results.box.map:.4f}")
    return results


if __name__ == "__main__":
    import sys
    data = sys.argv[1] if len(sys.argv) > 1 else None
    evaluate_detection(data_yaml=data)
