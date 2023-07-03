"""Logger customizado para `Utopiafy`"""

import logging

import colorlog

logger = logging.getLogger(name=__name__)
logger.setLevel(level=logging.DEBUG)

formatter = colorlog.ColoredFormatter(
    fmt="[%(log_color)s%(levelname)s%(reset)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
