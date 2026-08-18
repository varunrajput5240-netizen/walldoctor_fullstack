"""
This module is the fix for the single biggest flaw in the original site:
the frontend called api.anthropic.com directly from the browser with no
API key, so in production it silently always fell back to a crude
heuristic while presenting it as a full AI report.

Here the real call happens server-side, where the key is safe. If the AI
call fails for any reason, we still fall back to the heuristic -- but we
tag the result with source="fallback" so the frontend can be honest with
the user about which one actually ran, instead of hiding it.
"""
import base64
import io
import json
import math
import re

import httpx
from PIL import Image

from app.config import get_settings

settings = get_settings()

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

PROMPT = """You are an experienced home inspector and repair consultant specializing in wall and floor damage assessment.
Look carefully at the actual visual details in THIS specific photo only — texture, color variation, stains, cracks, lines, and lighting. Do not give a generic or templated answer; base every field strictly on what is visibly present in this exact image. If the surface looks clean and undamaged, honestly report it as healthy rather than inventing a problem.
Respond ONLY in the JSON format below, no extra text, no markdown, no code fences. Provide both English and Hindi (Devanagari script) versions of each text field as shown.

{
  "problem_detected": true or false,
  "problem_type_en": "name of the problem in English, e.g. Crack, Dampness/Seepage, Mold, Peeling Paint, Broken Tile, Uneven Flooring, Plaster Damage, or 'Healthy Surface' if nothing is wrong",
  "problem_type_hi": "same problem name in Hindi",
  "surface_en": "Wall or Floor", "surface_hi": "दीवार or फर्श",
  "severity": a number from 1 to 5 based on how extensive the damage actually looks,
  "description_en": "2-3 sentence description referencing specific visual details you actually see in this photo, in English",
  "description_hi": "same description in Hindi",
  "likely_cause_en": "one sentence on the probable cause based on the visible evidence",
  "likely_cause_hi": "same cause in Hindi",
  "recommended_solution_en": "2-3 sentence practical, specific repair recommendation",
  "recommended_solution_hi": "same recommendation in Hindi",
  "service_category": "one of: crack_repair, waterproofing, mold_treatment, painting, flooring, plastering, none",
  "urgency_en": "Low, Medium, or High", "urgency_hi": "कम, मध्यम, or अधिक"
}"""

REQUIRED_FIELDS = [
    "problem_detected", "problem_type_en", "problem_type_hi", "surface_en", "surface_hi",
    "severity", "description_en", "description_hi", "likely_cause_en", "likely_cause_hi",
    "recommended_solution_en", "recommended_solution_hi", "service_category", "urgency_en", "urgency_hi",
]


async def call_claude_vision(image_bytes: bytes) -> dict | None:
    """Returns a parsed diagnosis dict, or None if the AI call failed/was malformed."""
    if not settings.anthropic_api_key:
        return None

    b64 = base64.b64encode(image_bytes).decode()
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": settings.anthropic_model,
        "max_tokens": 1000,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(ANTHROPIC_URL, headers=headers, json=body)
        if resp.status_code != 200:
            return None
        data = resp.json()
        text_block = next((b["text"] for b in data.get("content", []) if b.get("type") == "text"), None)
        if not text_block:
            return None
        cleaned = re.sub(r"```json|```", "", text_block).strip()
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            cleaned = match.group(0)
        parsed = json.loads(cleaned)
        if not all(f in parsed for f in REQUIRED_FIELDS):
            return None
        return parsed
    except (httpx.HTTPError, json.JSONDecodeError, KeyError):
        return None


