import functools
import logging
import logging.handlers
import os
from collections.abc import Awaitable, Callable, Coroutine
from datetime import datetime
from typing import Any, Concatenate, ParamSpec, TypeVar

from .config import DATA_DIR

LOG_DIR = os.path.join(DATA_DIR, "logs")

P = ParamSpec("P")
T = TypeVar("T")


def setup_logger() -> logging.Logger:
    """Configures and returns a logger instance."""
    os.makedirs(LOG_DIR, exist_ok=True)

    log_file_path = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger("MusicBot")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


logger = setup_logger()


def log_command(
    func: Callable[Concatenate[Any, Any, P], Awaitable[T]],
) -> Callable[Concatenate[Any, Any, P], Coroutine[Any, Any, T]]:
    """A simple decorator to log the execution of a bot command function."""

    @functools.wraps(func)
    async def wrapper(
        self_or_musicbot: Any, ctx: Any, *args: P.args, **kwargs: P.kwargs
    ) -> T:
        user = ctx.author
        command_name = func.__name__

        logger.info(
            f"User '{user}' executed command '{command_name}' with args: {args}"
        )
        try:
            result = await func(self_or_musicbot, ctx, *args, **kwargs)
            logger.info(f"Finished '{command_name}' execution by user '{user}'.")
            return result
        except Exception as e:
            logger.error(
                f"Error executing command '{command_name}' for user '{user}': {e}",
                exc_info=True,
            )
            raise

    return wrapper
