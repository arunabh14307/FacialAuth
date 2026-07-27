"""
Structured Logging Module — Application, Audit, and Security Event Logging.
"""

import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(base_dir=None):
    """
    Initialize application and security loggers with rotating file handlers.
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    logs_dir = os.path.join(base_dir, '..', 'data', 'logs')
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        logs_dir = '/tmp/logs'
        os.makedirs(logs_dir, exist_ok=True)

    # 1. Main App Logger
    logger = logging.getLogger('faceguard')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
        )
        
        # File Handler (5 MB max, 3 backups)
        app_log_path = os.path.join(logs_dir, 'app.log')
        file_handler = RotatingFileHandler(app_log_path, maxBytes=5*1024*1024, backupCount=3)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 2. Security Logger
    sec_logger = logging.getLogger('faceguard.security')
    sec_logger.setLevel(logging.INFO)
    
    if not sec_logger.handlers:
        sec_formatter = logging.Formatter(
            '[%(asctime)s] [SECURITY] %(message)s'
        )
        sec_log_path = os.path.join(logs_dir, 'security.log')
        sec_file_handler = RotatingFileHandler(sec_log_path, maxBytes=5*1024*1024, backupCount=5)
        sec_file_handler.setLevel(logging.INFO)
        sec_file_handler.setFormatter(sec_formatter)
        sec_logger.addHandler(sec_file_handler)

    return logger, sec_logger


# Global instances
logger, sec_logger = setup_logger()


def log_security_event(event_type, details, ip_address=None, user_id=None):
    """Utility to log security-sensitive events."""
    msg = f"EVENT={event_type} | USER_ID={user_id or 'ANONYMOUS'} | IP={ip_address or 'UNKNOWN'} | DETAILS={details}"
    sec_logger.info(msg)
