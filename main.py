"""Bot application entry point."""

import sys

from application import Application
from application import ApplicationError
import log


def main():
    """Initialize the bot and run it."""
    log.setup_logging(log.LogLevel.INFO)
    logger = log.create_logger(main)
    try:
        app = Application()
        app.run()
    except KeyboardInterrupt:
        logger.info('Stopped by keyboard interrupt')
    except ApplicationError as e:
        logger.fatal('Stopped on error: %s', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
