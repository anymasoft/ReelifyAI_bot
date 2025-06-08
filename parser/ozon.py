import logging
import re
from bs4 import BeautifulSoup
from urllib.parse import quote
from playwright.async_api import async_playwright
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from config import OZON_SEARCH_URL, MAX_CARDS, PARSER_MODE
from storage.redis import RedisStorage
from typing import Dict, List
import time
import random
import hashlib
import asyncio
from webdriver_manager.microsoft import EdgeChromiumDriverManager

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

class OzonParser:
    def __init__(self):
        self.redis = RedisStorage()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129 Safari",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.cookies = [
            {"name": "__Secure-user-id", "value": "79976617", "domain": "ozon.ru", "path": "/"},
            {"name": "__Secure-ab-group", "value": "41", "domain": "ozon.ru", "path": "/"},
            {"name": "__Secure-refresh-token", "value": "8.789766123.L-gq-B3qSH6mP7umGDwtqA.41.Ad3yVqRwHsuVyefOiBk59XlMZey0iu2POFpLjDTGipdWGeWWBLBF8ecuEpNPEljON1pmGmdh8AX8n1mNFL8Si9-jqmGuKDL3QixyZhAt8wdPEyuswK-EiPFtI7ugHG8xvA.20211029180833.20250601191306.l3Ngi-bWTJSvcjZ1g7v-kdfGBSfeSd5JcT3VjEW0-JQ.192c4f9eaad9baf30", "domain": "ozon.ru", "path": "/"},
            {"name": "guest", "value": "true", "domain": "ozon.ru", "path": "/"},
            {"name": "abt_data", "value": "7.mQrry5HXK64odPL4Wf8zixfQM0BOxIiLbZqW4V9TCeIiNRaA8oNoJu0m-nfCi5RJ70IeGYvqK4SIYpzeOb9MUhrGKD6o3PV9Q7O5vib0t8CmmDuMMBBPM8v-V_7ZUTYrFC0NcQi_Pb49NJfXWnbVzYQ_nKvMdzcIDm3oPLqXzBZ_QN-ikgV8_cxpJUZWJSdE23HJCDHLA0ezK7GJSXidAdpbFgu60Tj8W2FazsD42CUkhXvcLUUuIZVfbZ6CLLXFp99l0mrBv4w_yB3fheqER3Jxv8jVYjc0T6NX1Kb0UdxvRyWq4xPJH-9_9IZho7t77h4w4oFZhyL8H2AfpB8PyfLCKE312ndKoAYLCUX67R0Fd1uUcYZ-Z-0XdQAvoNcPEfxL7r7iXrYc4uFx7L03g6Kuo_-rB_EBW2wIgx2bMoN2aRTCl7GbM2_dN4PPBMKz_ouHASYeMvzTor3O2Br1F9B5XfFg3PRz8tN2TIxQtFJ5Hr2-gkl9_rO4j-_C6_K8Z9BpXzvzFJc3CQ", "domain": "ozon.ru", "path": "/"},
            {"name": "__Secure-ext_xcid", "value": "a0fa506ac4ada48203c1c6725c110eb5", "domain": "ozon.ru", "path": "/"},
            {"name": "__Secure-access-token", "value": "8.79976617.L-gv-B3qSH6mP7umGDwtqA.41.Ad3yVqRwHsuVyefOiBk59XlMZey0iu2POFpLjDTGipdWGeWWBLBF8ecuEpNPEljON1pmGmdh8AX8n1mNFL8Si9-jqmGuKDL3QixyZhAt8wdPEyuswK-EiPFtI7ugHG8xvA.20211029180833.20250601191306.42aKVf6eSzjkZSSt7cgUedKQ07JISQ1oveTEES8i7Qo.1a50554bcc2a4813d", "domain": "ozon.ru", "path": "/"},
            {"name": "__Secure-ETC", "value": "1d21e62218142a7e59cc7da1308d817b", "domain": "ozon.ru", "path": "/"},
            {"name": "xcid", "value": "a0fa506ac4ada48203c1c6725c110eb5", "domain": "ozon.ru", "path": "/"}
        ]

    def clean_text(self, text: str) -> str:
        """Очистка текста от HTML-тегов, спецсимволов и лишних пробелов."""
        text = re.sub(r'<[^>]+>', '', text)  # Удаление HTML-тегов
        text = re.sub(r'[|•●→]', ' ', text)  # Удаление спецсимволов
        text = re.sub(r'\s+', ' ', text)  # Удаление лишних пробелов
        return text.strip()

    async def fetch_page_playwright(self, url: str) -> str | None:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.headers["User-Agent"],
                extra_http_headers=self.headers
            )
            page = await context.new_page()
            try:
                # Логирование куки для дебага
                logger.debug(f"Setting cookies: {self.cookies}")
                # Установка куки и загрузка главной страницы
                await page.goto("https://www.ozon.ru")
                await page.wait_for_timeout(random.uniform(2000, 4000))
                await context.add_cookies(self.cookies)

                # Переход на целевую страницу
                await page.goto(url)
                await page.wait_for_selector(".tile-root", timeout=20000)
                # Прокрутка страницы
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(random.uniform(3000, 5000))
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(random.uniform(3000, 5000))
                html = await page.content()
                # Сохранение HTML для дебага
                with open(f"debug_ozon_search_{int(time.time())}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                if "Antibot Challenge Page" in html:
                    logger.error(f"Antibot page detected for URL: {url}")
                    return None
                return html
            except Exception as e:
                logger.error(f"Error fetching page {url} with Playwright: {str(e)}")
                return None
            finally:
                await browser.close()

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
            time.sleep(random.uniform(2, 4))
            for cookie in self.cookies:
                driver.add_cookie(cookie)
            driver.get(url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".tile-root"))
            )
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(3, 5))
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(3, 5))
            html = driver.page_source
            with open(f"debug_ozon_search_{int(time.time())}.html", "w", encoding="utf-8") as f:
                f.write(html)
            if "Antibot Challenge Page" in html:
                logger.error(f"Antibot page detected for URL: {url}")
                return None
            return html
        except Exception as e:
            logger.error(f"Error fetching page {url} with Selenium: {str(e)}")
            return None
        finally:
            driver.quit()

    async def fetch_product_page(self, url: str, timeout: int = 30000) -> str | None:
        if PARSER_MODE == "playwright":
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    extra_http_headers=self.headers
                )
                page = await context.new_page()
                try:
                    logger.debug(f"Setting cookies for product page: {self.cookies}")
                    await page.goto("https://www.ozon.ru")
                    await page.wait_for_timeout(random.uniform(2000, 4000))
                    await context.add_cookies(self.cookies)

                    await page.goto(url)
                    await page.wait_for_selector("[data-widget='webProductHeading'], [data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']", timeout=timeout)
                    # Прокрутка
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(random.uniform(4000, 6000))
                    await page.evaluate("window.scrollTo(0, 0)")
                    await page.wait_for_timeout(random.uniform(4000, 6000))
                    # Попытка раскрыть описание
                    try:
                        await page.click("[data-auto='showMoreDescription'], .show-more, [data-state*='webShowMore']", timeout=5000)
                        await page.wait_for_timeout(random.uniform(3000, 5000))
                    except:
                        logger.debug(f"No 'Show More' button found for URL: {url}")
                    # Принудительный рендеринг
                    await page.evaluate("window.scrollBy(0, 1); window.scrollBy(0, -1);")
                    await page.wait_for_timeout(random.uniform(2000, 4000))
                    html = await page.content()
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    with open(f"debug_ozon_product_{url_hash}_{int(time.time())}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    soup = BeautifulSoup(html, "html.parser")
                    if not soup.select_one("[data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']"):
                        logger.warning(f"No product description found for URL: {url}")
                    return html
                except Exception as e:
                    logger.error(f"Error fetching product page {url} with Playwright: {str(e)}")
                    return None
                finally:
                    await browser.close()
        else:
            # Резервный вариант с Selenium
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
            try:
                driver.get("https://www.ozon.ru")
                time.sleep(random.uniform(2, 4))
                for cookie in self.cookies:
                    driver.add_cookie(cookie)
                driver.get(url)
                WebDriverWait(driver, timeout // 1000).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-widget='webProductHeading'], [data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']"))
                )
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(4, 6))
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(random.uniform(4, 6))
                try:
                    more_button = driver.find_element(By.CSS_SELECTOR, "[data-auto='showMoreDescription'], .show-more, [data-state*='webShowMore']")
                    ActionChains(driver).move_to_element(more_button).click().perform()
                    time.sleep(random.uniform(3, 5))
                except:
                    logger.debug(f"No 'Show More' button found for URL: {url}")
                driver.execute_script("window.scrollBy(0, 1); window.scrollBy(0, -1);")
                time.sleep(random.uniform(2, 4))
                html = driver.page_source
                url_hash = hashlib.md5(url.encode()).hexdigest()
                with open(f"debug_ozon_product_{url_hash}_{int(time.time())}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                soup = BeautifulSoup(html, "html.parser")
                if not soup.select_one("[data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']"):
                    logger.warning(f"No product description found for URL: {url}")
                return html
            except Exception as e:
                logger.error(f"Error fetching product page {url} with Selenium: {str(e)}")
                return None
            finally:
                driver.quit()

    async def parse_search(self, user_id: int, query: str) -> Dict[str, List[str]]:
        cached = self.redis.get_cache(user_id, query)
        if cached:
            logger.info(f"Cache hit for user {user_id}, query: {query}")
            return cached

        encoded_query = quote(query)
        url = f"{OZON_SEARCH_URL}?text={encoded_query}"

        if PARSER_MODE == "playwright":
            html = await self.fetch_page_playwright(url)
        else:
            html = self.fetch_page_selenium(url)

        if not html:
            logger.error(f"Failed to fetch page for query: {query}")
            return {"error": "Не удалось загрузить страницу"}

        if "Antibot Challenge Page" in html:
            logger.error(f"Antibot page detected for query: {query}")
            return {"error": "Обнаружена страница антибота"}

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(".tile-root")[:MAX_CARDS]
        result = {
            "titles": [],
            "descriptions": [],
            "alt_texts": [],
            "breadcrumbs": [],
            "product_descriptions": []
        }

        max_product_pages = 20
        for i, item in enumerate(items):
            title = item.select_one(".tsBody500Medium, .bq000-a span, .tile-title")
            if title:
                result["titles"].append(self.clean_text(title.text))

            desc = item.select_one(".tsBody400Small, .tsBody500Medium, .tsBodyControl400Small, .tile-info")
            if desc:
                result["descriptions"].append(self.clean_text(desc.text))
            else:
                desc_fallback = item.select_one(".p6b00-a4, .description")
                if desc_fallback:
                    result["descriptions"].append(self.clean_text(desc_fallback.text))

            img = item.select_one("img[src*='ozon.ru'], img.tile-image")
            if img and img.get("alt"):
                result["alt_texts"].append(self.clean_text(img["alt"]))

            if i < max_product_pages:
                product_link = item.select_one("a.tile-hover-target")
                if product_link and product_link.get("href"):
                    product_url = "https://www.ozon.ru" + product_link["href"]
                    product_html = await self.fetch_product_page(product_url)
                    if product_html:
                        product_soup = BeautifulSoup(product_html, "html.parser")
                        product_desc = product_soup.select_one("[data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']")
                        if product_desc:
                            cleaned_desc = self.clean_text(product_desc.text)
                            if cleaned_desc:
                                result["product_descriptions"].append(cleaned_desc)
                            else:
                                logger.warning(f"Empty cleaned description for URL: {product_url}")
                        else:
                            logger.warning(f"No description found for URL: {product_url}")

            breadcrumb = soup.select_one("nav.breadcrumbs, .k0l_24, .breadcrumb, .breadcrumbs-container")
            if breadcrumb:
                result["breadcrumbs"].append(self.clean_text(breadcrumb.text))

        if not any(result.values()):
            logger.warning(f"No data parsed for query: {query}")
            return {"error": "Не удалось извлечь данные"}

        logger.info(f"Parsed {len(items)} items for query: {query}")
        self.redis.set_cache(user_id, query, result)
        return result