import json
import logging
from datetime import datetime, timezone

from core.config import Settings

_RESERVED_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        parts = [
            timestamp,
            f"level={record.levelname}",
            f"logger={record.name}",
            f"message={json.dumps(record.getMessage())}",
        ]

        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_ATTRS or key.startswith("_"):
                continue
            parts.append(f"{key}={json.dumps(value, default=str)}")

        if record.exc_info:
            parts.append(f"exception={json.dumps(self.formatException(record.exc_info))}")

        return " ".join(parts)


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if settings.log_format == "json" else ConsoleFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.setLevel(level)
        logger.propagate = False

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = [handler]
    access_logger.setLevel(level)
    access_logger.propagate = False
