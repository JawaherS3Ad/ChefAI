import urllib.parse, random
from typing import List, Dict, Any

def get_shopping_suggestions(missing_items: List[str]) -> List[Dict[str, Any]]:
    if not missing_items:
        return []
    suggestions = []
    for item in missing_items:
        q = urllib.parse.quote(item)
        price = round(7 + random.random() * 10, 2)
        suggestions.append({
            "item": item,
            "quantity": 1,
            "unit": "علبة",
            "vendor": "HungryStation",
            "estimated_price": f"{price} SAR",
            "product_url": f"https://hungerstation.com/search?q={q}"
        })
    return suggestions
