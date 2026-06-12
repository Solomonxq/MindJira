import structlog

logger = structlog.get_logger()


def main() -> None:
    logger.info("Hello from mindjira!")


if __name__ == "__main__":
    main()
