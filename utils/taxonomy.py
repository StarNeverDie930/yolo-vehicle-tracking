"""项目统一的车辆类别体系。

检测模型、计数统计、轨迹记录和界面展示都依赖这里的类别编号。
把类别定义集中在这个文件里，可以避免不同模块各自维护一套
car/bus/van/truck 映射而导致统计口径不一致。
"""

# 系统内部统一使用 0~3 四个类别 ID；后续统计、绘图和报表都以此为准。
CLASS_NAMES = {
    0: "car",
    1: "bus",
    2: "van",
    3: "truck",
}

# 按 ID 顺序生成展示用类别名列表，供 UI 或下拉选项按固定顺序展示。
CLASS_LIST = [CLASS_NAMES[i] for i in sorted(CLASS_NAMES)]

# 固定类别 ID 集合，供计数模板、百分比计算等统计逻辑遍历。
CLASS_IDS = tuple(CLASS_NAMES)

# 数据集、模型输出或脚本中可能出现的原始类别名到统一 ID 的映射。
SOURCE_NAME_TO_ID = {
    "car": 0,
    "bus": 1,
    "van": 2,
    "truck": 3,
    # 部分车辆数据集会把大型车或未细分类别标成 others，这里并入 truck。
    "others": 3,
}

# COCO 预训练模型的车辆相关类别 ID 到本项目四类体系的映射。
# COCO 中没有 van 类，因此只显式接入 car/bus/truck 三类。
COCO_TO_UNIFIED = {
    2: 0,  # car
    5: 1,  # bus
    7: 3,  # truck
}


def get_class_name(class_id, default="vehicle"):
    """根据统一类别 ID 获取类别名，无法识别时返回默认名称。"""
    try:
        class_id = int(class_id)
    except (TypeError, ValueError):
        return default
    return CLASS_NAMES.get(class_id, default)


def class_counts_template():
    """创建包含所有统一类别的计数字典，初始值均为 0。"""
    return {class_id: 0 for class_id in CLASS_IDS}


def normalize_source_name(name):
    """把外部类别名标准化为项目内部统一类别 ID。"""
    if name is None:
        return None
    return SOURCE_NAME_TO_ID.get(str(name).strip().lower())


def normalize_model_class_id(class_id, model_names=None):
    """把模型输出类别映射到项目统一四类 taxonomy。

    自训练模型通常已经使用 0~3 的类别 ID；COCO 或其他来源的模型则可能
    携带自己的类别名。这里优先根据模型类别名映射，映射不到时再判断
    class_id 是否已经属于项目统一类别。
    """
    class_id = int(class_id)
    if model_names:
        raw_name = model_names.get(class_id)
        mapped = normalize_source_name(raw_name)
        if mapped is not None:
            return mapped
    if class_id in CLASS_NAMES:
        return class_id
    return None


def class_percentages(counts):
    """根据各类别计数计算占比，返回值仍按统一类别 ID 组织。"""
    total = sum(counts.get(class_id, 0) for class_id in CLASS_IDS)
    if total <= 0:
        return {class_id: 0.0 for class_id in CLASS_IDS}
    return {
        class_id: counts.get(class_id, 0) / total
        for class_id in CLASS_IDS
    }
