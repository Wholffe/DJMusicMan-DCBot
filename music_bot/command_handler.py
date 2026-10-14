import functools
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, Concatenate, ParamSpec

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
        self, func: Callable[Concatenate[Any, P], Awaitable[Any]]
    ) -> Callable[Concatenate[Any, P], Coroutine[Any, Any, None]]:
        """
        A decorator that wraps a command function in a try...except block.
        """

        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: P.args, **kwargs: P.kwargs) -> None:
            try:
                await func(ctx, *args, **kwargs)
            except Exception as e:
                await self.message_handler.send_error(
                    ctx,
                    f'Command "{func.__name__}" failed: {e}',
                )

        return wrapper
