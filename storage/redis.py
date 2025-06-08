import redis
import json
import logging
from config import CACHE_TTL, REQUEST_LIMIT, REQUEST_TTL, DEBUG_MODE
from typing import List, Optional

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

class RedisStorage:
    def __init__(self, host="localhost", port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def check_request_limit(self, user_id: int) -> bool:
        logger.info(f"Checking request limit for user {user_id}, DEBUG_MODE={DEBUG_MODE}")
        if DEBUG_MODE:
            logger.debug(f"Debug mode enabled, skipping request limit for user {user_id}")
            return True
        key = f"user:{user_id}:requests"
        count = self.client.get(key)
        logger.debug(f"Request count for user {user_id}: {count}")
        if count is None:
            self.client.setex(key, REQUEST_TTL, 1)
            logger.info(f"Set initial request count for user {user_id}")
            return True
        if int(count) >= REQUEST_LIMIT:
            logger.warning(f"User {user_id} exceeded request limit")
            return False
        self.client.incr(key)
        logger.info(f"Incremented request count for user {user_id}")
        return True

    def set_cache(self, user_id: int, key: str, data: dict):
        cache_key = f"cache:{user_id}:{key}"
        self.client.setex(cache_key, CACHE_TTL, json.dumps(data))
        logger.debug(f"Cached data for user {user_id}, key: {key}")

    def get_cache(self, user_id: int, key: str) -> Optional[dict]:
        cache_key = f"cache:{user_id}:{key}"
        data = self.client.get(cache_key)
        logger.debug(f"Cache lookup for user {user_id}, key: {key}, found: {bool(data)}")
        return json.loads(data) if data else None

    def add_stopword(self, word: str, user_id: int = None):
        word = word.lower().strip()
        self.client.sadd("global_stopwords", word)
        if user_id:
            self.client.sadd(f"user:{user_id}:stopwords", word)
        logger.info(f"Added stopword to Redis: {word} (user_id={user_id})")

    def is_stopword(self, word: str) -> bool:
        word = word.lower().strip()
        return self.client.sismember("global_stopwords", word)

    def get_stopwords(self, user_id: int = None) -> List[str]:
        if user_id:
            return list(self.client.smembers(f"user:{user_id}:stopwords"))
        return list(self.client.smembers("global_stopwords"))