import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class Claude3OpusCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-3-Opus",
            nickname="Claude",
            trigger_words=['claude', 'claude 3', 'opus'],
            model="anthropic/claude-3-opus:beta",
            provider="openrouter",
            prompt_file="claude3opus",
            supports_vision=True  # Enable vision support
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[{self.name}] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[{self.name}] Using provider: {self.provider}")
        logging.debug(f"[{self.name}] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Claude-3-Opus"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Add message to context before processing
        if self.context_cog:
            try:
                channel_id = str(message.channel.id)
                guild_id = str(message.guild.id) if message.guild else None
                user_id = str(message.author.id)
                content = message.content
                is_assistant = False
                persona_name = self.name
                emotion = None

                await self.context_cog.add_message_to_context(
                    channel_id=channel_id,
                    guild_id=guild_id,
                    user_id=user_id,
                    content=content,
                    is_assistant=is_assistant,
                    persona_name=persona_name,
                    emotion=emotion
                )
            except Exception as e:
                logging.error(f"[{self.name}] Failed to add message to context: {str(e)}")

        # Let base_cog handle message processing
        await super().handle_message(message)

async def setup(bot):
    # Register the cog with its proper name
    try:
        logging.info(f"[Claude-3-Opus] Starting cog setup...")
        cog = Claude3OpusCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Claude-3-Opus] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[Claude-3-Opus] Cog is loaded and listening for triggers: {cog.trigger_words}")
        return cog
    except Exception as e:
        logging.error(f"[Claude-3-Opus] Failed to register cog: {str(e)}", exc_info=True)
        raise
