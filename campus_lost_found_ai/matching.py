"""AI-powered multimodal matching for HACM121.

Primary AI model: OpenCLIP (ViT-B/32 by default), executed locally.
It creates embeddings for both images and descriptions. Matching also uses
location and time context. If OpenCLIP is unavailable, the app can fall back
to lightweight comparison when AI_FALLBACK=1; keep fallback disabled for the
hackathon demonstration if you want to require genuine AI matching.
"""
import os
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from difflib import SequenceMatcher
from urllib.request import urlopen
from io import BytesIO

import numpy as np
from database import get_items

BASE_DIR = Path(__file__).resolve().parent
AI_FALLBACK = os.getenv("AI_FALLBACK", "0") == "1"
MODEL_NAME = os.getenv("CLIP_MODEL", "ViT-B-32")
MODEL_PRETRAINED = os.getenv("CLIP_PRETRAINED", "laion2b_s34b_b79k")
AI_DEVICE = os.getenv("AI_DEVICE", "cpu")

_clip = None
_clip_preprocess = None
_clip_tokenizer = None
_clip_load_error = None


def _load_clip():
    global _clip, _clip_preprocess, _clip_tokenizer, _clip_load_error
    if _clip is not None:
        return _clip, _clip_preprocess, _clip_tokenizer
    if _clip_load_error is not None:
        raise RuntimeError(_clip_load_error)
    try:
        import open_clip
        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=MODEL_PRETRAINED, device=AI_DEVICE
        )
        tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        model.eval()
        _clip, _clip_preprocess, _clip_tokenizer = model, preprocess, tokenizer
        return _clip, _clip_preprocess, _clip_tokenizer
    except Exception as exc:
        _clip_load_error = (
            f"OpenCLIP could not be loaded: {exc}. "
            "Install requirements and allow the pretrained weights to download, "
            "or set AI_FALLBACK=1 for development only."
        )
        raise RuntimeError(_clip_load_error) from exc


def ai_status():
    if _clip is not None:
        return {"enabled": True, "model": f"{MODEL_NAME}/{MODEL_PRETRAINED}", "fallback": False}
    try:
        _load_clip()
        return {"enabled": True, "model": f"{MODEL_NAME}/{MODEL_PRETRAINED}", "fallback": False}
    except Exception as exc:
        return {"enabled": False, "model": None, "fallback": AI_FALLBACK, "error": str(exc)}


def normalize(text):
    return re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).strip()


def basic_text_similarity(a, b):
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio() * 100.0


def _local_path(url):
    if not url or url.startswith("http://") or url.startswith("https://"):
        return None
    clean = url.lstrip("/")
    return BASE_DIR / clean


def clip_image_embedding(image_url):
    from PIL import Image
    import torch
    path = _local_path(image_url)
    model, preprocess, _ = _load_clip()
    if path is not None:
        if not path.exists():
            return None
        source = Image.open(path).convert("RGB")
    else:
        # Production images may live on Cloudinary or another HTTPS object store.
        with urlopen(image_url, timeout=15) as response:
            source = Image.open(BytesIO(response.read())).convert("RGB")
    image = preprocess(source).unsqueeze(0).to(AI_DEVICE)
    with torch.no_grad():
        emb = model.encode_image(image)
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb[0].detach().cpu().numpy()


def clip_text_embedding(text):
    import torch
    if not text:
        return None
    model, _, tokenizer = _load_clip()
    tokens = tokenizer([text]).to(AI_DEVICE)
    with torch.no_grad():
        emb = model.encode_text(tokens)
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb[0].detach().cpu().numpy()


def cosine_percent(a, b):
    if a is None or b is None:
        return 0.0
    value = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
    return max(0.0, min(100.0, ((value + 1.0) / 2.0) * 100.0))


@lru_cache(maxsize=512)
def cached_image_embedding(image_url):
    return clip_image_embedding(image_url)


@lru_cache(maxsize=1024)
def cached_text_embedding(text):
    return clip_text_embedding(text)


def image_similarity(a, b):
    if not a or not b:
        return 0.0
    try:
        return cosine_percent(cached_image_embedding(a), cached_image_embedding(b))
    except Exception:
        if AI_FALLBACK:
            return basic_image_similarity(a, b)
        raise


def text_similarity(a, b):
    if not a or not b:
        return 0.0
    try:
        return cosine_percent(cached_text_embedding(a), cached_text_embedding(b))
    except Exception:
        if AI_FALLBACK:
            return basic_text_similarity(a, b)
        raise


def basic_image_similarity(path1, path2):
    from PIL import Image
    if not path1 or not path2:
        return 0.0
    p1, p2 = _local_path(path1), _local_path(path2)
    if p1 is None or p2 is None or not p1.exists() or not p2.exists():
        return 0.0
    try:
        img1 = Image.open(p1).convert("L").resize((32, 32))
        img2 = Image.open(p2).convert("L").resize((32, 32))
        a = np.asarray(img1, dtype=np.float32)
        b = np.asarray(img2, dtype=np.float32)
        diff = np.mean(np.abs(a - b)) / 255.0
        return max(0.0, (1.0 - diff) * 100.0)
    except Exception:
        return 0.0


def location_similarity(a, b):
    return basic_text_similarity(a, b)


def time_similarity(a, b):
    if not a or not b:
        return 0.0
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
        return 0.0
    days = abs((d1 - d2).total_seconds()) / 86400.0
    return max(0.0, 100.0 - days * 20.0)


def combined_text(item):
    return " | ".join(filter(None, [item["name"], item["category"], item["description"]]))


def find_matches(item):
    opposite = "found" if item["type"] == "lost" else "lost"
    candidates = get_items(opposite)
    results = []

    for candidate in candidates:
        img_score = image_similarity(item["image"], candidate["image"])
        text_score = text_similarity(combined_text(item), combined_text(candidate))
        loc_score = location_similarity(item["location"], candidate["location"])
        time_score = time_similarity(item["event_time"], candidate["event_time"])

        # Image is deliberately the strongest signal for HACM121.
        overall = (
            img_score * 0.55 +
            text_score * 0.25 +
            loc_score * 0.10 +
            time_score * 0.10
        )

        results.append({
            "item": candidate,
            "image_score": round(img_score),
            "text_score": round(text_score),
            "location_score": round(loc_score),
            "time_score": round(time_score),
            "overall": round(overall),
        })

    return sorted(results, key=lambda x: x["overall"], reverse=True)
