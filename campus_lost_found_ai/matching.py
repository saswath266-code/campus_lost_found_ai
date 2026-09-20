"""AI-powered multimodal matching for HACM121.

Uses Google's Gemini Embedding 2 API for:
- Image embeddings
- Text embeddings
- Image-to-image similarity
- Text-to-text similarity

Location and time are additional contextual signals.
"""

import os
import re
import mimetypes
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from difflib import SequenceMatcher
from urllib.request import urlopen
from io import BytesIO

import numpy as np
from PIL import Image
from database import get_items

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

GEMINI_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSION = 768

AI_FALLBACK = os.getenv("AI_FALLBACK", "0") == "1"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None


# ---------------------------------------------------------
# AI STATUS
# ---------------------------------------------------------

def ai_status():
    """Return current Gemini AI status."""

    if client is None:
        return {
            "enabled": False,
            "model": GEMINI_MODEL,
            "provider": "Google Gemini API",
            "fallback": AI_FALLBACK,
            "error": "GEMINI_API_KEY is not configured."
        }

    return {
        "enabled": True,
        "model": GEMINI_MODEL,
        "provider": "Google Gemini API",
        "fallback": AI_FALLBACK
    }


# ---------------------------------------------------------
# TEXT HELPERS
# ---------------------------------------------------------

def normalize(text):
    return re.sub(
        r"[^a-z0-9 ]",
        " ",
        (text or "").lower()
    ).strip()


def basic_text_similarity(a, b):
    """Fallback text similarity."""

    a = normalize(a)
    b = normalize(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio() * 100.0


# ---------------------------------------------------------
# IMAGE HELPERS
# ---------------------------------------------------------

def _local_path(url):
    """Convert a local image URL/path into a filesystem path."""

    if not url:
        return None

    if url.startswith("http://") or url.startswith("https://"):
        return None

    clean = url.lstrip("/")

    return BASE_DIR / clean


def _read_image_bytes(image_url):
    """Read image bytes from local storage or HTTPS storage."""

    local_path = _local_path(image_url)

    if local_path is not None:

        if not local_path.exists():
            return None, None

        with open(local_path, "rb") as file:
            data = file.read()

        mime_type = mimetypes.guess_type(str(local_path))[0]

        if not mime_type:
            mime_type = "image/jpeg"

        return data, mime_type

    # Cloudinary / HTTPS image
    with urlopen(image_url, timeout=15) as response:
        data = response.read()

        mime_type = response.headers.get(
            "Content-Type",
            "image/jpeg"
        )

    return data, mime_type


# ---------------------------------------------------------
# GEMINI EMBEDDINGS
# ---------------------------------------------------------

def _check_client():

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Add GEMINI_API_KEY to your .env file."
        )


@lru_cache(maxsize=1024)
def gemini_text_embedding(text):
    """Generate a Gemini embedding for text."""

    if not text:
        return None

    _check_client()

    result = client.models.embed_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                parts=[
                    types.Part.from_text(
                        text=text
                    )
                ]
            )
        ],
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        )
    )

    return np.array(
        result.embeddings[0].values,
        dtype=np.float32
    )


@lru_cache(maxsize=512)
def gemini_image_embedding(image_url):
    """Generate a Gemini embedding for an image."""

    if not image_url:
        return None

    _check_client()

    image_bytes, mime_type = _read_image_bytes(image_url)

    if image_bytes is None:
        return None

    result = client.models.embed_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                parts=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type
                    )
                ]
            )
        ],
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        )
    )

    return np.array(
        result.embeddings[0].values,
        dtype=np.float32
    )


# ---------------------------------------------------------
# COSINE SIMILARITY
# ---------------------------------------------------------

def cosine_percent(a, b):

    if a is None or b is None:
        return 0.0

    denominator = (
        np.linalg.norm(a) *
        np.linalg.norm(b)
    )

    if denominator == 0:
        return 0.0

    similarity = float(
        np.dot(a, b) / denominator
    )

    # Convert -1..1 to 0..100
    score = ((similarity + 1.0) / 2.0) * 100.0

    return max(
        0.0,
        min(100.0, score)
    )


