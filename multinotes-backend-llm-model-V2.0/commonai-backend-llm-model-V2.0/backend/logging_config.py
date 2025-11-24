"""
Logging configuration for MultinotesAI.

This module provides:
- Structured JSON logging
- Log aggregation configuration
- Custom formatters
- Log rotation settings
"""

import os
import json
import logging
from datetime import datetime
from pythonjsonlogger import jsonlogger


# =============================================================================
# Custom JSON Formatter
# =============================================================================

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging.

    Adds standard fields:
    - timestamp
    - level
    - logger
    - message
    - request_id (if available)
    - user_id (if available)
    """

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()

        # Add level name
        log_record['level'] = record.levelname

        # Add logger name
        log_record['logger'] = record.name

        # Add source location
        log_record['source'] = f"{record.filename}:{record.lineno}"

        # Add function name
        log_record['function'] = record.funcName

        # Add process/thread info for debugging
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread

        # Extract extra fields
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id


class SimpleFormatter(logging.Formatter):
    """
    Simple formatter for development/console output.

    Format: [LEVEL] timestamp | logger | message
    """

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',      # Reset
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        formatted = (
            f"{color}[{record.levelname:8}]{reset} "
            f"{timestamp} | "
            f"{record.name:20} | "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


# =============================================================================
# Filter Classes
# =============================================================================

class HealthCheckFilter(logging.Filter):
    """Filter out health check requests from logs."""

    def filter(self, record):
        message = record.getMessage()
        if '/health/' in message or '/metrics/' in message:
            return False
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from log messages."""

    SENSITIVE_PATTERNS = [
        'password',
        'token',
        'secret',
        'api_key',
        'authorization',
        'credit_card',
        'ssn',
    ]

    def filter(self, record):
        message = record.getMessage().lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                record.msg = self._mask_sensitive(record.msg)
                break
        return True

    def _mask_sensitive(self, message):
        """Mask sensitive data in message."""
        # Simple masking - in production use more sophisticated approach
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message.lower():
                message = f"[SENSITIVE DATA MASKED: {pattern}]"
                break
        return message


# =============================================================================
# Handler Classes
# =============================================================================

class AsyncFileHandler(logging.handlers.RotatingFileHandler):
    """
    Async-safe rotating file handler.

    Uses write-through buffering for better async compatibility.
    """

    def emit(self, record):
        try:
            super().emit(record)
            self.flush()
        except Exception:
            self.handleError(record)


# =============================================================================
# Logging Configuration Dict
# =============================================================================

def get_logging_config(log_dir='/var/log/multinotesai', debug=False):
    """
    Get logging configuration dict for Django settings.

    Args:
        log_dir: Directory for log files
        debug: Whether debug mode is enabled

    Returns:
        Dict suitable for Django LOGGING setting
    """
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)

    return {
        'version': 1,
        'disable_existing_loggers': False,

        # Formatters
        'formatters': {
            'json': {
                '()': CustomJsonFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s',
            },
            'simple': {
                '()': SimpleFormatter,
            },
            'verbose': {
                'format': '[{levelname}] {asctime} {name} {module}.{funcName}:{lineno} - {message}',
                'style': '{',
            },
        },

        # Filters
        'filters': {
            'health_check': {
                '()': HealthCheckFilter,
            },
            'sensitive_data': {
                '()': SensitiveDataFilter,
            },
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },

        # Handlers
        'handlers': {
            # Console handler for development
            'console': {
                'level': 'DEBUG' if debug else 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'simple' if debug else 'json',
                'filters': ['health_check'],
            },

            # Main application log
            'app_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'app.log'),
                'maxBytes': 50 * 1024 * 1024,  # 50MB
                'backupCount': 10,
                'formatter': 'json',
                'filters': ['health_check', 'sensitive_data'],
            },

            # Error log
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'error.log'),
                'maxBytes': 50 * 1024 * 1024,  # 50MB
                'backupCount': 10,
                'formatter': 'json',
            },

            # Performance log
            'performance_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'performance.log'),
                'maxBytes': 100 * 1024 * 1024,  # 100MB
                'backupCount': 5,
                'formatter': 'json',
                'filters': ['health_check'],
            },

            # Security/audit log
            'security_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'security.log'),
                'maxBytes': 50 * 1024 * 1024,  # 50MB
                'backupCount': 30,
                'formatter': 'json',
            },

            # Celery log
            'celery_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'celery.log'),
                'maxBytes': 50 * 1024 * 1024,  # 50MB
                'backupCount': 10,
                'formatter': 'json',
            },

            # Mail admins on critical errors
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler',
                'filters': ['require_debug_false'],
                'include_html': True,
            },
        },

        # Loggers
        'loggers': {
            # Root logger
            '': {
                'handlers': ['console', 'app_file', 'error_file'],
                'level': 'INFO',
            },

            # Django loggers
            'django': {
                'handlers': ['console', 'app_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console', 'app_file', 'error_file', 'mail_admins'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['console'] if debug else [],
                'level': 'DEBUG' if debug else 'INFO',
                'propagate': False,
            },
            'django.security': {
                'handlers': ['console', 'security_file'],
                'level': 'INFO',
                'propagate': False,
            },

            # Application loggers
            'coreapp': {
                'handlers': ['console', 'app_file', 'error_file'],
                'level': 'DEBUG' if debug else 'INFO',
                'propagate': False,
            },
            'planandsubscription': {
                'handlers': ['console', 'app_file', 'error_file'],
                'level': 'DEBUG' if debug else 'INFO',
                'propagate': False,
            },
            'backend': {
                'handlers': ['console', 'app_file', 'error_file'],
                'level': 'DEBUG' if debug else 'INFO',
                'propagate': False,
            },

            # Performance logger
            'performance': {
                'handlers': ['performance_file'],
                'level': 'INFO',
                'propagate': False,
            },

            # Security/audit logger
            'security': {
                'handlers': ['security_file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },

            # Celery logger
            'celery': {
                'handlers': ['console', 'celery_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'celery.task': {
                'handlers': ['console', 'celery_file'],
                'level': 'INFO',
                'propagate': False,
            },

            # Third-party loggers (reduce noise)
            'urllib3': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'requests': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'boto3': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'botocore': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
        },
    }


# =============================================================================
# Utility Functions
# =============================================================================

def get_logger(name):
    """
    Get a logger with the application prefix.

    Args:
        name: Logger name (will be prefixed with 'multinotesai.')

    Returns:
        Logger instance
    """
    return logging.getLogger(f"multinotesai.{name}")


def log_with_context(logger, level, message, **context):
    """
    Log a message with additional context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error)
        message: Log message
        **context: Additional context to include
    """
    extra = {'extra': context}
    getattr(logger, level)(message, extra=extra)


class RequestContextAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds request context to all log messages.

    Usage:
        logger = RequestContextAdapter(
            logging.getLogger(__name__),
            {'request_id': 'abc123', 'user_id': 1}
        )
        logger.info("Processing request")
    """

    def process(self, msg, kwargs):
        # Merge extra context
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


# =============================================================================
# Settings Configuration
# =============================================================================

"""
Add to your settings.py:

from backend.logging_config import get_logging_config

LOG_DIR = os.environ.get('LOG_DIR', '/var/log/multinotesai')
LOGGING = get_logging_config(log_dir=LOG_DIR, debug=DEBUG)
"""


# Required for imports
import logging.handlers
