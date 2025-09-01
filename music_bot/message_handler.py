import discord


class MessageHandler:
    """Handles sending messages to Discord context with embeds."""

    COLORS = {
        "success": discord.Color.green(),
        "error": discord.Color.red(),
        "info": discord.Color.blurple(),
        "default": discord.Color.blurple(),
    }

    async def _send_embed(
        self,
        ctx,
        message: str = "",
        title: str = "",
        color: discord.Color = None,
        fields: list[dict] = None,
        footer: str = None,
    ):
        embed = discord.Embed(
            description=message, color=color or self.COLORS["default"]
        )
        if title:
            embed.title = title
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False),
                )
        if footer:
            embed.set_footer(text=footer)
        await ctx.send(embed=embed)

    async def send_success(self, ctx, message: str):
        await self._send_embed(
            ctx,
            message=message,
            color=self.COLORS["success"],
        )

    async def send_error(self, ctx, message: str):
        await self._send_embed(
            ctx,
            message=message,
            color=self.COLORS["error"],
        )

    async def send_info(self, ctx, message: str):
        await self._send_embed(
            ctx,
            message=message,
            color=self.COLORS["info"],
        )

    async def send_raw(self, ctx, message: str):
        await self._send_embed(ctx, message=message)

    async def send_custom(self, ctx, embed_dict: dict):
        await self._send_embed(
            ctx,
            message=embed_dict.get("description", ""),
            title=embed_dict.get("title", ""),
            fields=embed_dict.get("fields"),
            footer=embed_dict.get("footer"),
            color=self.COLORS.get(embed_dict.get("color"), self.COLORS["default"]),
        )
