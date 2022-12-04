#!/usr/bin/env python
import os
import sys
import logging
import logging.handlers

# create log folder
current_directory = os.getcwd()
final_directory = os.path.join(
    current_directory, os.environ.get("LOG_FILE", "log/locallog").split("/")[0]
)
if not os.path.exists(final_directory):
    os.makedirs(final_directory)

# create rotating handler
handler = logging.handlers.TimedRotatingFileHandler(
    filename=os.environ.get("LOG_FILE", "log/locallog"),
    when="midnight",
    backupCount=os.environ.get("DELETE_LOG_OLDER_THAN_DAYS", 30),
    encoding="utf-8",
    delay=False,
)

logging.basicConfig(
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[handler],
    level=os.environ.get("LOG_LEVEL", "WARNING").upper(),
)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "injury_predict_web.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        error_message = (
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        )
        logging.error(error_message)
        raise ImportError(error_message) from exc
    execute_from_command_line(sys.argv)
