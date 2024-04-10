import logging


def configure_logging(log_level=None):
    effective_log_level = log_level if log_level is not None else logging.WARNING

    logging.basicConfig(level=effective_log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Example of adding a file handler
    file_handler = logging.FileHandler('newutil.log')
    file_handler.setLevel(effective_log_level)  # Use the effective log level for the file handler as well
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    return logging.getLogger(__name__)
