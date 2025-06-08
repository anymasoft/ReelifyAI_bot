import re
from collections import Counter
from typing import List, Tuple
import logging
from storage.redis import RedisStorage
from storage.sqlite import SQLiteStorage
from pathlib import Path

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

class StopWordsManager:
    def __init__(self, redis_client: RedisStorage = None, sqlite_client: SQLiteStorage = None):
        self.redis = redis_client
        self.sqlite = sqlite_client
        self.static_stopwords = set(self._load_file("filters/static_stopwords.txt"))
        self.static_phrases = set(self._load_file("filters/static_stop_phrases.txt"))
        self.category_stopwords = self._load_category_stopwords("filters/stopwords")

    def _load_file(self, filepath: str) -> List[str]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return [line.strip().lower() for line in f if line.strip()]
        except FileNotFoundError:
            logger.warning(f"Stopwords file not found: {filepath}")
            return []

    def _load_category_stopwords(self, directory: str) -> dict:
        category_stopwords = {}
        directory_path = Path(directory)
        if directory_path.exists():
            for file in directory_path.glob("*.txt"):
                category = file.stem
                category_stopwords[category] = set(self._load_file(str(file)))
        return category_stopwords

    def is_stopword(self, word: str, category: str = None) -> bool:
        word = word.lower().strip()
        if word in self.static_stopwords or word in self.static_phrases:
            return True
        if category and category in self.category_stopwords and word in self.category_stopwords[category]:
            return True
        if self.redis and self.redis.is_stopword(word):
            return True
        if self.sqlite and self.sqlite.is_stopword(word):
            return True
        return False

    def filter_ngrams(self, ngram_list: List[Tuple[str, int]], category: str = None) -> List[Tuple[str, int]]:
        return [(ng, count) for ng, count in ngram_list if not self.is_stopword(ng, category)]

    def add_stopword(self, word: str, user_id: int = None, category: str = None):
        word = word.lower().strip()
        if category and category in self.category_stopwords:
            self.category_stopwords[category].add(word)
            with open(f"filters/stopwords/{category}.txt", "a", encoding="utf-8") as f:
                f.write(f"{word}\n")
        if self.redis:
            self.redis.add_stopword(word, user_id)
        if self.sqlite:
            self.sqlite.add_stopword(word, user_id)
        logger.info(f"Added stopword: {word} (user_id={user_id}, category={category})")

    def get_user_stopwords(self, user_id: int) -> List[str]:
        if self.redis:
            return self.redis.get_stopwords(user_id)
        if self.sqlite:
            return self.sqlite.get_stopwords(user_id)
        return []

    def auto_learn_stopwords(self, ngram_counter: Counter, threshold: int = 100, category: str = None):
        """Добавляет в стоп-слова частые, но неинформативные фразы."""
        for phrase, freq in ngram_counter.items():
            if freq >= threshold and (len(phrase) < 3 or re.search(r'[^\w\s]', phrase)):
                self.add_stopword(phrase, category=category)