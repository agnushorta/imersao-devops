import logging
from logging.config import dictConfig
import os
from contextvars import ContextVar
from typing import Optional

# Define a context variable for the request ID with a default value of None.
# This makes the request ID available throughout the async context of a request.
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

class RequestIdFilter(logging.Filter):
    """A logging filter that injects the request_id from a context variable into the log record."""
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True

class JsonFormatter(logging.Formatter):
    """
    Custom formatter to output logs in JSON format.
    """
    def format(self, record):
        # Create a dictionary with the log record's attributes
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
            # Add request_id if it exists on the record
            "request_id": getattr(record, "request_id", None),
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }
        # Filter out null values for cleaner logs
        log_record_filtered = {k: v for k, v in log_record.items() if v is not None}
        return str(log_record_filtered).replace("'", '"') # Simple JSON conversion

# Read log level from environment variable, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    log_level = "INFO"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id_filter": {
            "()": RequestIdFilter,
        },
    },
    "formatters": {
        "json": {
            "()": JsonFormatter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
            # Attach the filter to the handler
            "filters": ["request_id_filter"],
        },
    },
    "root": {
        "level": log_level,
        "handlers": ["console"],
    },
}

def setup_logging():
    dictConfig(LOGGING_CONFIG)
