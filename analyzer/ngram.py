import nltk
import re
import pymorphy3
from nltk.tokenize import word_tokenize
from nltk.util import ngrams
from collections import Counter
from typing import Dict, List, Tuple
from analyzer.stopwords import StopWords
from sklearn.feature_extraction.text import TfidfVectorizer

class NGramAnalyzer:
    def __init__(self):
        nltk.download('punkt', quiet=True)
        self.stopwords = StopWords()
        self.morph = pymorphy3.MorphAnalyzer()
        self.term_mapping = {
            'case': 'чехол',
            'silicone': 'силиконовый',
            'silicon': 'силиконовый',
            'clear': 'прозрачный',
            'leather': 'кожаный',
            'nfc': '',
            'animation': '',
            'midnight': 'тёмный',
            'black': 'чёрный',
            'aquamarine': '',
            'peony': '',
            'stone': '',
            'pro': 'pro',
            'max': 'max',
            'plus': 'plus',
            'mini': 'mini',
            'boots': 'ботинки',
            'ugg': 'угги',
            'winter': 'зимние',
            'women': 'женские',
            'platform': 'платформа',
            'fur': 'мех',
            'stylish': 'стильные',
            'demi': 'демисезонные'
        }
        self.technical_codes = re.compile(r'^[a-z0-9_/]+$|^[a-z0-9]+/[a-z]$')
        self.brand_pattern = re.compile(r'^(zolinberg|vicappy|yzynx|arpstar|your way|botizzo|one move|румаркет|birkabrand|bati|lifexpert|нога-барыня|garofano|cavolo|o-keysi|bitdi|moon-land|gold-class|hoco|всечехлы|elago|broscorp|uniq|karl lagerfeld|gurdini|case place)$', re.IGNORECASE)

    def lemmatize(self, token: str) -> str:
        """Лемматизация токена с помощью pymorphy3."""
        return self.morph.parse(token)[0].normal_form

    def tokenize(self, text: str, query_tokens: set = None) -> List[str]:
        text = re.sub(r'[><.,:;!?()"\\/]|\b\d+\b|\b\w*_\w*\b|\s+', ' ', text)
        tokens = word_tokenize(text.lower(), language='russian')
        tokens = [self.term_mapping.get(token, self.lemmatize(token)) for token in tokens]
        filtered_tokens = [
            token for token in self.stopwords.filter(tokens)
            if any(c.isalpha() for c in token) and
               len(token) > 2 and
               not token.isdigit() and
               not self.technical_codes.match(token) and
               not self.brand_pattern.match(token)
        ]
        if query_tokens:
            filtered_tokens = sorted(
                filtered_tokens,
                key=lambda token: 0 if token in query_tokens or any(q in token for q in query_tokens) else 1
            )
        return filtered_tokens

    def extract_ngrams(self, texts: List[str], n: int, query_tokens: set = None) -> List[Tuple[str, int]]:
        all_ngrams = []
        for text in texts:
            tokens = self.tokenize(text, query_tokens)
            if len(tokens) >= n:
                n_grams = [' '.join(gram) for gram in ngrams(tokens, n) if len(set(gram)) == len(gram)]
                if query_tokens:
                    n_grams = [gram for gram in n_grams if any(q in gram for q in query_tokens)]
                all_ngrams.extend(n_grams)
        return Counter(all_ngrams).most_common()

    def analyze(self, data: Dict[str, List[str]], query: str = '') -> Dict[str, List[Tuple[str, int]]]:
        texts = (
            data.get('titles', []) +
            data.get('descriptions', []) +
            data.get('alt_texts', []) +
            data.get('breadcrumbs', []) +
            data.get('product_descriptions', [])
        )
        query_tokens = set(self.tokenize(query)) if query else set()
        result = {
            'unigrams': self.extract_ngrams(texts, 1, query_tokens),
            'bigrams': self.extract_ngrams(texts, 2, query_tokens),
            'trigrams': self.extract_ngrams(texts, 3, query_tokens)
        }
        return result

    def analyze_tfidf(self, texts: List[str], ngram_range=(1, 3), max_features=50) -> List[Tuple[str, float]]:
        """Анализ TF-IDF для извлечения ключевых фраз."""
        vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            stop_words=list(self.stopwords.stop_words),
            max_features=max_features,
            token_pattern=r'(?u)\b\w+\b'
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.sum(axis=0).A1
        return sorted([(name, score) for name, score in zip(feature_names, scores)], key=lambda x: x[1], reverse=True)

    def get_top_keys(self, ngrams: Dict[str, List[Tuple[str, int]]], limit: int = None) -> List[Tuple[str, int]]:
        combined = (
            ngrams['unigrams'] +
            ngrams['bigrams'] +
            ngrams['trigrams']
        )
        filtered = [(phrase, count) for phrase, count in combined if len(phrase) >= 3 and not re.search(r'[^\w\s]', phrase)]
        sorted_ngrams = sorted(filtered, key=lambda x: x[1], reverse=True)
        return sorted_ngrams[:limit] if limit else sorted_ngrams