import unittest
from unittest.mock import patch

import matching


LOST = {
    "id": 1,
    "type": "lost",
    "name": "Black Samsung phone",
    "category": "Mobile Phone",
    "description": "Black Samsung with a cracked screen and blue case",
    "location": "Main Library",
    "event_time": "2026-09-23T10:00",
    "image": "/static/uploads/lost.jpg",
    "status": "searching",
}
FOUND = {
    "id": 2,
    "type": "found",
    "name": "Samsung handset",
    "category": "Mobile Phone",
    "description": "Black phone found with a blue case",
    "location": "Library entrance",
    "event_time": "2026-09-23T11:00",
    "image": "/static/uploads/found.jpg",
    "status": "searching",
}


class MatchingTests(unittest.TestCase):
    def test_missing_key_uses_labelled_context_screening(self):
        with patch.object(matching, "get_items", return_value=[FOUND]), patch.object(
            matching, "get_match_review", return_value=None
        ), patch.object(matching, "_configured_client", return_value=None):
            results = matching.find_matches(LOST)
        self.assertEqual(results[0]["analysis_mode"], "manual")
        self.assertIsNone(results[0]["evidence_confidence"])
        self.assertIn("not configured", results[0]["analysis_message"])

    def test_malformed_model_response_falls_back_without_score(self):
        with patch.object(matching, "get_items", return_value=[FOUND]), patch.object(
            matching, "get_match_review", return_value=None
        ), patch.object(matching, "_configured_client", return_value=object()), patch.object(
            matching, "types", object()
        ), patch.object(
            matching, "_call_gemini", side_effect=matching.MalformedGeminiResponse()
        ):
            results = matching.find_matches(LOST)
        self.assertEqual(results[0]["analysis_mode"], "manual")
        self.assertIn("unusable evidence", results[0]["analysis_message"])

    def test_api_failure_falls_back_without_score(self):
        with patch.object(matching, "get_items", return_value=[FOUND]), patch.object(
            matching, "get_match_review", return_value=None
        ), patch.object(matching, "_configured_client", return_value=object()), patch.object(
            matching, "types", object()
        ), patch.object(
            matching, "_call_gemini", side_effect=matching.GeminiUnavailable()
        ):
            results = matching.find_matches(LOST)
        self.assertEqual(results[0]["analysis_mode"], "manual")
        self.assertIn("could not complete", results[0]["analysis_message"])

    def test_cached_evidence_is_reused(self):
        assessment = matching._normalise_assessment(
            {
                "visual_similarity": 72,
                "category_compatibility": "compatible",
                "location_compatibility": "compatible",
                "time_compatibility": "compatible",
                "match_likelihood": "possible_lead",
                "visual_evidence": ["Both photos show a black handset."],
                "description_evidence": ["Both reports mention a blue case."],
                "distinctive_features": ["A cracked screen is visible in one photo."],
                "missing_evidence": ["Office inspection is required."],
                "summary": "The reports are a possible lead, not proof of ownership.",
            }
        )
        review = {
            "id": 9,
            "input_fingerprint": matching._fingerprint(LOST, FOUND),
            "assessment": assessment,
            "decision": "potential",
        }
        with patch.object(matching, "get_items", return_value=[FOUND]), patch.object(
            matching, "get_match_review", return_value=review
        ), patch.object(matching, "_call_gemini") as call:
            results = matching.find_matches(LOST)
        call.assert_not_called()
        self.assertEqual(results[0]["analysis_mode"], "gemini")
        self.assertEqual(results[0]["review_id"], 9)

    def test_missing_image_is_reported_as_manual_review(self):
        photo_less_found = dict(FOUND, image="")
        with patch.object(matching, "get_items", return_value=[photo_less_found]), patch.object(
            matching, "get_match_review", return_value=None
        ), patch.object(matching, "_configured_client", return_value=object()), patch.object(
            matching, "types", object()
        ):
            results = matching.find_matches(LOST)
        self.assertEqual(results[0]["analysis_mode"], "manual")
        self.assertIn("need a photo", results[0]["analysis_message"])

    def test_invalid_json_shape_is_rejected(self):
        with self.assertRaises(matching.MalformedGeminiResponse):
            matching._normalise_assessment({"visual_similarity": 80})


if __name__ == "__main__":
    unittest.main()
