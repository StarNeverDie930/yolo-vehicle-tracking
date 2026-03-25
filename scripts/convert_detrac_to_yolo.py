"""
将 UA-DETRAC XML 标注转换为 YOLO 格式，并划分训练集/验证集。

YOLO 标注格式: class_id cx cy w h (归一化到 0-1)
类别映射: car->0, bus->1, van->2, others->3
"""

import os
import xml.etree.ElementTree as ET
import shutil
import random

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETRAC_DIR = os.path.join(BASE_DIR, "data", "UA-DETRAC")
XML_DIR = os.path.join(DETRAC_DIR, "DETRAC-Train-Annotations-XML")
IMG_DIR = os.path.join(DETRAC_DIR, "Insight-MVT_Annotation_Train")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "detrac_yolo")

# UA-DETRAC 车辆类型 -> YOLO 类别ID
VEHICLE_MAP = {"car": 0, "bus": 1, "van": 2, "others": 3}

# 图片尺寸
IMG_W, IMG_H = 960, 540

# 验证集比例
VAL_RATIO = 0.2


def parse_xml(xml_path):
    """解析单个 XML 标注文件，返回 {frame_num: [(class_id, cx, cy, w, h), ...]}"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    annotations = {}

    for frame in root.iter("frame"):
        num = int(frame.get("num"))
        boxes = []
        for target in frame.iter("target"):
            box = target.find("box")
            attr = target.find("attribute")
            if box is None or attr is None:
                continue

            vtype = attr.get("vehicle_type", "others").lower()
            cls_id = VEHICLE_MAP.get(vtype, 3)

            left = float(box.get("left"))
            top = float(box.get("top"))
            w = float(box.get("width"))
            h = float(box.get("height"))

            # 转换为 YOLO 格式 (归一化中心坐标)
            cx = (left + w / 2) / IMG_W
            cy = (top + h / 2) / IMG_H
            nw = w / IMG_W
            nh = h / IMG_H

            # 裁剪到 [0, 1]
            cx = max(0, min(1, cx))
            cy = max(0, min(1, cy))
            nw = max(0, min(1, nw))
            nh = max(0, min(1, nh))

            boxes.append((cls_id, cx, cy, nw, nh))
        annotations[num] = boxes
    return annotations


def main():
    random.seed(42)

    # 获取所有视频序列
    sequences = sorted([f.replace(".xml", "") for f in os.listdir(XML_DIR) if f.endswith(".xml")])
    print(f"共 {len(sequences)} 个视频序列")

    # 按序列划分训练/验证集
    random.shuffle(sequences)
    val_count = max(1, int(len(sequences) * VAL_RATIO))
    val_seqs = set(sequences[:val_count])
    train_seqs = set(sequences[val_count:])
    print(f"训练集: {len(train_seqs)} 个序列, 验证集: {len(val_seqs)} 个序列")

    # 创建输出目录
    for split in ["train", "val"]:
        os.makedirs(os.path.join(OUTPUT_DIR, "images", split), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "labels", split), exist_ok=True)

    total_images = 0
    for seq in sorted(train_seqs | val_seqs):
        xml_path = os.path.join(XML_DIR, f"{seq}.xml")
        img_dir = os.path.join(IMG_DIR, seq)

        if not os.path.exists(img_dir):
            print(f"跳过 {seq}: 图片目录不存在")
            continue

        annotations = parse_xml(xml_path)
        split = "val" if seq in val_seqs else "train"

        for frame_num, boxes in annotations.items():
            img_name = f"img{frame_num:05d}.jpg"
            src_img = os.path.join(img_dir, img_name)
            if not os.path.exists(src_img):
                continue

            # 复制图片（使用 序列名_帧号 避免重名）
            out_name = f"{seq}_{frame_num:05d}"
            dst_img = os.path.join(OUTPUT_DIR, "images", split, f"{out_name}.jpg")
            shutil.copy2(src_img, dst_img)

            # 写标注文件
            dst_label = os.path.join(OUTPUT_DIR, "labels", split, f"{out_name}.txt")
            with open(dst_label, "w") as f:
                for cls_id, cx, cy, w, h in boxes:
                    f.write(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

            total_images += 1

        print(f"  {seq} -> {split} ({len(annotations)} 帧)")

    print(f"\n转换完成! 共 {total_images} 张图片")
    print(f"输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
