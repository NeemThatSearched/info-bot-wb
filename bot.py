import json
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import *
import logging

# Загрузка данных из JSON
with open('buttons.json', 'r', encoding='utf-8') as f:
    buttons_data = json.load(f)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

class CashbackStates(StatesGroup):
    waiting_for_photos = State()

photo_message_ids = {}

# Функция для создания главного меню
def main_menu():
    markup = InlineKeyboardMarkup()
    for key, value in buttons_data['main'].items():
        if key != 'text':
            markup.add(InlineKeyboardButton(text=value, callback_data=key))
    return markup

# Обработчик для inline кнопок
@dp.callback_query_handler(lambda c: c.data in buttons_data)
async def process_callback_button(callback_query: types.CallbackQuery, state: FSMContext):
    code = callback_query.data
    await bot.answer_callback_query(callback_query.id)
    markup = InlineKeyboardMarkup()
    # Создание подменю
    if code == 'link' or code =='support':
        url = CHANEL_LINK if code == 'link' else MANAGER_LINK
        markup.add(InlineKeyboardButton(text=buttons_data[code][code], url=url))
        markup.add(InlineKeyboardButton(text=buttons_data['return'], callback_data='main'))
        text=buttons_data[code]['text']
    elif code == 'main':
        username = callback_query.from_user.username or "пользователь"
        text = buttons_data['main']['text'].format(username=username)
        markup == InlineKeyboardMarkup()
        for key, value in buttons_data['main'].items():
            if key != 'text':
                markup.add(InlineKeyboardButton(text=value, callback_data=key))
    elif code == 'cashback':
        # Отправка фотографий
        media = [
            InputMediaPhoto(open('media/photo1.jpeg', 'rb'))
        ]
        sent_media = await bot.send_media_group(chat_id=callback_query.from_user.id, media=media)
        
        # Сохранение идентификаторов сообщений
        photo_message_ids[callback_query.from_user.id] = [msg.message_id for msg in sent_media]

        markup.add(InlineKeyboardButton(text=buttons_data['return'], callback_data='delete_photos'))
        text = buttons_data[code]['text']
        # Установка состояния ожидания фотографий
        await CashbackStates.waiting_for_photos.set()
    elif code == 'delete_photos':
        user_id = callback_query.from_user.id
        try:
            if user_id in photo_message_ids:
                for message_id in photo_message_ids[user_id]:
                    await bot.delete_message(chat_id=user_id, message_id=message_id)
                del photo_message_ids[user_id]
        except Exception as e:
            print(e)

        # Возврат в главное меню
        current_state = await state.get_state()
        if current_state is not None:
            await state.finish()
        username = callback_query.from_user.username or "пользователь"
        text = buttons_data['main']['text'].format(username=username)
        for key, value in buttons_data['main'].items():
            if key != 'text':
                markup.add(InlineKeyboardButton(text=value, callback_data=key))
    else:
        print(f'\n\n\n\n\n\n\n{code}\n\n\n\n\n\n')
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=buttons_data['return'], callback_data='main'))
        text=buttons_data[code]['text']
    await bot.edit_message_text(
        text=text,
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=markup
    )

# Обработчик для получения фотографий
@dp.message_handler(state=CashbackStates.waiting_for_photos, content_types=types.ContentType.PHOTO)
async def handle_photos(message: types.Message, state: FSMContext):
    largest_photo = message.photo[-1]  # Выбираем самое большое фото
    await bot.send_photo(chat_id=CASHBACK_MANAGER, photo=largest_photo.file_id, caption=f'@{message.from_user.username}')
    # Завершение состояния
    await state.finish()
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=buttons_data['return'], callback_data='main'))
    await message.reply("Ваши фотографии были отправлены менеджеру.", reply_markup=markup)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    username = message.from_user.username or "пользователь"
    text = buttons_data['main']['text'].format(username=username)
    await message.reply(text, reply_markup=main_menu())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)