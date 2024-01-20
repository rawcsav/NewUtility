import logging

# Define a flag to check if the logger has been configured
logger_configured = False


def setup_logging():
    global logger_configured
    if not logger_configured:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(module)s:%(message)s")
        logger_configured = True
    return logging.getLogger()
