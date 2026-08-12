import os


DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_cors_origins():
    configured_origins = os.getenv("CORS_ORIGINS", "")
    origins = [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
    return origins or list(DEFAULT_CORS_ORIGINS)
