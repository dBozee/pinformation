import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ui import Button

from .bot_config import BotConfig

logger = logging.getLogger(__name__)
handler = logging.FileHandler(filename='bot_log.log', encoding='utf-8', mode='w')


INTENTS = discord.Intents.default()
INTENTS.message_content = True

class PinformationBot(commands.Bot):
    def __init__(self, config: BotConfig):
        super().__init__(intents=INTENTS,command_prefix=commands.when_mentioned_or(config.prefix))