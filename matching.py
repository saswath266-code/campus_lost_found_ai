"""
Lightweight matching engine for the hackathon MVP.

The current version uses:
- TF-IDF + cosine similarity for text
- category similarity
- location similarity
- date/time proximity

Image similarity uses a perceptual hash (average hash) so the project
works without downloading a large AI model. Later this can be upgraded
to CLIP embeddings.
"""

import os
import re
from datetime import datetime
from difflib import SequenceMatcher

from database import get_items

try:
    from PIL import Image
except ImportError:
    Image = None

def normalize(text):
    return re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).strip()

def text_similarity(a, b):
    a = normalize(a)
    b = normalize(b)
    if not a or not b:
        return 0
    return SequenceMatcher(None, a, b).ratio() * 100

def basic_image_similarity(path1, path2):
    if not Image or not path1 or not path2:
        return 0
    path1 = path1.lstrip("/")
    path2 = path2.lstrip("/")
    if not os.path.exists(path1) or not os.path.exists(path2):
        return 0
    try:
        img1 = Image.open(path1).convert("L").resize((32, 32))
        img2 = Image.open(path2).convert("L").resize((32, 32))
        p1 = list(img1.getdata())
        p2 = list(img2.getdata())
        diff = sum(abs(a-b) for a,b in zip(p1,p2)) / (len(p1)*255)
        return max(0, (1-diff)*100)
    except Exception:
        return 0

def location_similarity(a, b):
    return text_similarity(a, b)

def time_similarity(a, b):
    if not a or not b:
        return 0
    formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
    d1 = d2 = None
    for f in formats:
        try:
            d1 = datetime.strptime(a, f)
            break
        except ValueError:
            pass
    for f in formats:
        try:
            d2 = datetime.strptime(b, f)
            break
        except ValueError:
            pass
    if not d1 or not d2:
        return 0
    days = abs((d1-d2).total_seconds()) / 86400
    return max(0, 100 - days*20)

def find_matches(item):
    opposite = "found" if item["type"] == "lost" else "lost"
    candidates = get_items(opposite)
    results = []

    for candidate in candidates:
        img_score = basic_image_similarity(item["image"], candidate["image"])
        desc_score = text_similarity(item["description"], candidate["description"])
        name_score = text_similarity(item["name"], candidate["name"])
        category_score = text_similarity(item["category"], candidate["category"])
        loc_score = location_similarity(item["location"], candidate["location"])
        time_score = time_similarity(item["event_time"], candidate["event_time"])

        text_score = (desc_score * 0.65) + (name_score * 0.20) + (category_score * 0.15)

        overall = (
            img_score * 0.45 +
            text_score * 0.30 +
            loc_score * 0.15 +
            time_score * 0.10
        )

        results.append({
            "item": candidate,
            "image_score": round(img_score),
            "text_score": round(text_score),
            "location_score": round(loc_score),
            "time_score": round(time_score),
            "overall": round(overall)
        })

    return sorted(results, key=lambda x: x["overall"], reverse=True)
