# -*- coding: utf-8 -*-
import json
from typing import Any, Dict

def parse_vision_json(raw: str | Dict[str, Any]) -> Dict[str, Any]:
    """يحوّل خرج وكيل الرؤية إلى dict مضمون حتى لو داخل أسوار أو فيه نص إضافي."""
    if isinstance(raw, dict):
        return raw
    text = str(raw or "").strip()
    # إزالة أسوار الأكواد
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        first, last = text.find("{"), text.rfind("}")
        if first != -1 and last != -1:
            return json.loads(text[first:last+1])
    except Exception:
        pass
    try:
        return json.loads(text)
    except Exception:
        return {"ingredients": [], "notes": text}
