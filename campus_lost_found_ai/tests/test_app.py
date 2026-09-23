import io
import re
import unittest
from unittest.mock import patch

import app as application


def csrf_token(response):
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    if not match:
        raise AssertionError("No CSRF token found in form")
    return match.group(1)


class AppRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = application.create_app(
            {"TESTING": True, "AUTO_INIT_DB": False, "DATABASE_READY": True, "SECRET_KEY": "test-secret"}
        )
        self.client = self.app.test_client()

    def test_public_templates_render(self):
        sample = {
            "id": 1, "type": "lost", "name": "Keys", "category": "Keys", "description": "Blue tag",
            "location": "Library", "event_time": "2026-09-23T10:00", "image": "", "status": "searching",
        }
        with patch.object(application, "get_items", side_effect=[[sample], []]):
            home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"CampusFind", home.data)
        self.assertEqual(self.client.get("/report/lost").status_code, 200)
        self.assertEqual(self.client.get("/admin/login").status_code, 200)

    def test_invalid_upload_does_not_create_report(self):
        page = self.client.get("/report/lost")
        token = csrf_token(page)
        with patch.object(application, "add_item") as add:
            response = self.client.post(
                "/report/lost",
                data={
                    "csrf_token": token, "name": "Keys", "category": "Keys", "description": "Blue tag",
                    "location": "Library", "event_time": "2026-09-23T10:00",
                    "image": (io.BytesIO(b"not an image"), "fake.jpg"),
                },
                content_type="multipart/form-data",
                follow_redirects=False,
            )
        self.assertEqual(response.status_code, 302)
        add.assert_not_called()

    def test_valid_report_flow_calls_storage_and_database(self):
        page = self.client.get("/report/found")
        token = csrf_token(page)
        with patch.object(application, "save_uploaded_image", return_value="/static/uploads/photo.jpg"), patch.object(
            application, "add_item", return_value=42
        ) as add:
            response = self.client.post(
                "/report/found",
                data={
                    "csrf_token": token, "name": "Keys", "category": "Keys", "description": "Blue tag",
                    "location": "Library", "event_time": "2026-09-23T10:00",
                },
                follow_redirects=False,
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/matches/42", response.headers["Location"])
        add.assert_called_once()


if __name__ == "__main__":
    unittest.main()
