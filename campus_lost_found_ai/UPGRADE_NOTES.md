# CampusFind AI optimization notes

- Kept the Flask + MySQL + Gemini architecture; removed obsolete SQLite, OpenCLIP, and local-model assumptions from configuration and documentation.
- Replaced embedding-only matching with Gemini multimodal, schema-constrained pair reviews that explain visible and report-context evidence.
- Added transparent context screening when Gemini, a photo, or an API response is unavailable. These results are explicitly not presented as AI visual evidence.
- Added `match_reviews` for cached evidence and staff pair decisions. The original `items` schema remains intact, with safe default migrations.
- Added secure admin login, CSRF protection for every state change, POST-only office actions, upload content validation, and Cloudinary-aware production storage.
- Updated the responsive UI, Render configuration, setup guide, and test coverage for a repeatable demo.
