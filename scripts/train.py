"""
使用 UA-DETRAC 数据集训练 YOLOv11 车辆检测模型。

用法:
  1. 先运行 convert_detrac_to_yolo.py 转换数据集
  2. 再运行本脚本开始训练

示例:
  python scripts/train.py --model yolo11m.pt --epochs 50 --batch 8
  python scripts/train.py --model yolo11m.pt --epochs 100 --lr0 0.005 --optimizer AdamW
  python scripts/train.py --resume runs/detrac_train/weights/last.pt
"""

import argparse
import os

# 强制离线模式，禁止自动联网检查/下载模型
os.environ["YOLO_OFFLINE"] = "1"

from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    p = argparse.ArgumentParser(
        description="YOLOv11 车辆检测训练脚本",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ---- 基础参数 ----
    p.add_argument("--model", default="yolo11m.pt", help="预训练模型路径 (yolo11n/s/m/l/x.pt)")
    p.add_argument("--data", default=None, help="数据集配置文件路径 (默认 scripts/detrac.yaml)")
    p.add_argument("--epochs", type=int, default=50, help="训练轮数")
    p.add_argument("--batch", type=int, default=8, help="批大小 (显存不够就调小)")
    p.add_argument("--imgsz", type=int, default=640, help="输入图片尺寸")
    p.add_argument("--device", default="", help="设备: 0/1/cpu/空=自动")
    p.add_argument("--workers", type=int, default=4, help="数据加载线程数")
    p.add_argument("--resume", default=None, help="从断点恢复训练 (传入 last.pt 路径)")
    p.add_argument("--name", default="detrac_train", help="实验名称")

    # ---- 学习率与优化器 ----
    p.add_argument("--optimizer", default="auto", help="优化器: SGD/Adam/AdamW/auto")
    p.add_argument("--lr0", type=float, default=0.01, help="初始学习率")
    p.add_argument("--lrf", type=float, default=0.01, help="最终学习率 = lr0 * lrf")
    p.add_argument("--momentum", type=float, default=0.937, help="SGD 动量")
    p.add_argument("--weight-decay", type=float, default=0.0005, help="权重衰减")
    p.add_argument("--warmup-epochs", type=float, default=2.0, help="预热轮数")
    p.add_argument("--cos-lr", action="store_true", help="使用余弦学习率调度")

    # ---- 数据增强 ----
    p.add_argument("--mosaic", type=float, default=1.0, help="Mosaic 增强概率 (0-1)")
    p.add_argument("--mixup", type=float, default=0.0, help="MixUp 增强概率 (0-1)")
    p.add_argument("--degrees", type=float, default=0.0, help="旋转角度范围")
    p.add_argument("--scale", type=float, default=0.5, help="缩放范围")
    p.add_argument("--fliplr", type=float, default=0.5, help="水平翻转概率")
    p.add_argument("--close-mosaic", type=int, default=10, help="最后 N 轮关闭 Mosaic")

    # ---- 正则化 ----
    p.add_argument("--dropout", type=float, default=0.0, help="Dropout 比率 (仅分类头)")
    p.add_argument("--label-smoothing", type=float, default=0.0, help="标签平滑")

    # ---- 其他 ----
    p.add_argument("--patience", type=int, default=10, help="早停耐心值 (0=不早停)")
    p.add_argument("--save-period", type=int, default=-1, help="每 N 轮保存一次 (-1=只保存 best/last)")
    p.add_argument("--val", action="store_true", default=True, help="训练时进行验证")
    p.add_argument("--no-val", dest="val", action="store_false", help="训练时不验证")
    p.add_argument("--cache", action="store_true", help="缓存图片到内存 (加速训练但占内存)")
    p.add_argument("--freeze", type=int, default=0, help="冻结前 N 层 (迁移学习)")

    args = p.parse_args()

    # 断点恢复
    if args.resume:
        model = YOLO(args.resume)
        model.train(resume=True)
        return

    # 数据集配置
    data_yaml = args.data or os.path.join(os.path.dirname(os.path.abspath(__file__)), "detrac.yaml")

    # 模型路径: 支持直接写文件名，自动在项目根目录查找
    model_path = args.model
    if not os.path.exists(model_path):
        alt = os.path.join(BASE_DIR, model_path)
        if os.path.exists(alt):
            model_path = alt

    model = YOLO(model_path)

    # Ultralytics 自带进度条和训练日志，verbose=True 即可
    model.train(
        data=data_yaml,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device or None,
        workers=args.workers,
        project=os.path.join(BASE_DIR, "runs"),
        name=args.name,
        exist_ok=True,
        pretrained=True,
        verbose=True,
        # 学习率与优化器
        optimizer=args.optimizer,
        lr0=args.lr0,
        lrf=args.lrf,
        momentum=args.momentum,
        weight_decay=args.weight_decay,
        warmup_epochs=args.warmup_epochs,
        cos_lr=args.cos_lr,
        # 数据增强
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        flipud=0.0,
        fliplr=args.fliplr,
        mosaic=args.mosaic,
        mixup=args.mixup,
        degrees=args.degrees,
        scale=args.scale,
        close_mosaic=args.close_mosaic,
        # 正则化
        dropout=args.dropout,
        # 其他
        patience=args.patience,
        save_period=args.save_period,
        val=args.val,
        cache=args.cache,
        freeze=args.freeze if args.freeze > 0 else None,
    )

    print("\n" + "=" * 60)
    print("训练完成!")
    print(f"最佳模型: runs/{args.name}/weights/best.pt")
    print(f"最新模型: runs/{args.name}/weights/last.pt")
    print("=" * 60)
    print("使用方法: 修改 config.yaml 中 model.path 为上述 best.pt 路径")


if __name__ == "__main__":
    main()
