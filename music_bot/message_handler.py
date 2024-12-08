class MessageHandler:
    """Handles sending messages to the Discord context."""

    def __init__(self):
        self.prefix_success = "✅"
        self.prefix_error = "❌"
        self.prefix_info = "i"

    async def send_success(self, ctx, message: str):
        await ctx.send(f"{self.prefix_success} {message}")

    async def send_error(self, ctx, message: str):
        await ctx.send(f"{self.prefix_error} {message}")

    async def send_info(self, ctx, message: str):
        await ctx.send(f"{self.prefix_info} {message}")

    async def send_raw(self, ctx, message: str):
        await ctx.send(message)