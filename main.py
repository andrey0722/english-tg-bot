"""Bot application entry point."""

import sys

from application import Application, ApplicationError
from log import LogLevel, LogManager


def main():
    """Initialize the bot and run it."""
    log = LogManager()
    default_log_level = LogLevel.INFO
    log.setup(default_log_level)
    logger = log.create_logger(main, default_log_level)
    try:
        app = Application(log)
        app.run()
    except KeyboardInterrupt:
        logger.info('Stopped by keyboard interrupt')
    except ApplicationError as e:
        logger.fatal('Stopped on error: %s', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
