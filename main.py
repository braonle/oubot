import logging
from engine.tg.tg_handlers import start_bot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

start_bot()
