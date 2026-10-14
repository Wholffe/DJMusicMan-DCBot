import functools
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, ParamSpec

from discord.ext import commands

from .logger import logger
from .message_handler import MessageHandler

P = ParamSpec("P")


class CommandHandler:
    """
    A class to handle command-related logic, such as error handling.
    It's initialized with a message_handler to send responses.
    """

    def __init__(self, message_handler: MessageHandler) -> None:
        self.message_handler = message_handler

    def handle_errors(
        self, func: Callable[P, Awaitable[Any]]
    ) -> Callable[P, Coroutine[Any, Any, None]]:
        """
        A decorator that wraps a command function in a try...except block.
        Errors are sent to the first commands.Context argument, or logged if
        there is none.
        """

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                ctx = next(
                    (
                        arg
                        for arg in (*args, *kwargs.values())
                        if isinstance(arg, commands.Context)
                    ),
                    None,
                )
                if ctx is None:
                    logger.error(
                        f"Command '{func.__name__}' failed without a context: {e}",
                        exc_info=True,
                    )
                    return
                await self.message_handler.send_error(
                    ctx,
                    f'Command "{func.__name__}" failed: {e}',
                )

        return wrapper
