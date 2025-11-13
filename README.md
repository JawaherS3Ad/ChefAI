
# 🍳 ChefAI — Hybrid AI Orchestrator

**Two-Step Recipe Generation System (Vision + LLM + LangGraph Agents)**

ChefAI هو نظام ذكاء اصطناعي هجين بُني خصيصًا للهاكاثون.
يعالج صورة الثلاجة، ثم يولّد وصفات ذكية بناءً على المكونات + تفضيلات المستخدم.

النظام يجمع بين:

* **رؤية حاسوبية** (Computer Vision)
* **فاعلون ذكيون** (Autonomous Agents)
* **تنظيم هجين عبر LangGraph**
* **نماذج LLM مجانية** (Qwen) + تحسين لغوي باستخدام NameFixer Agent
* **خطوات معالجة منفصلة ومتوافقة مع الـFrontend**

والمعمارية الجديدة تعتمد على *Two-Step API Workflow* لضمان مرونة وتفاعل أفضل.

---

## 🚀 المميزات الرئيسية

### 1) نظام هجين Hybrid Orchestrator

دمج بين:

* Vision Agent
* NameFixer Agent
* Recipe Generator Agent
* Shopping Agent
  مع orchestrator مبني على LangGraph.

### 2) Two-Step API (مطلوب للFrontend + UX)

مصمّم ليتوافق مع تجربة المستخدم، ولعزل المهام المعقدة في مراحل مستقلة.

### 3) تحسين جودة نموذج Qwen

بسبب محدودية النموذج (لغة صينية)، NameFixer Agent:

* يستخدم قاموس داخلي ZH→AR
* ولديه fallback إلى LLM
  الهدف: رفع دقة المكونات والوصفات رغم استخدام نموذج مجاني.

### 4) قابل للتشغيل على Railway بدون أي تبعيات معقدة

لا Redis
لا Celery
لا Workers
فقط FastAPI + LangGraph + OpenRouter

---

# 🧩 المعمارية العامة

```
           STEP 1 — /api/chef/analyze
┌─────────────────────────────────────────────┐
│ Vision Agent → NameFixer Agent              │
│ (يستخرج المكونات فقط)                       │
└─────────────────────────────────────────────┘

           STEP 2 — /api/chef/generate
┌─────────────────────────────────────────────┐
│ Recipe Generator Agent → Shopping Agent     │
│ (يولّد وصفة + missing items + روابط شراء)  │
└─────────────────────────────────────────────┘
```

هذا الفصل يعطي:

* سرعة
* قابلية اختبار
* توافق كامل مع واجهة المستخدم

---

# 🔥 الـAPI Endpoints

## 1️⃣ **تحليل الصورة فقط**

**POST /api/chef/analyze**

#### Request:

```json
{
  "image_base64": "..."
}
```

#### Response:

```json
{
  "detected_ingredients": [...],
  "uncertain": [...],
  "notes": "..."
}
```

---

## 2️⃣ **توليد الوصفة**

**POST /api/chef/generate**

#### Request:

```json
{
  "ingredients": [...],
  "meal_type": "dinner",
  "time_limit": "20",
  "servings": 2,
  "cuisines": ["italian"]
}
```

#### Response:

```json
{
  "recipe_name": "...",
  "steps": [...],
  "ingredients_list": [...],
  "missing_items": [...],
  "shopping_links": [...]
}
```

---

# 🏗️ الهيكلة العامة للمشروع (بعد إعادة البناء)

```
/chef-backend
│
├── main.py                    # FastAPI Endpoints (Analyze + Generate)
├── agents.py                  # تعريف الوكلاء (Vision/NameFixer/Recipe/Shopping)
├── vision_agent.py
├── recipe_generator.py
├── shopping_integration.py
├── langgraph_core.py          # Graphs مفصولة (AnalyzeGraph + GenerateGraph)
├── ontology.py                # القواميس والمفاهيم المشتركة
├── utils.py                   # أدوات مساعدة
│
├── cache/                     # تخزين النتائج أثناء التطوير
└── README.md
```

---

# 🔧 أوامر التشغيل محليًا

### تثبيت الحزم

```
pip install -r requirements.txt
```

### تشغيل الخادم

```
uvicorn main:app --reload
```

### فتح السواجّر

```
http://localhost:8000/docs
```

---

# ☁️ النشر على Railway

1. اربط المستودع بـRailway
2. تأكد أن ملف التشغيل هو:

```
python main.py
```

أو

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

3. أضف متغيرات البيئة:

```
OPENROUTER_API_KEY=...
```

---

# 🧠 سبب اختيار LangGraph في الهاكاثون

اخترنا LangGraph لإظهار نظام “ذكاء توكيلي Agentic” بدل مجرد استدعاء LLM:

* يوضح أن النظام Modular وقابل للتوسّع
* يسمح بصنع Orchestrator هجيني
* يفصل المنطق إلى Agents واضحة
* سهل التوسع مستقبلًا للوصفات الشخصية أو OCR
* يعكس **تصميم هندسي صحيح** وليس مجرد LLM call

