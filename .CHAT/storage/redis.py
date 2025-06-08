import redis
import json
import logging
from config import CACHE_TTL, REQUEST_LIMIT, REQUEST_TTL, DEBUG_MODE

# Настройка логирования
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

    def set_cache(self, user_id: int, query: str, data: dict):
        key = f"cache:{user_id}:{query}"
        self.client.setex(key, CACHE_TTL, json.dumps(data))
        logger.debug(f"Cached data for user {user_id}, query: {query}")

    def get_cache(self, user_id: int, query: str) -> dict | None:
        key = f"cache:{user_id}:{query}"
        data = self.client.get(key)
        logger.debug(f"Cache lookup for user {user_id}, query: {query}, found: {bool(data)}")
        return json.loads(data) if data else None