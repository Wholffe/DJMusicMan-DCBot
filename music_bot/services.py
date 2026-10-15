"""Shared service instances."""

from concurrent.futures import ThreadPoolExecutor

from .cache_manager import CacheManager
from .command_handler import CommandHandler
from .idle_timer import IdleTimer
from .message_handler import MessageHandler

# region Global Instances
message_handler = MessageHandler()
idle_timer = IdleTimer()
cache_manager = CacheManager()
command_handler = CommandHandler(message_handler)
executor = ThreadPoolExecutor(max_workers=5)
