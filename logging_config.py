import logging
import os
import sys
from contextvars import ContextVar
from typing import Optional

import structlog
from structlog.types import Processor

# Context variable for request ID, to be used by our middleware and processor.
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

def add_request_id(_, __, event_dict: dict[str, any]) -> dict[str, any]:
    """A structlog processor to add the request_id from a context variable."""
    if request_id := request_id_var.get():
        event_dict["request_id"] = request_id
    return event_dict

def setup_logging():
    """
    Configure structlog to format logs as JSON and integrate with standard logging.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_formatter = os.getenv("LOG_FORMATTER", "json").lower()
    
    # These processors are shared between development and production
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_request_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Determine the final renderer based on the environment variable
    if log_formatter == "console":
        final_processor = structlog.dev.ConsoleRenderer(colors=True)
    else:  # Default to JSON for production
        final_processor = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            final_processor,
        ],
        # This wrapper class is what makes standard loggers (like uvicorn's)
        # use the structlog pipeline.
        wrapper_class=structlog.stdlib.BoundLogger,
        # This factory is used to create loggers for the standard logging module.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # This ensures that all logs are eventually passed to the standard logging
        # machinery, which is configured to handle output.
        cache_logger_on_first_use=True,
    )

    # Configure the standard logging module to use a simple handler that just
    # outputs the already-formatted log messages from structlog.
    logging.basicConfig(
        level=log_level,
        stream=sys.stdout,
        format="%(message)s", # structlog has already formatted the message
    )
