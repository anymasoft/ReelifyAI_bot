import asyncio
import logging
from bot.handlers import dp, bot
from config import AUTO_FLUSH_REDIS
from storage.redis import RedisStorage

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def flush_redis():
    """Очищает кэш Redis через Python-клиент."""
    if AUTO_FLUSH_REDIS:
        try:
            redis = RedisStorage()
            redis.client.flushall()
            logger.info("Redis cache flushed successfully.")
        except Exception as e:
            logger.error(f"Failed to flush Redis cache: {str(e)}")

async def main():
    # Очистка кэша Redis перед запуском
    flush_redis()

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received shutdown signal, stopping bot...")
        await dp.stop_polling()
        await bot.session.close()
        logger.info("Bot stopped gracefully.")
    except Exception as e:
        logger.error(f"Unexpected error during polling: {str(e)}", exc_info=True)
        await dp.stop_polling()
        await bot.session.close()
        logger.info("Bot stopped due to error.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot terminated by user.")
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)