# ---------------------------------------------------------
# IMAGE SIMILARITY
# ---------------------------------------------------------

def image_similarity(image1, image2):

    if not image1 or not image2:
        return 0.0

    try:

        embedding1 = gemini_image_embedding(image1)
        embedding2 = gemini_image_embedding(image2)

        return cosine_percent(
            embedding1,
            embedding2
        )

    except Exception:

        if AI_FALLBACK:
            return basic_image_similarity(
                image1,
                image2
            )

        raise


# ---------------------------------------------------------
# TEXT SIMILARITY
# ---------------------------------------------------------

def text_similarity(text1, text2):

    if not text1 or not text2:
        return 0.0

    try:

        embedding1 = gemini_text_embedding(text1)
        embedding2 = gemini_text_embedding(text2)

        return cosine_percent(
            embedding1,
            embedding2
        )

    except Exception:

        if AI_FALLBACK:
            return basic_text_similarity(
                text1,
                text2
            )

        raise


# ---------------------------------------------------------
# FALLBACK IMAGE SIMILARITY
# ---------------------------------------------------------

def basic_image_similarity(path1, path2):

    if not path1 or not path2:
        return 0.0

    p1 = _local_path(path1)
    p2 = _local_path(path2)

    if (
        p1 is None
        or p2 is None
        or not p1.exists()
        or not p2.exists()
    ):
        return 0.0

    try:

        img1 = (
            Image.open(p1)
            .convert("L")
            .resize((32, 32))
        )

        img2 = (
            Image.open(p2)
            .convert("L")
            .resize((32, 32))
        )

        a = np.asarray(
            img1,
            dtype=np.float32
        )

        b = np.asarray(
            img2,
            dtype=np.float32
        )

        diff = (
            np.mean(np.abs(a - b))
            / 255.0
        )

        return max(
            0.0,
            (1.0 - diff) * 100.0
        )

    except Exception:

        return 0.0


# ---------------------------------------------------------
# LOCATION SIMILARITY
# ---------------------------------------------------------

def location_similarity(a, b):

    return basic_text_similarity(
        a,
        b
    )


# ---------------------------------------------------------
# TIME SIMILARITY
# ---------------------------------------------------------

def time_similarity(a, b):

    if not a or not b:
        return 0.0

    formats = [
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d"
    ]

    d1 = None
    d2 = None

    for fmt in formats:

        try:
            d1 = datetime.strptime(
                a,
                fmt
            )
            break

        except ValueError:
            pass

    for fmt in formats:

        try:
            d2 = datetime.strptime(
                b,
                fmt
            )
            break

        except ValueError:
            pass

    if not d1 or not d2:
        return 0.0

    days = abs(
        (d1 - d2).total_seconds()
    ) / 86400.0

    return max(
        0.0,
        100.0 - days * 20.0
    )


# ---------------------------------------------------------
# COMBINED TEXT
# ---------------------------------------------------------

def combined_text(item):

    return " | ".join(
        filter(
            None,
            [
                item["name"],
                item["category"],
                item["description"]
            ]
        )
    )


# ---------------------------------------------------------
# FIND MATCHES
# ---------------------------------------------------------

def find_matches(item):

    opposite = (
        "found"
        if item["type"] == "lost"
        else "lost"
    )

    candidates = get_items(opposite)

    results = []

    for candidate in candidates:

        img_score = image_similarity(
            item["image"],
            candidate["image"]
        )

        text_score = text_similarity(
            combined_text(item),
            combined_text(candidate)
        )

        loc_score = location_similarity(
            item["location"],
            candidate["location"]
        )

        time_score = time_similarity(
            item["event_time"],
            candidate["event_time"]
        )

        # HACM121 matching weights
        overall = (
            img_score * 0.55
            + text_score * 0.25
            + loc_score * 0.10
            + time_score * 0.10
        )

        results.append({

            "item": candidate,

            "image_score": round(
                img_score
            ),

            "text_score": round(
                text_score
            ),

            "location_score": round(
                loc_score
            ),

            "time_score": round(
                time_score
            ),

            "overall": round(
                overall
            )
        })

    return sorted(
        results,
        key=lambda x: x["overall"],
        reverse=True
    )