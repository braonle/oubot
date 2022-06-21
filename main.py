import logging
from engine.tg.tg_handlers import start_bot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

if __name__ == '__main__':
    start_bot()