def compute_image_stats(image_bytes: bytes) -> dict:
    """Port of the frontend's resizeImage() sampling: average RGB + luma variance."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((60, 60))
    pixels = list(img.getdata())
    if not pixels:
        return {"r": 128, "g": 128, "b": 128, "brightness": 128, "variance": 0}

    r_sum = sum(p[0] for p in pixels)
    g_sum = sum(p[1] for p in pixels)
    b_sum = sum(p[2] for p in pixels)
    count = len(pixels)
    lumas = [0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in pixels]
    brightness = sum(lumas) / count
    variance = math.sqrt(sum((l - brightness) ** 2 for l in lumas) / count)

    return {"r": r_sum / count, "g": g_sum / count, "b": b_sum / count, "brightness": brightness, "variance": variance}


def fallback_diagnosis(stats: dict) -> dict:
    """Direct port of the frontend's fallbackDiagnosis() heuristic. Used only when the
    real AI call is unavailable or fails -- and always labeled as such downstream."""
    r, g, b = stats["r"], stats["g"], stats["b"]
    brightness, variance = stats["brightness"], stats["variance"]

    greenish = g > r and g > b
    yellow_brown = r > 140 and g > 100 and b < 110 and r > b + 30
    dark_patchy = brightness < 95 and variance > 28
    high_contrast = variance > 42
    very_even = variance < 14 and brightness > 150

    def sev_from_variance(base: int) -> int:
        return max(1, min(5, round(base + (variance - 25) / 12)))

    def urgency_from_severity(s: int) -> tuple[str, str]:
        if s >= 4:
            return "High", "अधिक"
        if s >= 3:
            return "Medium", "मध्यम"
        return "Low", "कम"

    if greenish and brightness < 140:
        sev = sev_from_variance(3)
        u_en, u_hi = urgency_from_severity(sev)
        return {
            "problem_detected": True, "problem_type_en": "Mold", "problem_type_hi": "फफूंद",
            "surface_en": "Wall", "surface_hi": "दीवार", "severity": sev,
            "description_en": "Patchy greenish-dark discoloration is visible across the surface, consistent with fungal growth in a damp, poorly ventilated area.",
            "description_hi": "सतह पर धब्बेदार हरा-काला रंग दिखाई दे रहा है, जो नमी और खराब हवादार क्षेत्र में फफूंद बनने के अनुरूप है।",
            "likely_cause_en": "Prolonged moisture exposure with poor ventilation in this area.",
            "likely_cause_hi": "इस क्षेत्र में लंबे समय से नमी और खराब हवा का आना-जाना।",
            "recommended_solution_en": "Clean the affected area with an anti-fungal solution, let it dry fully, then apply a mold-resistant primer before repainting.",
            "recommended_solution_hi": "प्रभावित हिस्से को एंटी-फंगल घोल से साफ करें, पूरी तरह सूखने दें, फिर दोबारा पेंट करने से पहले मोल्ड-रेसिस्टेंट प्राइमर लगाएं।",
            "service_category": "mold_treatment", "urgency_en": u_en, "urgency_hi": u_hi,
        }

    if yellow_brown:
        sev = sev_from_variance(3)
        u_en, u_hi = urgency_from_severity(sev)
        return {
            "problem_detected": True, "problem_type_en": "Dampness/Seepage", "problem_type_hi": "सीलन/नमी",
            "surface_en": "Wall", "surface_hi": "दीवार", "severity": sev,
            "description_en": "Yellow-brown staining with an uneven tide-mark pattern suggests water seepage moving through the surface.",
            "description_hi": "पीले-भूरे रंग के धब्बे और असमान निशान बताते हैं कि पानी सतह के अंदर से रिस रहा है।",
            "likely_cause_en": "A hidden leak or moisture ingress from an external wall or plumbing line.",
            "likely_cause_hi": "बाहरी दीवार या पाइपलाइन से छुपी हुई रिसाव।",
            "recommended_solution_en": "Trace and seal the moisture source first, let the wall dry out completely, then apply a waterproof coating in two layers.",
            "recommended_solution_hi": "पहले नमी के स्रोत का पता लगाकर उसे बंद करें, दीवार को पूरी तरह सूखने दें, फिर दो परतों में वॉटरप्रूफ कोटिंग लगाएं।",
            "service_category": "waterproofing", "urgency_en": u_en, "urgency_hi": u_hi,
        }

    if high_contrast:
        sev = sev_from_variance(3)
        u_en, u_hi = urgency_from_severity(sev)
        return {
            "problem_detected": True, "problem_type_en": "Crack", "problem_type_hi": "दरार",
            "surface_en": "Wall", "surface_hi": "दीवार", "severity": sev,
            "description_en": "A sharp, high-contrast line runs across the surface, consistent with a structural crack.",
            "description_hi": "सतह पर एक स्पष्ट, गहरी रेखा दिख रही है, जो संरचनात्मक दरार के अनुरूप है।",
            "likely_cause_en": "Structural settling or thermal expansion over time.",
            "likely_cause_hi": "समय के साथ संरचना का धंसना या तापमान के कारण फैलाव।",
            "recommended_solution_en": "Widen the crack slightly to remove loose material, fill it with a flexible crack-filler compound, sand smooth once cured, then prime and repaint.",
            "recommended_solution_hi": "दरार को थोड़ा चौड़ा कर ढीला मलबा हटाएं, फिर फ्लेक्सिबल क्रैक-फिलर से भरें, सूखने के बाद रेत से चिकना करें, फिर प्राइमर लगाकर पेंट करें।",
            "service_category": "crack_repair", "urgency_en": u_en, "urgency_hi": u_hi,
        }

    if dark_patchy:
        sev = sev_from_variance(2)
        u_en, u_hi = urgency_from_severity(sev)
        return {
            "problem_detected": True, "problem_type_en": "Plaster Damage", "problem_type_hi": "प्लास्टर क्षति",
            "surface_en": "Wall", "surface_hi": "दीवार", "severity": sev,
            "description_en": "Uneven dark patches suggest the plaster layer is loosening or has started crumbling in places.",
            "description_hi": "असमान गहरे धब्बे बताते हैं कि प्लास्टर की परत ढीली हो रही है या कुछ जगहों पर उखड़ने लगी है।",
            "likely_cause_en": "Aging plaster losing adhesion to the base wall.",
            "likely_cause_hi": "पुराना प्लास्टर दीवार से अपनी पकड़ खो रहा है।",
            "recommended_solution_en": "Remove the loose or crumbling plaster down to a solid base, apply a bonding coat, then re-plaster the patch in layers.",
            "recommended_solution_hi": "ढीले या उखड़ते प्लास्टर को ठोस सतह तक हटाएं, बॉन्डिंग कोट लगाएं, फिर उस हिस्से पर परतों में दोबारा प्लास्टर करें।",
            "service_category": "plastering", "urgency_en": u_en, "urgency_hi": u_hi,
        }

    if very_even:
        return {
            "problem_detected": False, "problem_type_en": "Healthy Surface", "problem_type_hi": "स्वस्थ सतह",
            "surface_en": "Wall", "surface_hi": "दीवार", "severity": 1,
            "description_en": "The surface appears smooth and evenly toned with no visible cracks, staining, or damage.",
            "description_hi": "सतह चिकनी और एकसार दिख रही है, कोई दरार, दाग या क्षति दिखाई नहीं दे रही।",
            "likely_cause_en": "No issues detected.", "likely_cause_hi": "कोई समस्या नहीं मिली।",
            "recommended_solution_en": "No repair needed right now — just keep an eye on this area during your regular home maintenance checks.",
            "recommended_solution_hi": "अभी किसी मरम्मत की ज़रूरत नहीं है — बस अपने नियमित रखरखाव के दौरान इस जगह पर नज़र रखें।",
            "service_category": "none", "urgency_en": "Low", "urgency_hi": "कम",
        }

    sev = sev_from_variance(2)
    u_en, u_hi = urgency_from_severity(sev)
    return {
        "problem_detected": True, "problem_type_en": "Peeling Paint", "problem_type_hi": "उखड़ता पेंट",
        "surface_en": "Wall", "surface_hi": "दीवार", "severity": sev,
        "description_en": "The surface tone is uneven, consistent with paint that has started to fade, flake, or peel in patches.",
        "description_hi": "सतह का रंग असमान है, जो जगह-जगह पेंट के फीका पड़ने, उखड़ने या छिलने के अनुरूप है।",
        "likely_cause_en": "Age of the existing paint layer or minor moisture beneath it.",
        "likely_cause_hi": "मौजूदा पेंट की उम्र या नीचे मामूली नमी।",
        "recommended_solution_en": "Scrape away the loose, flaking paint, sand the area smooth, apply a suitable primer, then repaint with two coats.",
        "recommended_solution_hi": "उखड़े हुए ढीले पेंट को खुरचें, सतह को रेत से चिकना करें, उपयुक्त प्राइमर लगाएं, फिर दो कोट पेंट करें।",
        "service_category": "painting", "urgency_en": u_en, "urgency_hi": u_hi,
    }


async def diagnose(image_bytes: bytes) -> tuple[dict, str]:
    """Returns (diagnosis_dict, source) where source is 'ai' or 'fallback'."""
    ai_result = await call_claude_vision(image_bytes)
    if ai_result is not None:
        return ai_result, "ai"
    stats = compute_image_stats(image_bytes)
    return fallback_diagnosis(stats), "fallback"
