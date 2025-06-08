import logging
from bs4 import BeautifulSoup
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import OZON_SEARCH_URL, MAX_CARDS, PARSER_MODE
from storage.redis import RedisStorage
from typing import Dict, List
import time
import random
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OzonParser:
    def __init__(self):
        self.redis = RedisStorage()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.cookies = [
            {"name": "__Secure-user-id", "value": "79976617", "path": "/"},
            {"name": "__Secure-ab-group", "value": "41", "path": "/"},
            {"name": "__Secure-refresh-token", "value": "8.79976617.L-gv-B3qSH6mP7umGDwtqA.41.Ad3yVqRwHsuVyefOiBk59XlMZey0iu2POFpLjDTGipdWGeWWBLBF8ecuEpNPEljON1pmGmdh8AX8n1mNFL8Si9-jqmGuKDL3QixyZhAt8wdPEyuswK-EiPFtI7ugHG8xvA.20211029180833.20250601191306.l3Ngi-bWTJSvcjZ1g7v-kdfGBSfeSd5JcT3VjEW0-JQ.192c4f9eaad9baf30", "path": "/"},
            {"name": "guest", "value": "true", "path": "/"},
            {"name": "abt_data", "value": "7.mQrry5HXK64odPL4Wf8zixfQM0BOxIiLbZqW4V9TCeIiNRaA8oNoJu0m-nfCi5RJ70IeGYvqK4SIYpzeOb9MUhrGKD6o3PV9Q7O5vibOtj88CmmDuMMBBPM8v-V_7ZUTYrFC0NcQi_Pb49NJfXWnbVzYQ_nKvMdzcIDm3oPLqXzBZ_QN-ikgV8_cxpJUZWJSdE23HJCDHLA0ezK7GJSXidAdpbFgu60Tj8W2FazsD42CUkhXvcLUUuIZVfbZ6CLLXFp99l0mrBv4w_yB3fheqER3Jxv8jVYjc0T6NX1Kb0UdxvRyWq4xPJH-9_9IZho7t77h4w4oFZhyL8H2AfpB8PyfLCKE312ndKoAYLCUX67R0Fd1uUcYZ-Z-0XdQAvoNcPEfxL7r7iXrYc4uFx7L03g6Kuo_-rB_EBW2wIgx2bMoN2aRTCl7GbM2_dN4PPBMKz_ouHASYeMvzTor3O2Br1F9B5XfFg3PRz8tN2TIxQtFJ5Hr2-gkl9_rO4j-_C6_K8Z9BpXzvzFJc3CQ", "path": "/"},
            {"name": "rfuid", "value": "LTE5NTAyNjU0NzAsMTI0LjA0MzQ3NTI3NTE2MDc0LC0xMTI5ODYxNzU3LC0xLDY2MjIyOTUzNSxXM3NpYm1GdFpTSTZJbEJFUmlCV2FXVjNaWElpTENKa1pYTmpjbWx3ZEdsdmJpSTZJbEJ2Y25SaFlteGxJRVJ2WTNWdFpXNTBJRVp2Y20xaGRDSXNJbTFwYldWVWVYQmxjeUk2VzNzaWRIbHdaU0k2SW1Gd2NHeHBZMkYwYVc5dUwzQmtaaUlzSW5OMVptWnBlR1Z6SWpvaWNHUm1JbjBzZXlKMGVYQmxJam9pZEdWNGRDOXdaR1lpTENKemRXZm1hWGhsY3lJNkluQmtaaUo5WFgwc2V5SnVZVzFsSWpvaVEyaHliMjFsSUZCRVJpQldhV1YzWlhJaUxDSmtaWE5qY21sd2RHbHZiaUk2SWxCdmNuUmhZbXhsSUVSdlkzVnRaVzUwSUVadmNtMWhkQ0lzSW0xcGJXVlVlWEJsY3lJNlczc2lkSGx3WlNJNkltRndjR3hwWTJGMGFXOXVMM0JrWmlJc0luTjFabVpwZUdWeklqb2ljR1JtSW4wc2V5SjBlWEJsSWpvaWRHVjRkQzl3WkdZaUxDSnpkV1ptYVhobGN5STZJbkJrWmlKOVhYMHNleUp1WVcxbElqb2lRMmh5YjIxcGRXMGdVRVJHSUZacFpYZGxjaUlzSW1SbGMyTnlhWEIwYVc9dUlqb2lVRzl5ZEdGaWJHVWdSRzlqZFcxbGJuUWdSbTl5YldGMElpd2liV2x0WlZSNWNHVnpJanBiZXlKMGVYQmxJam9pWVhCd2JHbGpZWFJwYjI0dmNHUm1JaXdpYzNWbVptbDRaWE1pT2lKd1pHWWlmU3g3SW5SNWNHVWlPaUowWlhoMEwzQmtaaUlzSW5OMVptWnBlR1Z6SWpvaWNHUm1JbjBzZXlKMGVYQmxJam9pWVhCd2JHbGpZWFJwYjI0dmNHUm1JaXdpYzNWbVptbDRaWE1pT2lKd1pHWWlmU3g3SW5SNWNHVWlPaUowWlhoMEwzQmtaaUlzSW5OMVptWnBlR1Z6SWpvaWNHUm1JbjBkZlN4N0ltNWhiV1VpT2lKTmFXTnliM052Wm5RZ1JXUm5aU0JQUkVZZ1ZtbGxkDlZ5SWl3aVpHVnpZM0pwY0hScGIyNGlPaUpRYjNKMFlXSnNaU0JFYjJOMWJXVnVkQ0JHYjNKdFlYUWlMQ0p0YVcxbFZIbHdaWE1pT2x0N0luUjVjR1VpT2lKaGNIQnNhV05oZEdsdmJpOXdaR1lpTENKemRXZm1hWGhsY3lJNkluQmtaaUo5TEhzaWRIbHdaU0k2SW5SbGVIUXZjR1JtSWl3aWMzVm1abWw0WlhNaU9pSndaR1lpZlYxOUxIc2libUZ0WlNJNklsZGxZa3RwZENCaWRXbHNkQzFwYmlCUVJFWWlMQ0prWlhOamNtbHdkR2x2YmlJNklsQnZjblJoWW14bElFUnZZM1Z0Wlc1MElFWnZjbTFoZENJc0ltMXBiV1ZVZVhCbGN5STZXM3NpZEhsd1pTSTZJbUZ3Y0d4cFkyRjBhVzl1TDNCa1ppSXNJbk4xWm1acGVHVnpJam9pY0dSbUluMHNleUowZVhCbElqb2lkR1Y4ZEM5d1pHWWlMQ0p6ZFdabWFYaGxjeUk2SW5Ca1ppSjlYWDFkLFd5SnlkU0pkLDAsMSwwLDI0LDIzNzQxNTkzMCw4LDIyNzEyNjUyMCwwLDEsMCwtNDkxMjc1TTIzLFIyOXZaMnhsSUVsdVl5NGdUbVYwYzJOaGNHVWdSMlZqYTI4Z1YybHVNeklnTlM0d0lDaFhhVzVrYjNkeklFNVVJREV3TGpBN0lGZHBialkwT3lCNE5qUXBJRUZ3Y0d4bFYyVmlTMmwwTHpVek55NHpOaUFvUzBoVVRVd3NJR3hwYTJVZ1IyVmphMjhwSUVOb2NtOXRaUzh4TXpjdU1DNHdMakFnVTJGbVlYSnBMelV6Tnk0ek5pQkZaR2N2TVRNM0xqQXVNQzR3SURJd01ETXdNVEEzSUUxdmVtbHNiR0U9LGV5SmphSEp2YldVaU9uc2lZWEJ3SWpwN0ltbHpTVzV6ZEdGc2JHVmtJanBtWVd4elpTd2lTVzV6ZEdGc2JGTjBZWFJsSWpwN0lrUkpVMEZDVEVWRUlqb2laR2x6WVdKc1pXUWlMQ0pKVGxOVVFVeE1SVVFpT2lKcGJuTjBZV3hzWldRaUxDSk9UMVJmU1U1VFZFRk1URVZFSWpvaWJtOTBYMmx1YzNSaGJHeGxaQ0o5TENKU2RXNXVhVzVuVTNSaGRHVWlPbnNpUTBGT1RrOVVYMUpWVGlJNkltTmhibTV2ZEY5eWRXNGlMQ0pTUlVGRVdWOVVUMTlTVlU0aU9pSnlaV0ZrZVY5MGIxOXlkVzRpTENKU1ZVNU9TVTXISWpvaWNuVnVibWx1WnlKOWZYMTksNjUsLTEyODU1NTEzLDEsMSwtMSwxNjk5OTU0ODg3LDE2OTk5NTQ4ODcsMzM2MDA3OTMzLDEy", "path": "/"},
            {"name": "__Secure-ext_xcid", "value": "a0fa506ac4ada48203c1c6725c110eb5", "path": "/"},
            {"name": "__Secure-access-token", "value": "8.79976617.L-gv-B3qSH6mP7umGDwtqA.41.Ad3yVqRwHsuVyefOiBk59XlMZey0iu2POFpLjDTGipdWGeWWBLBF8ecuEpNPEljON1pmGmdh8AX8n1mNFL8Si9-jqmGuKDL3QixyZhAt8wdPEyuswK-EiPFtI7ugHG8xvA.20211029180833.20250601191306.42aKVf6eSzjkZSSt7cgUedKQ07JISQ1oveTEES8i7Qo.1a50554bcc2a4813d", "path": "/"},
            {"name": "__Secure-ETC", "value": "1d21e62218142a7e59cc7da1308d817b", "path": "/"},
            {"name": "xcid", "value": "a0fa506ac4ada48203c1c6725c110eb5", "path": "/"}
        ]

    def fetch_page_selenium(self, url: str) -> str | None:
        options = Options()
        options.add_argument("--headless")
        options.add_argument(f"user-agent={self.headers['User-Agent']}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })

        try:
            driver.get("https://www.ozon.ru")
            time.sleep(random.uniform(1, 3))
            # Попробуем без куки для тестирования
            # for cookie in self.cookies:
            #     driver.add_cookie(cookie)
            driver.get(url)
            # Явное ожидание загрузки карточек
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".tile-root"))
            )
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 3))
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 3))
            html = driver.page_source
            # Сохраняем HTML для отладки
            with open(f"debug_ozon_{int(time.time())}.html", "w", encoding="utf-8") as f:
                f.write(html)
            if "Antibot Challenge Page" in html:
                logger.error(f"Antibot page detected for URL: {url}")
                return None
            return html
        except Exception as e:
            logger.error(f"Error fetching page {url}: {str(e)}")
            return None
        finally:
            driver.quit()

    async def parse_search(self, user_id: int, query: str) -> Dict[str, List[str]]:
        # Временно отключим кэширование
        # cached = self.redis.get_cache(user_id, query)
        # if cached:
        #     logger.info(f"Cache hit for user {user_id}, query: {query}")
        #     return cached

        # Build URL
        encoded_query = quote(query)
        url = f"{OZON_SEARCH_URL}?text={encoded_query}"

        # Fetch page
        if PARSER_MODE == "selenium":
            html = self.fetch_page_selenium(url)
        else:
            logger.error(f"Unsupported parser mode: {PARSER_MODE}")
            return {"error": "Неподдерживаемый режим парсинга"}

        if not html:
            logger.error(f"Failed to fetch page for query: {query}")
            return {"error": "Не удалось загрузить страницу"}

        # Check for antibot
        if "Antibot Challenge Page" in html:
            logger.error(f"Antibot page detected for query: {query}")
            return {"error": "Обнаружена страница антибота"}

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(".tile-root")[:MAX_CARDS]
        result = {
            "titles": [],
            "descriptions": [],
            "alt_texts": [],
            "breadcrumbs": []
        }

        for item in items:
            # Title
            title = item.select_one(".bq000-a span.tsBody500Medium")
            if title:
                result["titles"].append(title.text.strip())

            # Description
            desc = item.select_one(".tsBody400Small, .tsBody500Medium")  # Более широкий селектор
            if desc:
                result["descriptions"].append(desc.text.strip())
            else:
                desc_fallback = item.select_one(".p6b00-a4")
                if desc_fallback:
                    result["descriptions"].append(desc_fallback.text.strip())

            # Alt texts
            img = item.select_one("img.r1j_24")
            if img and img.get("alt"):
                result["alt_texts"].append(img["alt"].strip())

            # Breadcrumbs
            breadcrumb = soup.select_one("nav.breadcrumbs, .k0l_24")
            if breadcrumb:
                result["breadcrumbs"].append(breadcrumb.text.strip())

        logger.info(f"Parsed {len(items)} items for query: {query}")
        # Cache result
        self.redis.set_cache(user_id, query, result)
        return result