import logging
import sys

from extract_load.config import Settings
from extract_load.extract import ExtractError, extract
from extract_load.load import LoadError, load


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def main() -> int:
    settings = Settings()  # falha cedo se .env incompleto
    setup_logging(settings.log_level)
    log = logging.getLogger("extract_load")
    log.info("pipeline starting")
    try:
        dfs = extract(settings)
        load(dfs, settings)
    except (ExtractError, LoadError) as e:
        log.error("pipeline failed: %s", e)
        return 1
    log.info("pipeline complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
