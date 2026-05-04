"""Unified vehicle class taxonomy used by runtime, scripts and reports."""

CLASS_NAMES = {
    0: "car",
    1: "bus",
    2: "van",
    3: "truck",
}

CLASS_LIST = [CLASS_NAMES[i] for i in sorted(CLASS_NAMES)]
CLASS_IDS = tuple(CLASS_NAMES)

SOURCE_NAME_TO_ID = {
    "car": 0,
    "bus": 1,
    "van": 2,
    "truck": 3,
    "others": 3,
}

COCO_TO_UNIFIED = {
    2: 0,  # car
    5: 1,  # bus
    7: 3,  # truck
}


def get_class_name(class_id, default="vehicle"):
    try:
        class_id = int(class_id)
    except (TypeError, ValueError):
        return default
    return CLASS_NAMES.get(class_id, default)


def class_counts_template():
    return {class_id: 0 for class_id in CLASS_IDS}


def normalize_source_name(name):
    if name is None:
        return None
    return SOURCE_NAME_TO_ID.get(str(name).strip().lower())


def normalize_model_class_id(class_id, model_names=None):
    """Map a model class id/name to the unified four-class taxonomy."""
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
    total = sum(counts.get(class_id, 0) for class_id in CLASS_IDS)
    if total <= 0:
        return {class_id: 0.0 for class_id in CLASS_IDS}
    return {
        class_id: counts.get(class_id, 0) / total
        for class_id in CLASS_IDS
    }
