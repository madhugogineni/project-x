import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/test_projectx",
)
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-which-is-definitely-long-enough",
)
