import logging
import os
import time
from functools import wraps
from logging.handlers import RotatingFileHandler


class Logger:
    """
    A configurable logger class that handles logging to the console
    and to rotating files. Also provides a decorator for logging function calls.
    """

    def __init__(
        self,
        logger_name: str = "MusicBot",
        log_level: int = logging.INFO,
        log_dir: str = "logs",
        log_file: str = "music_bot.log",
    ):
        """
        Initializes the logger with specific configurations.

        Args:
            logger_name (str): The name of the logger.
            log_level (int): The logging level (e.g., logging.INFO).
            log_dir (str): The directory for storing log files.
            log_file (str): The name of the log file.
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)
        self.logger.propagate = False

        log_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s"
        )

        if not self.logger.handlers:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Console Hander
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_format)
            self.logger.addHandler(console_handler)

            file_handler = RotatingFileHandler(
                os.path.join(log_dir, log_file),
                maxBytes=(5 * 1024 * 1024),  # 5 MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(log_format)
            self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """Returns the configured logger instance."""
        return self.logger

    def log_function(self, level: int = logging.INFO):
        """
        A decorator that logs a function's call, its arguments,
        the result, and its execution time.

        Args:
            level (int): The log level for the success message (e.g., logging.DEBUG).
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                func_name = func.__name__
                arg_list = [repr(a) for a in args[1:]]
                kwarg_list = [f"{k}={v!r}" for k, v in kwargs.items()]
                all_args = ", ".join(arg_list + kwarg_list)

                self.logger.log(
                    level, f"Calling function '{func_name}' with args: ({all_args})"
                )

                try:
                    result = await func(*args, **kwargs)
                    end_time = time.time()
                    execution_time = end_time - start_time

                    self.logger.log(
                        level,
                        f"Function '{func_name}' finished in {execution_time:.4f}s. "
                        f"Result: {result!r}",
                    )
                    return result
                except Exception as e:
                    self.logger.error(
                        f"Exception in function '{func_name}': {e}", exc_info=True
                    )
                    raise

            return wrapper

        return decorator
