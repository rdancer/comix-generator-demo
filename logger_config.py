import logging

class LogColors:
    RESET = "\033[0m"
    DEBUG = "\033[38;5;45m"  # Cyan-like color
    INFO = "\033[38;5;34m"   # Some shade of green
    WARNING = "\033[38;5;226m" # Bright yellow
    ERROR = "\033[38;5;196m"   # Bright red
    CRITICAL = "\033[48;5;196m" # Red background (bright)

class ColorFormatter(logging.Formatter):
    def __init__(self, fmt):
        super().__init__(fmt)

    def format(self, record):
        color = LogColors.RESET
        if record.levelno == logging.DEBUG:
            color = LogColors.RESET
        elif record.levelno == logging.INFO:
            color = LogColors.INFO
        elif record.levelno == logging.WARNING:
            color = LogColors.WARNING
        elif record.levelno == logging.ERROR:
            color = LogColors.ERROR
        elif record.levelno == logging.CRITICAL:
            color = LogColors.CRITICAL

        record.msg = f"{color}{record.msg}{LogColors.RESET}"
        return super().format(record)

def get_logger(level):
    logger = logging.getLogger("uvicorn")
    logger.setLevel(level)

    formatter = ColorFormatter("[%(asctime)s %(levelname)s [%(funcName)s] %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(handler)

    print_test_message(logger)
    return logger

def print_test_message(logger):
    """
    Prints a test message for each log level, so that we can see the colors.
    """
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    