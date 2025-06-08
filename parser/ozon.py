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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.ozon.com/",
        }
        self.cookies = [
            {
                "name": "__Secure-user-id",
                "value": "79976617",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "Lax",
                "httpOnly": True,
                "secure": True,
                "expires": 1780928785
            },
            {
                "name": "__Secure-ab-group",
                "value": "41",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "Lax",
                "httpOnly": False,
                "secure": True,
                "expires": 1780928785
            },
            {
                "name": "__Secure-refresh-token",
                "value": "8.79976617.L-gv-B3qSH6mP7umGDwtqA.41.AZY-nBSLXgF6ullbjYgcsX9x774GwSJK3oqP2utKpoV0z8LDeFAfAtOKkf2X-m5LaWEsSAk6DPWIu58xFbaDFcsF7MALB9uCwiHHNsy0Cw-8egc3IyuSG8mQ2ple6zi7Ig.20211029180833.20250608162623.XaoJg3VwlSVn2fIeBJmnkjjbm0VnKjOVSYG-NEmkM3g.1bcb02488bc602bae",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "Lax",
                "httpOnly": True,
                "secure": True,
                "expires": 1780928785
            },
            {
                "name": "guest",
                "value": "true",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "None",
                "httpOnly": False,
                "secure": False
            },
            {
                "name": "abt_data",
                "value": "7.X4zhVlIv1_rxcAKXHLQRWC_i0yIo7BqnSYdCym1uxRQ4RhCC-AnS8OUShekV-MZ4Uum89o2-O9FaldvAuk7NuD5vNb464r-ZtI6ni3QYfKUMQcITkKws9OGiVvHJahxpDcLNu9ZWSnwqnVD6NlkoJ-PB8661YJ8wT7E4FCq6XwtVRB9SZYfXx_zSLVUnBDOho8ZNZ9ofzEjnzE_yv_vFCIlSt14pRfuaF5z8-t0Rou-so4kZwLRo1vxzY2fslg7BJD-Os99SX7RehPzAeFDDs63momD4jVZrhipTX2nDpC8bp03JDx2wWCi2vaG1OzSgRSteuQXDyFOuum2bb_JtCnUeaHP_ZKizJk3fqJgMgiagHiC-4qtMSQ5CaqSXC-xIFrbQS5XwZAFw08IWQiNrlXsKYZPEQt4IX5O1R9c74lzSnZPxDKpYW6AVecd46jvDnJwrFk_NVbm86lF5vrBGHB3I-FLbbt2NA5ziRxjYRvHN66FZ7e463JZvLPraY4LNNDxIcIvEEh9KY1YxsdYlnQdBxlVnQ2ix8-PqWdkTCeBh9GUGzWIvZ6IQxih3-zVK4lQjY7r3",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "None",
                "httpOnly": True,
                "secure": True,
                "expires": 1780887119
            },
            {
                "name": "__Secure-ext_xcid",
                "value": "a0fa506ac4ada48203c1c6725c110eb5",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "None",
                "httpOnly": True,
                "secure": True,
                "expires": 1780332055
            },
            {
                "name": "__Secure-access-token",
                "value": "8.79976617.L-gv-B3qSH6mP7umGDwtqA.41.AZY-nBSLXgF6ullbjYgcsX9x774GwSJK3oqP2utKpoV0z8LDeFAfAtOKkf2X-m5LaWEsSAk6DPWIu58xFbaDFcsF7MALB9uCwiHHNsy0Cw-8egc3IyuSG8mQ2ple6zi7Ig.20211029180833.20250608162623.e1eFXbwIjxYn42IoAk4bDYG5Ox8wFBCsWG8lNnbpy9U.1dd89bd79fd2d8baf",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "Lax",
                "httpOnly": True,
                "secure": True,
                "expires": 1780928785
            },
            {
                "name": "__Secure-ETC",
                "value": "1d21e62218142a7e59cc7da1308d817b",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "None",
                "httpOnly": True,
                "secure": True,
                "expires": 1780887117
            },
            {
                "name": "xcid",
                "value": "a0fa506ac4ada48203c1c6725c110eb5",
                "domain": ".ozon.com",
                "path": "/",
                "sameSite": "None",
                "httpOnly": False,
                "secure": False
            }
        ]

    def fix_cookie_samesite(self, cookie: dict) -> dict:
        """Исправление значения sameSite для совместимости с Playwright."""
        if 'sameSite' in cookie:
            val = cookie['sameSite'].lower()
            if val == 'lax':
                cookie['sameSite'] = 'Lax'
            elif val == 'strict':
                cookie['sameSite'] = 'Strict'
            elif val == 'none':
                cookie['sameSite'] = 'None'
        # Удаление expires для сессионных куки
        if cookie.get('expires', 0) == -1:
            cookie.pop('expires', None)
        return cookie

    def clean_text(self, text: str) -> str:
        """Очистка текста от HTML-тегов, спецсимволов и лишних пробелов."""
        text = re.sub(r'<[^>]+>', '', text)  # Удаление HTML-тегов
        text = re.sub(r'[|•●→]', ' ', text)  # Удаление спецсимволов
        text = re.sub(r'\s+', ' ', text)  # Удаление лишних пробелов
        return text.strip()

    async def fetch_page_playwright(self, url: str) -> str | None:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Для отладки
            context = await browser.new_context(
                user_agent=self.headers["User-Agent"],
                extra_http_headers=self.headers
            )
            page = await context.new_page()
            try:
                fixed_cookies = [self.fix_cookie_samesite(c) for c in self.cookies]
                logger.debug(f"Setting cookies: {[c['name'] for c in fixed_cookies]}")
                await page.goto("https://www.ozon.com", timeout=30000, wait_until='networkidle')
                await page.wait_for_timeout(random.uniform(2000, 4000))
                await context.add_cookies(fixed_cookies)

                await page.goto(url, timeout=30000, wait_until='networkidle')
                # Проверка селекторов
                selectors = [
                    ".tile-root",
                    "[data-widget='searchResultsV2']"
                ]
                for selector in selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=30000)
                        logger.debug(f"Found selector: {selector}")
                        break
                    except:
                        logger.debug(f"Selector {selector} not found, trying next")
                else:
                    raise Exception("No valid selector found for search results")

                # Прокрутка для полной загрузки
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(random.uniform(3000, 5000))
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(random.uniform(3000, 5000))
                html = await page.content()
                timestamp = int(time.time())
                with open(f"debug_ozon_search_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                if "Antibot Challenge Page" in html:
                    logger.error(f"Antibot page detected for URL: {url}")
                    return None
                return html
            except Exception as e:
                timestamp = int(time.time())
                await page.screenshot(path=f"ozon_error_{timestamp}.png", full_page=True)
                html = await page.content()
                with open(f"ozon_error_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(html)
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
            driver.get("https://www.ozon.com")
            time.sleep(random.uniform(2, 4))
            for cookie in self.cookies:
                selenium_cookie = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie["path"],
                    "httpOnly": cookie.get("httpOnly", False),
                    "secure": cookie.get("secure", False),
                }
                if cookie.get("expires", -1) > 0:
                    selenium_cookie["expiry"] = int(cookie["expires"])
                driver.add_cookie(selenium_cookie)
            driver.get(url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_any_elements_located((
                    By.CSS_SELECTOR, ".tile-root, [data-widget='searchResultsV2']"
                ))
            )
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(3, 5))
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(3, 5))
            html = driver.page_source
            timestamp = int(time.time())
            with open(f"debug_ozon_search_{timestamp}.html", "w", encoding="utf-8") as f:
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
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    extra_http_headers=self.headers
                )
                page = await context.new_page()
                try:
                    fixed_cookies = [self.fix_cookie_samesite(c) for c in self.cookies]
                    logger.debug(f"Fetching product page with cookies: {[c['name'] for c in fixed_cookies]}")
                    await page.goto("https://www.ozon.com", timeout=timeout, wait_until='networkidle')
                    await page.wait_for_timeout(random.uniform(2, 4))
                    await context.add_cookies(fixed_cookies)

                    await page.goto(url, timeout=timeout, wait_until='networkidle')
                    await page.wait_for_selector(
                        "[data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']",
                        timeout=timeout
                    )
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(random.uniform(2, 4))
                    await page.evaluate("window.scrollTo(0, 0)")
                    await page.wait_for_timeout(random.uniform(2, 4))
                    try:
                        await page.click("[data-auto='showMoreDescription'], .show-moreButton, [data-state='webShowMoreButton']", timeout=5000)
                        await page.wait_for_timeout(3000)
                    except:
                        logger.debug(f"No 'Show More' button found for: {url}")
                    await page.evaluate("window.scrollBy(0, 1); window.scrollBy(0, -1);")
                    await page.wait_for_timeout(random.uniform(2, 4))
                    html = await page.content()
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    timestamp = int(time.time())
                    with open(f"debug_ozon_product_{url_hash}_{timestamp}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    soup = BeautifulSoup(html, "html.parser")
                    if not soup.select_one("[data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .webProductDescription"):
                        logger.warning(f"No product description found for: {url}")
                    return html
                except Exception as e:
                    timestamp = int(time.time())
                    await page.screenshot(path=f"product_error_{timestamp}.png", full_page=True)
                    html = await page.content()
                    with open(f"product_error_{timestamp}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    logger.error(f"Error fetching product page {url} with Playwright: {str(e)}")
                    return None
                finally:
                    await browser.close()
        else:
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
                driver.get("https://www.ozon.com")
                time.sleep(random.uniform(2, 4))
                for cookie in self.cookies:
                    selenium_cookie = {
                        "name": cookie["name"],
                        "value": cookie["value"],
                        "domain": cookie["domain"],
                        "path": cookie["path"],
                        "httpOnly": cookie.get("httpOnly", False),
                        "secure": cookie.get("secure", False),
                    }
                    if cookie.get("expires", -1) > 0:
                        selenium_cookie["expiry"] = int(cookie["expires"])
                    driver.add_cookie(selenium_cookie)
                driver.get(url)
                WebDriverWait(driver, timeout // 1000).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']"))
                )
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 4))
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(random.uniform(2, 4))
                try:
                    more_button = driver.find_element(By.CSS_SELECTOR, "[data-auto='showMoreDescription'], .show-moreButton, [data-state='webShowMoreButton']")
                    ActionChains(driver).move_to_element(more_button).click().perform()
                    time.sleep(3)
                except:
                    logger.debug(f"No 'Show More' button found for: {url}")
                driver.execute_script("window.scrollBy(0, 1); window.scrollBy(0, -1);")
                time.sleep(random.uniform(2, 4))
                html = driver.page_source
                url_hash = hashlib.md5(url.encode()).hexdigest()
                timestamp = int(time.time())
                with open(f"debug_ozon_product_{url_hash}_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                soup = BeautifulSoup(html, "html.parser")
                if not soup.select_one("[data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']"):
                    logger.warning(f"No product description found for: {url}")
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
            return {"error": "Обнаружена страница антибот-защиты"}

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
            title = item.select_one(".tsBody500Medium")
            if title:
                result["titles"].append(self.clean_text(title.text))

            desc = item.select_one(".p6b00-a4, .c301-a1")
            if desc:
                result["descriptions"].append(self.clean_text(desc.text))

            img = item.select_one("img[src*='ozon.com']")
            if img and img.get("alt"):
                result["alt_texts"].append(self.clean_text(img.get("alt")))

            if i < max_product_pages:
                product_link = item.select_one("a[href^='/product/']")
                if product_link and product_link.get("href"):
                    product_url = "https://www.ozon.com" + product_link["href"]
                    product_html = await self.fetch_product_page(product_url)
                    if product_html:
                        product_soup = BeautifulSoup(product_html, "html.parser")
                        product_desc = product_soup.select_one("[data-widget='webCharacteristics'], .tsBody500Medium, .webDescription, .pdp-description-text, .pdp-details, .tsBodyM, .tsBodyL, [data-auto='description'], .product-description, .description-container, [data-widget='webProductDescription']")
                        if product_desc:
                            cleaned_desc = self.clean_text(product_desc.text)
                            if cleaned_desc:
                                result["product_descriptions"].append(cleaned_desc)
                            else:
                                logger.debug(f"Empty cleaned description for {product_url}")
                        else:
                            logger.debug(f"No description found for {product_url}")

            breadcrumb = soup.select_one("nav.breadcrumbs, .nav_24, .breadcrumb, .breadcrumbs-wrapper")
            if breadcrumb:
                result["breadcrumbs"].append(self.clean_text(breadcrumb.text))

        if not any(result.values()):
            logger.warning(f"No data parsed for query: {query}")
            return {"error": "Не удалось извлечь данные"}

        logger.info(f"Parsed {len(items)} items for query: {query}")
        self.redis.set_cache(user_id, query, result)
        return result