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
# -*- coding: utf-8 -*-
# قاموس ثنائي اللغة: إنجليزي وصيني إلى عربي

EN2AR = {
    "tomato": "طماطم",
    "onion": "بصل",
    "garlic": "ثوم",
    "bell pepper": "فلفل رومي",
    "green pepper": "فلفل أخضر",
    "carrot": "جزر",
    "potato": "بطاطس",
    "cucumber": "خيار",
    "lettuce": "خس",
    "spinach": "سبانخ",
    "broccoli": "بروكلي",
    "cauliflower": "قرنبيط",
    "eggplant": "باذنجان",
    "zucchini": "كوسة",
    "apple": "تفاح",
    "banana": "موز",
    "pear": "كمثرى",
    "peach": "خوخ",
    "strawberry": "فراولة",
    "lemon": "ليمون",
    "lime": "ليمون أخضر",
    "orange": "برتقال",
    "watermelon": "بطيخ",
    "milk": "حليب",
    "egg": "بيض",
    "pasta": "مكرونة",
    "bread": "خبز",
    "butter": "زبدة",
    "cheese": "جبن",
    "rice": "أرز",
    "meat": "لحم",
    "chicken": "دجاج",
    "fish": "سمك",
    "shrimp": "جمبري",
    "salt": "ملح",
    "sugar": "سكر",
    "oil": "زيت",
    "flour": "دقيق",
    "chicken breast": "صدر دجاج",
    "green beans": "فاصوليا خضراء",
    "yogurt": "زبادي",
    "mango": "مانجو",
    "chili pepper": "فلفل حار",
    "tomato sauce": "صلصة طماطم",
    "garlic powder": "بودرة ثوم",
    "onion powder": "بودرة بصل"
}

ZH2AR = {
    "番茄": "طماطم",
    "洋葱": "بصل",
    "大蒜": "ثوم",
    "辣椒": "فلفل رومي",
    "胡椒": "فلفل",
    "胡萝卜": "جزر",
    "土豆": "بطاطس",
    "黄瓜": "خيار",
    "生菜": "خس",
    "菠菜": "سبانخ",
    "西兰花": "بروكلي",
    "花椰菜": "قرنبيط",
    "茄子": "باذنجان",
    "西葫芦": "كوسة",
    "苹果": "تفاح",
    "香蕉": "موز",
    "梨": "كمثرى",
    "桃子": "خوخ",
    "草莓": "فراولة",
    "柠檬": "ليمون",
    "橙子": "برتقال",
    "西瓜": "بطيخ",
    "牛奶": "حليب",
    "鸡蛋": "بيض",
    "意大利面": "مكرونة",
    "面包": "خبز",
    "黄油": "زبدة",
    "奶酪": "جبن",
    "米饭": "أرز",
    "牛肉": "لحم",
    "鸡肉": "دجاج",
    "鱼": "سمك",
    "虾": "جمبري",
    "盐": "ملح",
    "糖": "سكر",
    "油": "زيت",
    "面粉": "دقيق",
}

def lookup_to_ar(name_en: str = "", name_zh: str = "", fallback: str = "") -> str:
    """
    يحوّل اسم (EN أو ZH) إلى عربي باستخدام القواميس.
    - يجرّب EN2AR أولاً
    - ثم ZH2AR
    - وإلا يرجّع fallback (أو الاسم نفسه)
    """
    ne = (name_en or "").strip().lower()
    nz = (name_zh or "").strip()
    if ne and ne in EN2AR:
        return EN2AR[ne]
    if nz and nz in ZH2AR:
        return ZH2AR[nz]
    return (fallback or name_en or name_zh or "").strip()

# وحدات عربية مقترحة
UNIT_FALLBACK = "حبة"

def is_bucket(name_en: str, name_ar: str) -> bool:
    ne = (name_en or "").strip().lower()
    na = (name_ar or "").strip()
    return ne in BANNED_BUCKETS_EN or na in BANNED_BUCKETS_AR

def normalize_ar(name_ar: str) -> str:
    base = (name_ar or "").strip()
    return AR_NORMALIZE.get(base, base)
