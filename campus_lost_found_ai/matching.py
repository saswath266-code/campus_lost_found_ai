"""Evidence-based Gemini multimodal matching for CampusFind AI.

Gemini is asked to compare the two report photos and report its observations in
a constrained JSON shape. The displayed confidence is calculated from that
visual evidence plus transparent, deterministic report context; it is a triage
aid for the office, never proof of ownership.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import mimetypes
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

from database import get_items, get_match_review, save_match_review

try:  # Allows a helpful runtime message before dependencies are installed.
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - exercised on a new teammate machine
    genai = None
    types = None

load_dotenv()

LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
STOP_WORDS = {
    "a", "an", "and", "at", "for", "from", "in", "is", "it", "of", "on", "or",
    "the", "to", "with", "this", "that", "was", "were", "my", "found", "lost",
}

ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "visual_similarity": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Visual similarity based only on the supplied photos.",
        },
        "category_compatibility": {
            "type": "string",
            "enum": ["compatible", "unclear", "incompatible"],
        },
        "location_compatibility": {
            "type": "string",
            "enum": ["compatible", "unclear", "incompatible"],
        },
        "time_compatibility": {
            "type": "string",
            "enum": ["compatible", "unclear", "incompatible"],
        },
        "match_likelihood": {
            "type": "string",
            "enum": ["strong_lead", "possible_lead", "weak_lead", "inconclusive"],
        },
        "visual_evidence": {"type": "array", "items": {"type": "string"}},
        "description_evidence": {"type": "array", "items": {"type": "string"}},
        "distinctive_features": {"type": "array", "items": {"type": "string"}},
        "missing_evidence": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": [
        "visual_similarity",
        "category_compatibility",
        "location_compatibility",
        "time_compatibility",
        "match_likelihood",
        "visual_evidence",
        "description_evidence",
        "distinctive_features",
        "missing_evidence",
        "summary",
    ],
    "additionalProperties": False,
}


class MatchingError(RuntimeError):
    """Base class for safe matching errors."""


class GeminiUnavailable(MatchingError):
    """Gemini cannot be used for this comparison."""


class MalformedGeminiResponse(MatchingError):
    """Gemini returned content that cannot safely be shown as evidence."""


class ImageEvidenceError(MatchingError):
    """A stored image is missing, too large, unsafe, or unreadable."""


def _configured_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    if genai is None:
        return None
    return genai.Client(api_key=api_key)


def ai_status() -> dict[str, Any]:
    """Return public-safe AI availability without exposing configuration details."""

    enabled = bool(os.getenv("GEMINI_API_KEY", "").strip()) and genai is not None
    return {
        "enabled": enabled,
        "model": GEMINI_MODEL,
        "provider": "Google Gemini API",
        "message": "Gemini visual evidence is ready." if enabled else "Gemini is not configured; context screening remains available.",
    }


def _bounded_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MalformedGeminiResponse("Gemini did not provide a numeric visual assessment.")
    return max(0, min(100, round(value)))


def _short_text_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise MalformedGeminiResponse(f"Gemini returned an invalid {field_name} field.")
    clean: list[str] = []
    for entry in value[:5]:
        if not isinstance(entry, str):
            continue
        text = " ".join(entry.split()).strip()
        if text:
            clean.append(text[:280])
    return clean


def _normalise_assessment(payload: Any) -> dict[str, Any]:
    """Validate all model output before it is stored or rendered."""

    if not isinstance(payload, dict):
        raise MalformedGeminiResponse("Gemini did not return a JSON object.")

    allowed = {
        "category_compatibility": {"compatible", "unclear", "incompatible"},
        "location_compatibility": {"compatible", "unclear", "incompatible"},
        "time_compatibility": {"compatible", "unclear", "incompatible"},
        "match_likelihood": {"strong_lead", "possible_lead", "weak_lead", "inconclusive"},
    }
    normalised: dict[str, Any] = {"visual_similarity": _bounded_int(payload.get("visual_similarity"))}
    for field, values in allowed.items():
        value = payload.get(field)
        if value not in values:
            raise MalformedGeminiResponse(f"Gemini returned an invalid {field} field.")
        normalised[field] = value

    for field in ("visual_evidence", "description_evidence", "distinctive_features", "missing_evidence"):
        normalised[field] = _short_text_list(payload.get(field), field)

    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise MalformedGeminiResponse("Gemini did not provide a usable evidence summary.")
    normalised["summary"] = " ".join(summary.split())[:500]
    return normalised


def _response_to_payload(response: Any) -> dict[str, Any]:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed

    raw_text = getattr(response, "text", "")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise MalformedGeminiResponse("Gemini returned no JSON evidence.")
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE)
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise MalformedGeminiResponse("Gemini returned malformed JSON evidence.") from exc


def _image_mime_and_bytes(data: bytes, hint: str = "") -> tuple[bytes, str]:
    if not data:
        raise ImageEvidenceError("Image data is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageEvidenceError("Image is too large for visual comparison.")
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageEvidenceError("Stored image is not a readable supported image.") from exc

    format_mimes = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    mime_type = format_mimes.get(image_format) or mimetypes.guess_type(hint)[0]
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ImageEvidenceError("Stored image has an unsupported format.")
    return data, mime_type


def _local_image_path(image_reference: str) -> Path | None:
    if not image_reference.startswith("/static/uploads/"):
        return None
    filename = Path(urlparse(image_reference).path).name
    if not filename or filename != Path(filename).name:
        raise ImageEvidenceError("Unsafe local image path.")
    candidate = (BASE_DIR / "static" / "uploads" / filename).resolve()
    upload_dir = (BASE_DIR / "static" / "uploads").resolve()
    if candidate.parent != upload_dir:
        raise ImageEvidenceError("Unsafe local image path.")
    return candidate


def _remote_image_allowed(image_reference: str) -> bool:
    parsed = urlparse(image_reference)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    configured = os.getenv("CLOUDINARY_ALLOWED_HOSTS", "res.cloudinary.com")
    allowed_hosts = {host.strip().lower() for host in configured.split(",") if host.strip()}
    return parsed.hostname.lower() in allowed_hosts


def _read_image_bytes(image_reference: str) -> tuple[bytes, str]:
    """Read only our local uploads or explicit trusted image-host domains."""

    if not image_reference:
        raise ImageEvidenceError("A photo was not supplied for this report.")

    local_path = _local_image_path(image_reference)
    if local_path is not None:
        if not local_path.is_file():
            raise ImageEvidenceError("The stored photo is no longer available.")
        return _image_mime_and_bytes(local_path.read_bytes(), str(local_path))

    if not _remote_image_allowed(image_reference):
        raise ImageEvidenceError("The stored image host is not approved for analysis.")

    try:
        request = Request(image_reference, headers={"User-Agent": "CampusFindAI/1.0"})
        with urlopen(request, timeout=12) as response:
            advertised_size = response.headers.get("Content-Length")
            if advertised_size and int(advertised_size) > MAX_IMAGE_BYTES:
                raise ImageEvidenceError("Cloud image is too large for visual comparison.")
            payload = response.read(MAX_IMAGE_BYTES + 1)
    except ImageEvidenceError:
        raise
    except Exception as exc:
        raise ImageEvidenceError("The stored cloud image could not be read.") from exc
    return _image_mime_and_bytes(payload, image_reference)


def _tokens(text: Any) -> set[str]:
    words = re.findall(r"[a-z0-9]{2,}", str(text or "").lower())
    return {word for word in words if word not in STOP_WORDS}


def _token_similarity(left: Any, right: Any) -> tuple[float, list[str]]:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0, []
    shared = sorted(left_tokens & right_tokens)
    return (len(shared) / len(left_tokens | right_tokens)) * 100.0, shared[:7]


def _text_similarity(left: Any, right: Any) -> float:
    left_clean = " ".join(str(left or "").lower().split())
    right_clean = " ".join(str(right or "").lower().split())
    if not left_clean or not right_clean:
        return 0.0
    jaccard, _ = _token_similarity(left_clean, right_clean)
    sequence = SequenceMatcher(None, left_clean, right_clean).ratio() * 100.0
    return round((jaccard * 0.65) + (sequence * 0.35), 1)


def _parse_event_time(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    for pattern in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, pattern)
        except ValueError:
            pass
    return None


def _time_similarity(left: Any, right: Any) -> tuple[float, str]:
    first, second = _parse_event_time(left), _parse_event_time(right)
    if not first or not second:
        return 0.0, "One or both report times could not be compared."
    hours_apart = abs((first - second).total_seconds()) / 3600
    # This is a transparent proximity signal, not a claim about custody history.
    score = max(0.0, 100.0 * math.exp(-hours_apart / (24 * 10)))
    if hours_apart < 24:
        detail = "Report times are within one day."
    elif hours_apart < 24 * 7:
        detail = f"Report times are {round(hours_apart / 24)} days apart."
    else:
        detail = f"Report times are about {round(hours_apart / 24)} days apart."
    return round(score, 1), detail


def _item_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(field) or "") for field in ("name", "category", "description")
    )


def _context_signals(item: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    category_score, category_terms = _token_similarity(item.get("category"), candidate.get("category"))
    if str(item.get("category") or "").strip().lower() == str(candidate.get("category") or "").strip().lower() and item.get("category"):
        category_score = 100.0
        category_detail = f"Same category: {item['category']}."
    elif category_terms:
        category_detail = f"Related category terms: {', '.join(category_terms)}."
    else:
        category_detail = "Categories do not provide a clear connection."

    description_score = _text_similarity(_item_text(item), _item_text(candidate))
    _, shared_terms = _token_similarity(_item_text(item), _item_text(candidate))
    description_detail = (
        f"Shared report terms: {', '.join(shared_terms)}."
        if shared_terms
        else "No distinctive report terms overlap."
    )
    location_score, location_terms = _token_similarity(item.get("location"), candidate.get("location"))
    if str(item.get("location") or "").strip().lower() == str(candidate.get("location") or "").strip().lower() and item.get("location"):
        location_score = 100.0
        location_detail = f"Same reported location: {item['location']}."
    elif location_terms:
        location_detail = f"Related location terms: {', '.join(location_terms)}."
    else:
        location_detail = "Locations do not clearly overlap."
    time_score, time_detail = _time_similarity(item.get("event_time"), candidate.get("event_time"))

    return {
        "category_score": round(category_score),
        "description_score": round(description_score),
        "location_score": round(location_score),
        "time_score": round(time_score),
        "details": [category_detail, description_detail, location_detail, time_detail],
    }


def _context_screening_score(signals: dict[str, Any]) -> int:
    return round(
        (signals["category_score"] * 0.30)
        + (signals["description_score"] * 0.35)
        + (signals["location_score"] * 0.20)
        + (signals["time_score"] * 0.15)
    )


def _fingerprint(item: dict[str, Any], candidate: dict[str, Any]) -> str:
    fields = ("id", "type", "name", "category", "description", "location", "event_time", "image", "status")
    pair = [{field: item.get(field) for field in fields}, {field: candidate.get(field) for field in fields}]
    return hashlib.sha256(json.dumps(pair, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _lost_and_found_ids(item: dict[str, Any], candidate: dict[str, Any]) -> tuple[int, int]:
    if item.get("type") == "lost":
        return int(item["id"]), int(candidate["id"])
    return int(candidate["id"]), int(item["id"])


def _safe_report_data(item: dict[str, Any]) -> dict[str, str]:
    return {
        "report_type": str(item.get("type") or ""),
        "name": str(item.get("name") or "")[:255],
        "category": str(item.get("category") or "")[:100],
        "description": str(item.get("description") or "")[:1000],
        "location": str(item.get("location") or "")[:255],
        "event_time": str(item.get("event_time") or "")[:100],
    }


def _call_gemini(item: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    client = _configured_client()
    if client is None or types is None:
        raise GeminiUnavailable("Gemini is not configured.")

    first_image, first_mime = _read_image_bytes(str(item.get("image") or ""))
    second_image, second_mime = _read_image_bytes(str(candidate.get("image") or ""))
    prompt = (
        "You support a campus lost-and-found office. Compare Report A and Report B and their photos. "
        "Assess object/category compatibility; visible appearance, color, shape, brand or model when actually visible; "
        "and distinctive physical characteristics such as stickers, cases, scratches, damage, or missing parts. "
        "Compare the supplied report descriptions and treat location and time only as supporting context. "
        "Do not infer ownership, identity, or facts not visible/supplied. Never say the objects are definitely the same. "
        "When photos are unclear or evidence conflicts, state that plainly and lower visual_similarity. "
        f"Report A: {json.dumps(_safe_report_data(item), ensure_ascii=False)}\n"
        f"Report B: {json.dumps(_safe_report_data(candidate), ensure_ascii=False)}\n"
        "The first supplied image is Report A and the second is Report B."
    )
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(data=first_image, mime_type=first_mime),
                types.Part.from_bytes(data=second_image, mime_type=second_mime),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=ASSESSMENT_SCHEMA,
                temperature=0.1,
            ),
        )
    except Exception as exc:
        LOGGER.exception("Gemini API call failed")
        raise GeminiUnavailable("Gemini could not complete this comparison.") from exc
    return _normalise_assessment(_response_to_payload(response))


def _ai_confidence(assessment: dict[str, Any], signals: dict[str, Any]) -> int:
    """Calculate the visible confidence shown in the UI from named components."""

    return round(
        (assessment["visual_similarity"] * 0.40)
        + (signals["description_score"] * 0.25)
        + (signals["category_score"] * 0.15)
        + (signals["location_score"] * 0.10)
        + (signals["time_score"] * 0.10)
    )


def _result_from_assessment(
    candidate: dict[str, Any],
    signals: dict[str, Any],
    assessment: dict[str, Any],
    review: dict[str, Any] | None,
    *,
    cached: bool,
) -> dict[str, Any]:
    confidence = _ai_confidence(assessment, signals)
    return {
        "item": candidate,
        "analysis_mode": "gemini",
        "analysis_message": "Saved Gemini evidence reused; no new API call was made." if cached else "Gemini reviewed the two supplied photos and report details.",
        "evidence_confidence": confidence,
        "screening_score": _context_screening_score(signals),
        "visual_score": assessment["visual_similarity"],
        "scores": signals,
        "assessment": assessment,
        "review_id": review.get("id") if review else None,
        "decision": review.get("decision", "potential") if review else "potential",
        "match_likelihood": assessment["match_likelihood"],
    }


def _manual_result(candidate: dict[str, Any], signals: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "item": candidate,
        "analysis_mode": "manual",
        "analysis_message": message,
        "evidence_confidence": None,
        "screening_score": _context_screening_score(signals),
        "visual_score": None,
        "scores": signals,
        "assessment": None,
        "review_id": None,
        "decision": "potential",
        "match_likelihood": "inconclusive",
    }


def _max_candidates() -> int:
    try:
        return max(1, min(10, int(os.getenv("MAX_GEMINI_CANDIDATES", "5"))))
    except ValueError:
        return 5


def find_matches(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Return opposite-type reports with cached Gemini evidence when available.

    Gemini requests are intentionally limited to the top context-supported pairs
    that have two usable image references. Other records remain visible for a
    human to screen; no made-up AI score is shown for them.
    """

    item_type = item.get("type")
    if item_type not in {"lost", "found"}:
        raise ValueError("The report has an invalid item type.")

    opposite = "found" if item_type == "lost" else "lost"
    candidates = [candidate for candidate in get_items(opposite) if candidate.get("status") not in {"returned", "rejected"}]
    ranked: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for candidate in candidates:
        signals = _context_signals(item, candidate)
        # Image-bearing reports are preferable for expensive visual review, but
        # context remains the primary pre-screening signal.
        image_bonus = 15 if item.get("image") and candidate.get("image") else 0
        ranked.append((_context_screening_score(signals) + image_bonus, candidate, signals))
    ranked.sort(key=lambda entry: entry[0], reverse=True)

    results: list[dict[str, Any]] = []
    requests_used = 0
    gemini_ready = _configured_client() is not None and types is not None
    for _, candidate, signals in ranked:
        fingerprint = _fingerprint(item, candidate)
        lost_id, found_id = _lost_and_found_ids(item, candidate)
        review = get_match_review(lost_id, found_id)
        if review and review.get("input_fingerprint") == fingerprint and review.get("assessment"):
            results.append(_result_from_assessment(candidate, signals, review["assessment"], review, cached=True))
            continue

        has_two_images = bool(item.get("image") and candidate.get("image"))
        if gemini_ready and has_two_images and requests_used < _max_candidates():
            requests_used += 1
            try:
                assessment = _call_gemini(item, candidate)
                confidence = _ai_confidence(assessment, signals)
                review_id = save_match_review(lost_id, found_id, fingerprint, assessment, confidence)
                saved_review = {
                    "id": review_id,
                    "decision": review.get("decision", "potential") if review else "potential",
                }
                results.append(_result_from_assessment(candidate, signals, assessment, saved_review, cached=False))
                continue
            except ImageEvidenceError:
                message = "Photo evidence is missing or unreadable, so this pair needs manual review."
            except MalformedGeminiResponse:
                LOGGER.warning("Discarded malformed Gemini match response for items %s and %s", item.get("id"), candidate.get("id"))
                message = "Gemini returned unusable evidence for this pair; use the report details for manual review."
            except GeminiUnavailable:
                LOGGER.warning("Gemini comparison unavailable for items %s and %s", item.get("id"), candidate.get("id"))
                message = "Gemini could not complete this pair right now; use the report details for manual review."
        elif not gemini_ready:
            message = "Gemini is not configured, so this is context screening only, not AI visual evidence."
        elif not has_two_images:
            message = "Both reports need a photo before Gemini can compare visible evidence."
        else:
            message = "Gemini review is limited to the most context-compatible photo pairs; this report remains available for manual review."
        results.append(_manual_result(candidate, signals, message))

    return results
