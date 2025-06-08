from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    buttons = [
        [KeyboardButton(text="🔍 Новый анализ"), KeyboardButton(text="📊 История")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="🔍 Скрыть ключ")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Введите запрос или выберите действие"
    )

def get_analysis_menu():
    buttons = [
        [InlineKeyboardButton(text="🔝 Топ-10 ключей", callback_data="top_10")],
        [InlineKeyboardButton(text="🔝 Топ-30 ключей", callback_data="top_30")],
        [InlineKeyboardButton(text="📄 Все ключи", callback_data="all_keys")],
        [InlineKeyboardButton(text="📥 Скачать TXT", callback_data="download_txt")],
        [InlineKeyboardButton(text="🔄 Повторить анализ", callback_data="repeat")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_history_menu(analyses):
    buttons = [
        [InlineKeyboardButton(text=f"📄 Анализ #{i} ({timestamp.strftime('%d.%m.%y %H:%M')})", callback_data=f"history_{i}")]
        for i, (query, timestamp) in enumerate(analyses, 1)
    ]
    buttons.append([InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_history")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)