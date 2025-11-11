# -*- coding: utf-8 -*-
# قواميس وتطبيع أسماء

# عناصر عامة ممنوعة (نحذفها أو نحاول تفصيلها لاحقًا)
BANNED_BUCKETS_EN = {
    "mixed vegetables", "cut vegetables", "frozen vegetables",
    "mixed fruits", "frozen meats", "sauces"
}
BANNED_BUCKETS_AR = {"خضروات متنوعة", "خضروات مقطعة", "خضروات مجمدة", "فواكه متنوعة", "لحوم مجمدة", "صلصات"}

# مرادفات عربية → شكل موحّد
AR_NORMALIZE = {
    "بندورة": "طماطم",
    "فليفلة": "فلفل رومي",
    "فلفل": "فلفل رومي",  # ممكن تخصيص لاحقًا (أخضر/أحمر) حسب الرؤية
    "كوسا": "كوسة",
}

# إنجليزي → عربي (أساسي للدعم لما name_ar="")
EN2AR = {
    "tomato": "طماطم",
    "green bell pepper": "فلفل رومي أخضر",
    "red bell pepper": "فلفل رومي أحمر",
    "broccoli": "بروكلي",
    "cucumber": "خيار",
    "potato": "بطاطس",
    "egg": "بيض",
    "beef cubes": "لحم بقري مكعبات",
    "chicken breast": "صدر دجاج",
    "ground beef": "لحم مفروم",
    "pasta": "مكرونة",
    "mustard": "خردل",
    "tomato sauce": "صلصة طماطم",
    "pickle": "مخلل",
}

# وحدات عربية مقترحة
UNIT_FALLBACK = "حبة"

def is_bucket(name_en: str, name_ar: str) -> bool:
    ne = (name_en or "").strip().lower()
    na = (name_ar or "").strip()
    return ne in BANNED_BUCKETS_EN or na in BANNED_BUCKETS_AR

def normalize_ar(name_ar: str) -> str:
    base = (name_ar or "").strip()
    return AR_NORMALIZE.get(base, base)
