from loguru import logger
import sys
from pathlib import Path


def configure_logging(log_dir: Path | None = None, level: str = "INFO") -> None:
    """Configure loguru with sensible defaults for console and rotating files."""
    logger.remove()
    logger.add(sys.stdout, level=level, enqueue=True, colorize=True, backtrace=False, diagnose=False)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        # Use unique daily log files to avoid Windows rename locks during rotation
        logger.add(
            log_dir / "trading_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="7 days",
            level=level,
            serialize=False,
            enqueue=True,
            delay=True,
        )


__all__ = ["configure_logging", "logger"]
