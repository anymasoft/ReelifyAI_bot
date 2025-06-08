import openai
from typing import Dict, List
import logging
import json

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
        openai.api_key = api_key

    def process_ngrams(self, query: str, data: Dict[str, List[str]]) -> List[Dict[str, int]]:
        texts = (
            data.get('titles', []) +
            data.get('descriptions', []) +
            data.get('alt_texts', []) +
            data.get('breadcrumbs', [])
        )
        text_input = "\n".join(texts)
        prompt = """
        Вы — SEO-аналитик. Дан запрос: "{}".
        Извлеките из текста ниже ключевые фразы (1–3 слова), релевантные для SEO.
        Исключите неинформативные слова (например, "купить", "доставка", "цена"),
        технические коды (например, "ma7e4zm/a") и повторы слов.
        Нормализуйте термины (например, "case" → "чехол", "boots" → "ботинки").
        Верните список фраз с частотой в формате JSON: [{{"phrase": "фраза", "count": N}}, ...].
        Текст:
        {}
        """.format(query, text_input)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            result = response.choices[0].message.content
            return json.loads(result)
        except Exception as e:
            logger.error(f"GPT processing error: {str(e)}")
            return []