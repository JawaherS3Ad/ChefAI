# -*- coding: utf-8 -*-
"""
vision_agent.py — GPT-5-Pro Vision (OpenAI Responses API)
---------------------------------------------------------
تحليل صورة الثلاجة باستخدام GPT-5-Pro من OpenAI — النسخة الجديدة.
"""

import os
import base64
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------------------
# تجهيز الصورة (base64 / URL / ملف)
# -------------------------------------------------------------
def _image_part(image: str) -> Dict[str, Any]:
    # إذا كانت data:image جاهزة
    if image.startswith("data:image"):
        return {"type": "input_image", "image_url": image}

    # إذا كانت URL مباشرة
    if image.startswith("http://") or image.startswith("https://"):
        return {"type": "input_image", "image_url": image}

    # إذا كانت base64 خام
    if len(image) > 500 and not os.path.exists(image):
        return {"type": "input_image", "image_url": f"data:image/png;base64,{image}"}

    # إذا كان ملف محلي → نحوله base64
    with open(image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    ext = "jpeg" if image.lower().endswith((".jpg", ".jpeg")) else "png"
    return {
        "type": "input_image",
        "image_url": f"data:image/{ext};base64,{b64}"
    }


# -------------------------------------------------------------
# برومبت شديد الصرامة — Ultra Strict Mode
# -------------------------------------------------------------
PROMPT_VISION = """
You are a zero-tolerance food ingredient detection system.

Behavior rules:
- You MUST detect **every** visible ingredient. Missing items = failure.
- You MUST NOT guess, infer, imagine, or assume items not visually confirmed.
- All outputs must be fully grounded in the pixels of the image.
- If any item cannot be identified with 90% confidence → set:
    { "name_en": "unknown", "state": "unknown", "inferred": false }
- If an item appears partially visible, mark inferred=true.
- If any item is repeated, miscounted, or incorrectly grouped → your output is invalid.
- NO explanations, NO text outside JSON.
- Output MUST be valid JSON ONLY.

JSON structure:
{
  "ingredients": [
    {
      "name_ar": "",
      "quantity_estimate": 0,
      "unit": "piece | bundle | gram | ml",
      "state": "fresh | frozen | cooked | canned | jarred | unknown",
      "category": "vegetable | fruit | protein | carb | dairy | condiment | beverage | other | unknown",
      "confidence": 0.0,
      "inferred": false
    }
  ],
  "notes": ""
}
"""


# -------------------------------------------------------------
# تحليل الصورة باستخدام GPT-5-Pro (Responses API)
# -------------------------------------------------------------
def analyze_fridge_image(image: str):
    try:
        response = client.responses.create(
            model="gpt-5-pro-2025-10-06",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT_VISION},
                        _image_part(image)
                    ]
                }
            ],
            max_output_tokens=1500
        )

        # استخراج النص النهائي من Responses API
        return response.output_text

    except Exception as e:
        print("⚠️ Vision model error:", e)
        return '{"ingredients": [], "notes": "vision model failed"}'


# -------------------------------------------------------------
# اختبار محلي
# -------------------------------------------------------------
if __name__ == "__main__":
    print("🔹 Local test for GPT-5-Pro Vision...")

    # ضعي هنا أي صورة تريدين اختبارها
    out = analyze_fridge_image("/Users/jawaher.s/Projects/CHEFAI/Example_fridge.png")  # أو مسار آخر
    print(out)
