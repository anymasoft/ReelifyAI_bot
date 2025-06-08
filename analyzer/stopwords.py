import nltk
from nltk.corpus import stopwords
from typing import Set

class StopWords:
    def __init__(self):
        nltk.download('stopwords', quiet=True)
        self.stop_words = set(stopwords.words('russian')) | set(stopwords.words('english'))
        self.custom_stop_words = {
            'купить', 'цена', 'ozon', 'доставка', 'бесплатно', 'руб', 'скидка', 'акция',
            'товар', 'интернет', 'магазин', 'качество', 'гарантия', 'шт', 'осталось',
            'анимация', 'анимацией', 'кнопка', 'боковая', 'камеры', 'смартфона',
            'обувная', 'серия', 'угги/ботинки', 'распродажа', 'отзывы'
        }
        self.stop_words.update(self.custom_stop_words)

    def filter(self, tokens: list[str]) -> list[str]:
        return [token for token in tokens if token.lower() not in self.stop_words]