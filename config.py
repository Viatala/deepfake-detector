import os

# Admin credentials
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "Viatala2026")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "deepfake-secret-key-change-me")

# Hugging Face API
HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/dima806/deepfake_vs_real_image_detection"

# App settings
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# Site status
SITE_ENABLED = True
