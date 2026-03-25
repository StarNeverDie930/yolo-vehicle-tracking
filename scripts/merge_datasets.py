"""
合并 UA-DETRAC (detrac_yolo) 和 KITTI (KITTI_YOLO_merged) 到 merged_yolo

统一类别: ["car", "bus", "van", "truck"]
- detrac_yolo 标注已是统一格式，直接复制
- KITTI_YOLO_merged 标注已通过 kitti_to_yolo.py 映射，直接复制

用法:
  python scripts/merge_datasets.py
"""
import shutil
from pathlib import Path

DETRAC = Path("data/detrac_yolo")
KITTI = Path("data/KITTI_YOLO_merged")
DST = Path("data/merged_yolo")


def copy_split(src_dir, prefix, split):
    img_src = src_dir / "images" / split
    lbl_src = src_dir / "labels" / split
    img_dst = DST / "images" / split
    lbl_dst = DST / "labels" / split
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for img in img_src.iterdir():
        lbl = lbl_src / img.with_suffix(".txt").name
        if not lbl.exists():
            continue
        shutil.copy(img, img_dst / f"{prefix}_{img.name}")
        shutil.copy(lbl, lbl_dst / f"{prefix}_{lbl.name}")
        count += 1
    return count


def main():
    for split in ("train", "val"):
        n_detrac = copy_split(DETRAC, "detrac", split)
        n_kitti = copy_split(KITTI, "kitti", split)
        print(f"{split}: detrac={n_detrac}, kitti={n_kitti}, total={n_detrac + n_kitti}")

    print(f"\nDone! Merged dataset -> {DST}")
    print("Next: python scripts/train.py --model runs/detrac_train/weights/best.pt "
          "--data scripts/merged.yaml --epochs 30 --lr0 0.001 --freeze 10 --name merged_train")


if __name__ == "__main__":
    main()
