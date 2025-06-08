import nltk
import re
from nltk.tokenize import word_tokenize
from nltk.util import ngrams
from collections import Counter
from typing import Dict, List, Tuple
from analyzer.stopwords import StopWords

class NGramAnalyzer:
    def __init__(self):
        nltk.download('punkt', quiet=True)
        self.stopwords = StopWords()
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
            'mini': 'mini'
        }
        self.technical_codes = re.compile(r'^[a-z0-9_/]+$|^[a-z0-9]+/[a-z]$')

    def tokenize(self, text: str, query_tokens: set = None) -> List[str]:
        text = re.sub(r'[><.,:;!?()"\\/]|\b\d+\b|\b\w*_\w*\b|\s+', ' ', text)
        tokens = word_tokenize(text.lower(), language='russian')
        tokens = [self.term_mapping.get(token, token) for token in tokens]
        filtered_tokens = [
            token for token in self.stopwords.filter(tokens)
            if any(c.isalpha() for c in token) and
               len(token) > 2 and
               not token.isdigit() and
               not self.technical_codes.match(token)
        ]
        # Приоритизация токенов, связанных с запросом
        if query_tokens:
            filtered_tokens = [
                token for token in filtered_tokens
                if token in query_tokens or any(q in token for q in query_tokens)
            ] + [token for token in filtered_tokens if token not in query_tokens]
        return filtered_tokens

    def extract_ngrams(self, texts: List[str], n: int, query_tokens: set = None) -> List[Tuple[str, int]]:
        all_ngrams = []
        for text in texts:
            tokens = self.tokenize(text, query_tokens)
            if len(tokens) >= n:
                n_grams = [' '.join(gram) for gram in ngrams(tokens, n) if len(set(gram)) == len(gram)]
                # Фильтрация n-грамм: должны содержать хотя бы один токен запроса
                if query_tokens:
                    n_grams = [gram for gram in n_grams if any(q in gram for q in query_tokens)]
                all_ngrams.extend(n_grams)
        return Counter(all_ngrams).most_common()

    def analyze(self, data: Dict[str, List[str]], query: str = '') -> Dict[str, List[Tuple[str, int]]]:
        texts = (
            data.get('titles', []) +
            data.get('descriptions', []) +
            data.get('alt_texts', []) +
            data.get('breadcrumbs', [])
        )
        # Токены запроса
        query_tokens = set(self.tokenize(query)) if query else set()
        result = {
            'unigrams': self.extract_ngrams(texts, 1, query_tokens),
            'bigrams': self.extract_ngrams(texts, 2, query_tokens),
            'trigrams': self.extract_ngrams(texts, 3, query_tokens)
        }
        return result

    def get_top_keys(self, ngrams: Dict[str, List[Tuple[str, int]]], limit: int = None) -> List[Tuple[str, int]]:
        combined = (
            ngrams['unigrams'] +
            ngrams['bigrams'] +
            ngrams['trigrams']
        )
        sorted_ngrams = sorted(combined, key=lambda x: x[1], reverse=True)
        return sorted_ngrams[:limit] if limit else sorted_ngrams