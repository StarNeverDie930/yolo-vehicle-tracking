"""UA-DETRAC 标注到 MOTChallenge GT 的转换脚本。"""

import xml.etree.ElementTree as ET
import os
import argparse

XML_DIR = "data/UA-DETRAC/DETRAC-Train-Annotations-XML"
OUT_DIR = "evaluation/mot_data"


def convert(seq):
    xml_path = os.path.join(XML_DIR, f"{seq}.xml")
    tree = ET.parse(xml_path)
    lines = []
    for frame in tree.findall(".//frame"):
        fnum = int(frame.get("num"))
        for target in frame.findall(".//target"):
            tid = int(target.get("id"))
            box = target.find("box")
            l = float(box.get("left"))
            t = float(box.get("top"))
            w = float(box.get("width"))
            h = float(box.get("height"))
            lines.append(f"{fnum},{tid},{l:.2f},{t:.2f},{w:.2f},{h:.2f},1,-1,-1,-1")
    out_path = os.path.join(OUT_DIR, seq)
    os.makedirs(out_path, exist_ok=True)
    with open(os.path.join(out_path, "gt.txt"), "w") as f:
        f.write("\n".join(lines))
    print(f"GT saved: {out_path}/gt.txt ({len(lines)} rows)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seq", required=True, help="序列名称，如 MVI_20011")
    args = parser.parse_args()
    convert(args.seq)
