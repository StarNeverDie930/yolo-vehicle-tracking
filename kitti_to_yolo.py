"""
KITTI -> YOLO format converter (unified class mapping for merging with UA-DETRAC)

Unified class mapping (matches UA-DETRAC: car/bus/van/truck):
  Car(0)     -> 0 (car)
  Cyclist(1) -> skip
  Truck(2)   -> 3 (truck)
  Van(3)     -> 2 (van)

Output: data/KITTI_YOLO_merged/{images,labels}/{train,val}/ + dataset.yaml
"""
import shutil
import random
from pathlib import Path
from PIL import Image

# Config
SRC_IMGS = Path("data/KITTI/data_object_image_2/training/image_2")
SRC_LBLS = Path("data/KITTI/training/label_2")
DST = Path("data/KITTI_YOLO_merged")
VAL_RATIO = 0.1
SEED = 42

# Unified classes matching UA-DETRAC: ["car", "bus", "van", "truck"]
# KITTI class -> unified class_id (None = skip)
KITTI_MAP = {"Car": 0, "Cyclist": None, "Truck": 3, "Van": 2}
UNIFIED_NAMES = ["car", "bus", "van", "truck"]


def convert_label(label_path, img_w, img_h):
    lines = []
    for line in label_path.read_text().splitlines():
        parts = line.split()
        cls = parts[0]
        if cls not in KITTI_MAP or KITTI_MAP[cls] is None:
            continue
        x1, y1, x2, y2 = map(float, parts[4:8])
        cx = (x1 + x2) / 2 / img_w
        cy = (y1 + y2) / 2 / img_h
        w = (x2 - x1) / img_w
        h = (y2 - y1) / img_h
        lines.append(f"{KITTI_MAP[cls]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


def main():
    img_files = sorted(SRC_IMGS.glob("*.png"))
    img_files = [f for f in img_files if (SRC_LBLS / f.with_suffix(".txt").name).exists()]

    random.seed(SEED)
    random.shuffle(img_files)
    n_val = int(len(img_files) * VAL_RATIO)
    splits = {"val": img_files[:n_val], "train": img_files[n_val:]}

    for split, files in splits.items():
        (DST / "images" / split).mkdir(parents=True, exist_ok=True)
        (DST / "labels" / split).mkdir(parents=True, exist_ok=True)

        skipped = 0
        for img_path in files:
            lbl_path = SRC_LBLS / img_path.with_suffix(".txt").name
            img = Image.open(img_path)
            w, h = img.size
            yolo_lines = convert_label(lbl_path, w, h)
            if not yolo_lines:
                skipped += 1
                continue
            shutil.copy(img_path, DST / "images" / split / img_path.name)
            (DST / "labels" / split / lbl_path.name).write_text("\n".join(yolo_lines))

        print(f"{split}: {len(files) - skipped} images copied, {skipped} skipped (no valid labels)")

    yaml = f"""path: {DST.resolve().as_posix()}
train: images/train
val: images/val

nc: 4
names: {UNIFIED_NAMES}
"""
    (DST / "dataset.yaml").write_text(yaml)
    print(f"\nDone! dataset.yaml -> {DST / 'dataset.yaml'}")


if __name__ == "__main__":
    main()
