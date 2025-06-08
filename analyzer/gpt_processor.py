import openai
import hashlib
import json
from typing import Dict, List
import logging
from analyzer.ngram import NGramAnalyzer
from storage.redis import RedisStorage
from fuzzywuzzy import fuzz

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

class GPTProcessor:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.redis = RedisStorage()
        self.analyzer = NGramAnalyzer()

    def cluster_phrases(self, phrases: List[Dict[str, int]]) -> List[Dict[str, int]]:
        clustered = []
        used = set()
        for i, p1 in enumerate(phrases):
            if i in used:
                continue
            cluster = [p1]
            cluster_count = p1['count']
            for j, p2 in enumerate(phrases[i+1:], i+1):
                if j not in used and fuzz.ratio(p1['phrase'].lower(), p2['phrase'].lower()) > 80:
                    cluster.append(p2)
                    cluster_count += p2['count']
                    used.add(j)
            clustered.append({"phrase": p1['phrase'], "count": cluster_count})
            used.add(i)
        return clustered

    def filter_junk_phrases(self, phrases: List[Dict[str, int]], niche: str) -> List[Dict[str, int]]:
        """Фильтрация мусорных фраз с помощью GPT."""
        phrase_list = [p['phrase'] for p in phrases]
        prompt = """
        Вы — SEO-аналитик. Дана ниша: "{}".
        Определите, какие из следующих фраз бесполезны для SEO-продвижения в этой нише.
        Бесполезные фразы включают:
        - Рекламные маркеры ("скидка", "акция", "🔥").
        - Общие слова без конкретики ("качество", "лучший").
        - Технические или неинформативные фразы ("обувная серия", "в наличии").
        - Бренды ("ZOLINBERG", "YZYNX").
        Верните JSON: [{{ "phrase": "фраза", "is_junk": true/false }}, ...].
        Фразы:
        {}
        """.format(niche, "\n".join(phrase_list))
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.1
            )
            result = json.loads(response.choices[0].message.content)
            return [
                p for p in phrases
                if not next((r['is_junk'] for r in result if r['phrase'] == p['phrase']), False)
            ]
        except Exception as e:
            logger.error(f"GPT junk filter error: {str(e)}")
            return phrases  # Возвращаем исходный список при ошибке

    def process_ngrams(self, query: str, data: Dict[str, List[str]]) -> List[Dict[str, int]]:
        cache_key = f"gpt_ngrams:{hashlib.md5((query + json.dumps(data)).encode()).hexdigest()}"
        cached = self.redis.get_cache(0, cache_key)
        if cached:
            logger.info(f"Cache hit for GPT n-grams: {cache_key}")
            return cached

        texts = (
            data.get('titles', []) +
            data.get('descriptions', []) +
            data.get('alt_texts', []) +
            data.get('breadcrumbs', []) +
            data.get('product_descriptions', [])
        )
        text_input = "\n".join([t for t in texts if t and t.lower() not in ['распродажа', 'осталась 1 шт', '']])
        if not text_input:
            logger.warning("Empty or non-informative text input for GPT processing")
            return self.fallback_ngram_analysis(query, data)

        prompt = """
        Вы — SEO-аналитик. Дан запрос: "{}".
        Извлеките из текста ключевые фразы (1–3 слова), релевантные для SEO.
        Обязательно включите биграммы (например, "зимние ботинки") и триграммы (например, "женские зимние ботинки"), связанные с запросом.
        Исключите:
        - Неинформативные слова ("купить", "доставка", "распродажа", "обувная серия", "гарантия", "отзывы").
        - Бренды (например, "ZOLINBERG", "YZYNX", "Vicappy", "ARPSTAR", "Your Way").
        - Технические коды ("ma7e4zm/a").
        - Повторы слов ("ботинки ботинки").
        Нормализуйте термины ("boots" → "ботинки", "women" → "женские").
        Верните JSON: [{{ "phrase": "фраза", "count": N }}, ...], где N — частота фразы.
        Текст:
        {}
        """.format(query, text_input)
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1
            )
            result = response.choices[0].message.content
            parsed_result = json.loads(result)
            parsed_result = [item for item in parsed_result if item.get('phrase') and item.get('count', 0) > 0]
            if not parsed_result:
                logger.warning("GPT returned empty result, falling back to local n-gram analysis")
                parsed_result = self.fallback_ngram_analysis(query, data)
            clustered_result = self.cluster_phrases(parsed_result)
            filtered_result = self.filter_junk_phrases(clustered_result, query)
            self.redis.set_cache(0, cache_key, filtered_result)
            return filtered_result
        except Exception as e:
            logger.error(f"GPT processing error: {str(e)}")
            return self.fallback_ngram_analysis(query, data)

    def fallback_ngram_analysis(self, query: str, data: Dict[str, List[str]]) -> List[Dict[str, int]]:
        texts = (
            data.get('titles', []) +
            data.get('descriptions', []) +
            data.get('alt_texts', []) +
            data.get('breadcrumbs', []) +
            data.get('product_descriptions', [])
        )
        tfidf_result = self.analyzer.analyze_tfidf(texts, ngram_range=(1, 3), max_features=50)
        return [{"phrase": phrase, "count": int(score * 10)} for phrase, score in tfidf_result]