# Upgrade notes from the supplied project

The original prototype was retained as the base. The main changes are:

1. `matching.py`: replaced the 32x32 grayscale pixel comparison with OpenCLIP embeddings for images and text.
2. `database.py`: supports SQLite locally and PostgreSQL in production through `DATABASE_URL`.
3. `storage.py`: supports local uploads and Cloudinary in production.
4. `app.py`: adds production-safe configuration, admin login, health endpoint, and upload validation.
5. Templates: improved public workflow and match explanation.
6. `Procfile` and `render.yaml`: added production deployment configuration.
7. `.env.example`: lists credentials and service settings that must be supplied by the deployer.
