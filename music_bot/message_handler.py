import discord


class MessageHandler:
    """Handles sending messages to the Discord context."""

    def __init__(self):
        self.prefix_success = "✅"
        self.prefix_error = "❌"
        self.prefix_info = ""

    async def send_success(self, ctx, message: str):
        await ctx.send(f"{self.prefix_success} {message}")

    async def send_error(self, ctx, message: str):
        await ctx.send(f"{self.prefix_error} {message}")

    async def send_info(self, ctx, message: str):
        await ctx.send(f"{self.prefix_info} {message}")

    async def send_raw(self, ctx, message: str):
        await ctx.send(message)

    async def send_embed(self, ctx, embed_dict: dict):
        embed = discord.Embed(
            description=embed_dict.get("description", ""),
            color=discord.Color.blurple()
        )

        if embed_dict.get("title"):
            embed.title = embed_dict["title"]

        for field in embed_dict.get("fields", []):
            embed.add_field(name=field.get("name", ""), value=field.get("value", ""), inline=field.get("inline", False))

        if embed_dict.get("footer"):
            embed.set_footer(text=embed_dict["footer"])

        await ctx.send(embed=embed)