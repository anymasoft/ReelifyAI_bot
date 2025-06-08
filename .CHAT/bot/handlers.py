import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from .keyboards import get_main_menu, get_analysis_menu, get_history_menu
from config import BOT_TOKEN, DEBUG_MODE, OPENAI_API_KEY
from storage.sqlite import SQLiteStorage
from storage.redis import RedisStorage
from parser.ozon import OzonParser
from analyzer.ngram import NGramAnalyzer
from analyzer.gpt_processor import GPTProcessor
from exporter.txt import TXTExporter

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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
sqlite_storage = SQLiteStorage()
redis_storage = RedisStorage()
ozon_parser = OzonParser()
ngram_analyzer = NGramAnalyzer()
gpt_processor = GPTProcessor(OPENAI_API_KEY)

# Тексты кнопок reply-клавиатуры
BUTTON_TEXTS = ["🔍 Новый анализ", "📊 История", "❓ Помощь", "📬 Обратная связь"]

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"User {message.from_user.id} started bot")
    await message.answer("Привет! Я бот для SEO-анализа карточек Ozon.", reply_markup=get_main_menu())

@dp.message(Command("analyze"))
async def cmd_analyze(message: types.Message):
    user_id = message.from_user.id
    query = message.text.replace("/analyze", "").strip()
    logger.info(f"User {user_id} requested analysis via command: {query}")
    await process_query(message, user_id, query)

@dp.message(F.text.in_(BUTTON_TEXTS))
async def handle_button_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    logger.info(f"User {user_id} pressed button: {text}")
    if text == "🔍 Новый анализ":
        await message.answer("Введите запрос, например: чехол iphone или ссылку на товар Ozon", reply_markup=get_main_menu())
    elif text == "📊 История":
        await cmd_history(message)
    elif text == "❓ Помощь":
        await cmd_help(message)
    elif text == "📬 Обратная связь":
        await cmd_feedback(message)

@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    query = message.text.strip()
    logger.info(f"User {user_id} sent text: {query}")
    if query not in BUTTON_TEXTS:
        await process_query(message, user_id, query)

async def process_query(message: types.Message, user_id: int, query: str):
    logger.info(f"Processing query for user {user_id}: {query}")
    try:
        if not query:
            logger.info(f"User {user_id} sent empty query")
            await message.answer("Введите запрос, например: чехол iphone или ссылку на товар Ozon", reply_markup=get_main_menu())
            return
        if not redis_storage.check_request_limit(user_id):
            logger.warning(f"User {user_id} exceeded request limit")
            await message.answer("Лимит запросов (5/час) исчерпан. Попробуйте позже.", reply_markup=get_main_menu())
            return
        parse_result = await ozon_parser.parse_search(user_id, query)
        logger.info(f"Parse result for user {user_id}: {parse_result}")
        if "error" in parse_result:
            logger.error(f"Parse error for user {user_id}: {parse_result['error']}")
            await message.answer(f"Ошибка: {parse_result['error']}", reply_markup=get_main_menu())
            return
        # Используем GPT для обработки n-грамм
        ngram_result = gpt_processor.process_ngrams(query, parse_result)
        logger.info(f"NGram result for user {user_id}: {ngram_result}")
        # Сохраняем результат в формате, совместимом с текущей логикой
        ngram_formatted = {
            'unigrams': [(item['phrase'], item['count']) for item in ngram_result if len(item['phrase'].split()) == 1],
            'bigrams': [(item['phrase'], item['count']) for item in ngram_result if len(item['phrase'].split()) == 2],
            'trigrams': [(item['phrase'], item['count']) for item in ngram_result if len(item['phrase'].split()) == 3]
        }
        sqlite_storage.add_history(user_id, query, {"parse": parse_result, "ngrams": ngram_formatted})
        await message.answer("Анализ завершён!", reply_markup=get_analysis_menu())
        logger.info(f"Sending keyboard to user {user_id}")
        if DEBUG_MODE:
            logger.debug(f"Debug mode: Sending immediate keyboard to user {user_id}")
            await message.answer("Выберите действие:", reply_markup=get_main_menu())
    except Exception as e:
        logger.error(f"Error in process_query for user {user_id}: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при анализе.", reply_markup=get_main_menu())
        if DEBUG_MODE:
            await message.answer("Выберите действие:", reply_markup=get_main_menu())

@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested history")
    analyses = sqlite_storage.get_history(user_id)
    if not analyses:
        logger.info(f"User {user_id} has empty history")
        await message.answer("История пуста.", reply_markup=get_main_menu())
        return
    formatted_analyses = [(query, timestamp) for query, _, timestamp in analyses]
    await message.answer("Ваши анализы:", reply_markup=get_history_menu(formatted_analyses))

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    logger.info(f"User {message.from_user.id} requested help")
    await message.answer("Используйте /analyze для анализа, /history для просмотра истории.", reply_markup=get_main_menu())

@dp.message(Command("feedback"))
async def cmd_feedback(message: types.Message):
    logger.info(f"User {message.from_user.id} requested feedback")
    await message.answer("Напишите ваш отзыв:", reply_markup=get_main_menu())

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    logger.info(f"User {user_id} clicked callback: {data}")
    try:
        if data.startswith("top_") or data == "all_keys":
            analyses = sqlite_storage.get_history(user_id)
            if not analyses:
                logger.info(f"User {user_id} has empty history for callback")
                await callback.message.answer("История пуста.", reply_markup=get_main_menu())
                return
            latest = analyses[0]
            ngrams = latest[1]["ngrams"]
            limit = 10 if data == "top_10" else 30 if data == "top_30" else None
            keys = ngram_analyzer.get_top_keys(ngrams, limit)
            logger.info(f"Keys for user {user_id}: {keys}")
            if not keys:
                logger.info(f"No keys found for user {user_id}")
                await callback.message.answer("Ключи не найдены.", reply_markup=get_main_menu())
                return
            response = "\n".join(f"{key}: {count}" for key, count in keys)
            if len(response) > 4096:
                logger.warning(f"Response too large for user {user_id}, suggesting TXT download")
                await callback.message.answer("Результат слишком большой, используйте 'Скачать TXT'.", reply_markup=get_main_menu())
            else:
                await callback.message.answer(response, reply_markup=get_main_menu())
        elif data == "download_txt":
            logger.info(f"User {user_id} requested TXT download")
            analyses = sqlite_storage.get_history(user_id)
            if not analyses:
                await callback.message.answer("История пуста.", reply_markup=get_main_menu())
                return
            latest = analyses[0]
            ngrams = latest[1]["ngrams"]
            keys = ngram_analyzer.get_top_keys(ngrams)
            txt_file = TXTExporter.export_to_txt(keys)
            await callback.message.answer_document(txt_file, reply_markup=get_main_menu())
        elif data == "repeat":
            logger.info(f"User {user_id} requested repeat analysis")
            await callback.message.answer("Введите запрос для нового анализа:", reply_markup=get_main_menu())
    except Exception as e:
        logger.error(f"Error in callback for user {user_id}: {str(e)}", exc_info=True)
        await callback.message.answer("Произошла ошибка.", reply_markup=get_main_menu())
    await callback.answer()