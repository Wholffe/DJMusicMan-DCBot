from .message_handler import MessageHandler


class CommandHandler:
    """
    A class to handle command-related logic, such as error handling.
    It's initialized with a message_handler to send responses.
    """

    def __init__(self, message_handler: MessageHandler):
        self.message_handler = message_handler

    def handle_errors(self, func):
        """
        A decorator that wraps a command function in a try...except block.
        """

        async def wrapper(ctx, *args, **kwargs):
            try:
                await func(ctx, *args, **kwargs)
            except Exception as e:
                await self.message_handler.send_error(
                    ctx,
                    f'Command "{func.__name__}" failed: {e}',
                )

        return wrapper
