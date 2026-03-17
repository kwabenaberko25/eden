import logging

from eden.logging import get_logger, setup_logging


def test_setup_logging_sets_module_level_and_handler():
    # Configure logging with a specific module override
    setup_logging(level="INFO", loggers={"eden.db": "DEBUG"})

    logger = logging.getLogger("eden.db")
    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert len(logger.handlers) > 0

    # Root eden logger should also have a handler
    eden_logger = logging.getLogger("eden")
    assert any(isinstance(h, logging.StreamHandler) for h in eden_logger.handlers)


def test_get_logger_prefixes_with_eden():
    logger = get_logger("db")
    assert logger.name == "eden.db"

    logger2 = get_logger("eden.db")
    assert logger2.name == "eden.db"
