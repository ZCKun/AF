import os

from loguru import logger
from datetime import datetime

LOG_PATH = "log"
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

logger.add(os.path.join(LOG_PATH, f"a_{datetime.now().strftime('%Y%m%d%H%M%S')}.log"),
           format="{time} | {level} - {message}",
           enqueue=True)
