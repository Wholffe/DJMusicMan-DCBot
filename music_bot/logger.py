import functools
import logging
import logging.handlers
import os
from typing import Callable

from music_bot.config import DATA_DIR

LOG_FILE = os.path.join(DATA_DIR, "music_bot.log")


def setup_logger():
    """Configures and returns a logger instance."""
    os.makedirs(DATA_DIR, exist_ok=True)

    logger = logging.getLogger("MusicBot")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"
    )

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


def log_command(logger_instance: logging.Logger):
    """A simple decorator to log the execution of a bot command function."""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(self_or_musicbot, ctx, *args, **kwargs):
            user = ctx.author
            command_name = func.__name__

            logger_instance.info(
                f"User '{user}' executed command '{command_name}' with args: {args}"
            )
            try:
                result = await func(self_or_musicbot, ctx, *args, **kwargs)
                logger_instance.info(
                    f"Finished '{command_name}' execution by user '{user}'."
                )
                return result
            except Exception as e:
                logger_instance.error(
                    f"Error executing command '{command_name}' for user '{user}': {e}",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


logger = setup_logger()
log_command = log_command(logger)
