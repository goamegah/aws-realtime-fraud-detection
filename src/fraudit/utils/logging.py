# fraudit/utils/logging.py

import logging

def get_logger(name: str = "fraudit"):
    """
    Configure et retourne un logger standardisé.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)

    # Eviter les handlers multiples si déjà configuré
    if not logger.handlers:
        logger.addHandler(ch)

    return logger
