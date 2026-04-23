import logging
import sys
from pathlib import Path

def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Configures a standard logger for the Hydro-Dataset project.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    if not logger.handlers:
        # Console handler
        c_handler = logging.StreamHandler(sys.stdout)
        c_handler.setLevel(getattr(logging, log_level.upper()))

        # Formatting
        c_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(c_format)

        # Add handler to logger
        logger.addHandler(c_handler)

    return logger
