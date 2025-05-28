import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

API_TOKEN = 'TOKEN'  # ВАШ ТОКЕН С БОТФАЗЕРА
ADMIN_USER_IDS = {8006053775}  # ID админов
NOTIFICATION_CHAT_ID = '-4983541359'  # ID чата куда будут падать заказы

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

CONFIG_FILE = 'builder_config.json'

class AddLevelState(StatesGroup):
    waiting_for_level_name = State()
    waiting_for_level_message = State()

class EditLevelState(StatesGroup):
    waiting_for_level_name = State()
    waiting_for_level_message = State()

class AddButtonState(StatesGroup):
    waiting_for_level_name = State()
    waiting_for_button_text = State()
    waiting_for_target_level = State()

class AddLinkButtonState(StatesGroup):
    waiting_for_level_name = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()

class DeleteLevelState(StatesGroup):
    waiting_for_level_name = State()

class DeleteButtonState(StatesGroup):
    waiting_for_level_name = State()
    waiting_for_button_index = State()

class AddPaymentButtonState(StatesGroup):
    waiting_for_level_name = State()
    waiting_for_button_text = State()

class ListButtomstate(StatesGroup):
    waiting_for_level_name = State()

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        default = {"levels": {}}
        save_config(default)
        return default

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def is_admin(user_id):
    return user_id in ADMIN_USER_IDS

def build_keyboard(buttons):
    builder = InlineKeyboardBuilder()
    for btn in buttons:
        if 'callback_data' in btn:
            builder.add(InlineKeyboardButton(text=btn['text'], callback_data=btn['callback_data']))
        elif 'url' in btn:
            builder.add(InlineKeyboardButton(text=btn['text'], url=btn['url']))
        builder.adjust(1)
    return builder.as_markup(width=1)

def keyboardadmin():
    buttons = [
        [types.InlineKeyboardButton(text="Добавить уровень", callback_data="add_level")],
        [types.InlineKeyboardButton(text="Изменить уровень", callback_data="edit_level")],
        [types.InlineKeyboardButton(text="Удалить уровень", callback_data="delete_level")],
        [types.InlineKeyboardButton(text="Добавить кнопку", callback_data="add_button")],
        [types.InlineKeyboardButton(text="Добавить кнопку ссылку", callback_data="add_button_with_link")],
        [types.InlineKeyboardButton(text="Добавить кнопку оплаты", callback_data="add_payment_button")],
        [types.InlineKeyboardButton(text="Удалить кнопку", callback_data="delete_button")], 
        [types.InlineKeyboardButton(text="Посмотреть уровни", callback_data="list_levels")], 
        [types.InlineKeyboardButton(text="Посмотреть кнопки", callback_data="list_buttons")], 
        [types.InlineKeyboardButton(text="Помощь", callback_data="help")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

@dp.message(Command(commands=["start"]))
async def user_start(message: types.Message):
    config = load_config()
    levels = config.get('levels', {})
    if not levels:
        await message.answer("Бот еще не настроен. Обратитесь к администратору.")
        return
    first_level_name = next(iter(levels))
    level = levels[first_level_name]
    await message.answer(level['message'], reply_markup=build_keyboard(level.get('buttons', [])))

@dp.message(Command(commands=["inline_mode"]))
async def inline_(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Доступ запрещен.")
        return
    await message.answer("Команды доступные вам", reply_markup=keyboardadmin())

@dp.callback_query(F.data == "add_level")
@dp.message(Command(commands=["add_level"]))
async def add_level_command(update, state: FSMContext):
    message_obj = None

    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return
    await message_obj.answer("Введите название нового уровня:")
    await state.set_state(AddLevelState.waiting_for_level_name)

@dp.message(AddLevelState.waiting_for_level_name)
async def add_level_name(message: types.Message, state: FSMContext):
    level_name = message.text.strip()
    config = load_config()
    if level_name in config['levels']:
        await message.answer("Уровень с таким названием уже существует. Попробуйте другое имя.")
        return
    await state.update_data(level_name=level_name)
    await message.answer("Введите сообщение для этого уровня:")
    await state.set_state(AddLevelState.waiting_for_level_message)

@dp.message(AddLevelState.waiting_for_level_message)
async def add_level_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    level_name = data['level_name']
    level_message = message.text.strip()
    config = load_config()
    config['levels'][level_name] = {"message": level_message, "buttons": []}
    save_config(config)
    await message.answer(f"Уровень '{level_name}' успешно добавлен.")
    await state.clear()

@dp.callback_query(F.data == "edit_level")
@dp.message(Command(commands=["edit_level"]))
async def edit_level_command(update, state: FSMContext):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return
    config = load_config()
    levels = config['levels']
    if not levels:
        await message_obj.answer("Уровней нет.")
        return
    await message_obj.answer("Введите название уровня для редактирования:")
    await state.set_state(EditLevelState.waiting_for_level_name)

@dp.message(EditLevelState.waiting_for_level_name)
async def edit_level_name(message: types.Message, state: FSMContext):
    level_name = message.text.strip()
    config = load_config()
    if level_name not in config['levels']:
        await message.answer("Такого уровня нет.")
        await state.clear()
        return
    await state.update_data(level_name=level_name)
    await message.answer("Введите новое сообщение для уровня:")
    await state.set_state(EditLevelState.waiting_for_level_message)

@dp.message(EditLevelState.waiting_for_level_message)
async def edit_level_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    level_name = data['level_name']
    new_message = message.text.strip()
    config = load_config()
    config['levels'][level_name]['message'] = new_message
    save_config(config)
    await message.answer(f"Уровень '{level_name}' успешно отредактирован.")
    await state.clear()

@dp.callback_query(F.data == "delete_level")
@dp.message(Command(commands=["delete_level"]))
async def delete_level_command(update, state: FSMContext):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return
    config = load_config()
    levels = config['levels']
    if not levels:
        await message_obj.answer("Уровней нет для удаления.")
        return
    await message_obj.answer("Введите название уровня для удаления:")
    await state.set_state(DeleteLevelState.waiting_for_level_name)

@dp.message(DeleteLevelState.waiting_for_level_name)
async def delete_level_name(message: types.Message, state: FSMContext):
    level_name = message.text.strip()
    config = load_config()
    if level_name not in config['levels']:
        await message.answer("Такого уровня нет.")
        await state.clear()
        return
    del config['levels'][level_name]
    save_config(config)
    await message.answer(f"Уровень '{level_name}' и все его кнопки удалены.")
    await state.clear()

@dp.callback_query(F.data == "add_button")
@dp.message(Command(commands=["add_button"]))
async def add_button_command(update, state: FSMContext):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return
    config = load_config()
    if not config['levels']:
        await message_obj.answer("Сначала добавьте уровни.")
        return
    await message_obj.answer("Введите название уровня, к которому хотите добавить кнопку:")
    await state.set_state(AddButtonState.waiting_for_level_name)

@dp.message(AddButtonState.waiting_for_level_name)
async def add_button_level_name(message: types.Message, state: FSMContext):
    level_name = message.text.strip()
    config = load_config()
    if level_name not in config['levels']:
        await message.answer("Уровень не найден.")
        await state.clear()
        return
    await state.update_data(level_name=level_name)
    await message.answer("Введите текст кнопки:")
    await state.set_state(AddButtonState.waiting_for_button_text)

@dp.message(AddButtonState.waiting_for_button_text)
async def add_button_text(message: types.Message, state: FSMContext):
    button_text = message.text.strip()
    await state.update_data(button_text=button_text)

    config = load_config()
    levels = list(config['levels'].keys())
    levels_list = "\n".join(levels)
    await message.answer(f"Введите название уровня, на который будет вести кнопка. Доступные уровни:\n{levels_list}")
    await state.set_state(AddButtonState.waiting_for_target_level)

@dp.message(AddButtonState.waiting_for_target_level)
async def add_button_target_level(message: types.Message, state: FSMContext):
    target_level = message.text.strip()
    config = load_config()
    if target_level not in config['levels']:
        await message.answer("Целевой уровень не найден.")
        await state.clear()
        return

    data = await state.get_data()
    level_name = data['level_name']
    button_text = data['button_text']
    callback_data = f"go_{target_level}"

    config['levels'][level_name]['buttons'].append({
        "text": button_text,
        "callback_data": callback_data
    })
    save_config(config)
    await message.answer(f"Кнопка '{button_text}' добавлена к уровню '{level_name}', ведет на уровень '{target_level}'.")
    await state.clear()

@dp.callback_query(F.data == "add_button_with_link")
@dp.message(Command(commands=["add_button_with_link"]))
async def add_button_with_link_command(update, state: FSMContext):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return
    config = load_config()
    if not config['levels']:
        await message_obj.answer("Сначала добавьте уровни.")
        return
    await message_obj.answer("Введите название уровня, к которому хотите добавить кнопку с ссылкой:")
    await state.set_state(AddLinkButtonState.waiting_for_level_name)

@dp.message(AddLinkButtonState.waiting_for_level_name)
async def add_link_button_level_name(message: types.Message, state: FSMContext):
    level_name = message.text.strip()
    config = load_config()
    if level_name not in config['levels']:
        await message.answer("Уровень не найден.")
        await state.clear()
        return
    await state.update_data(level_name=level_name)
    await message.answer("Введите текст кнопки:")
    await state.set_state(AddLinkButtonState.waiting_for_button_text)

@dp.message(AddLinkButtonState.waiting_for_button_text)
async def add_link_button_text(message: types.Message, state: FSMContext):
    button_text = message.text.strip()
    await state.update_data(button_text=button_text)
    await message.answer("Введите URL для кнопки (должен начинаться с http:// или https://):")
    await state.set_state(AddLinkButtonState.waiting_for_button_url)

@dp.message(AddLinkButtonState.waiting_for_button_url)
async def add_link_button_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("Некорректный URL. Попробуйте ещё раз.")
        return
    
    data = await state.get_data()
    level_name = data['level_name']
    button_text = data['button_text']

    config = load_config()
    config['levels'][level_name]['buttons'].append({
        "text": button_text,
        "url": url
    })
    save_config(config)
    await message.answer(f"Кнопка с ссылкой '{button_text}' добавлена к уровню '{level_name}'.")
    await state.clear()

@dp.callback_query(F.data == "add_payment_button")
@dp.message(Command(commands=["add_payment_button"]))
async def add_payment_button_command(update, state: FSMContext):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return
    config = load_config()
    if not config['levels']:
        await message_obj.answer("Сначала добавьте уровни.")
        return
    await message_obj.answer("Введите название уровня, к которому хотите добавить кнопку оплаты:")
    await state.set_state(AddPaymentButtonState.waiting_for_level_name)

@dp.message(AddPaymentButtonState.waiting_for_level_name)
async def add_payment_button_level_name(message: types.Message, state: FSMContext):
    level_name = message.text.strip()
    config = load_config()
    if level_name not in config['levels']:
        await message.answer("Уровень не найден.")
        await state.clear()
        return
    await state.update_data(level_name=level_name)
    await message.answer("Введите текст кнопки оплаты (например, 'Купить цветы - 200 рублей'):")
    await state.set_state(AddPaymentButtonState.waiting_for_button_text)

@dp.message(AddPaymentButtonState.waiting_for_button_text)
async def add_payment_button_text(message: types.Message, state: FSMContext):
    button_text = message.text.strip()
    data = await state.get_data()
    level_name = data['level_name']

    config = load_config()
    callback_data = f"buy_{button_text}"
    config['levels'][level_name]['buttons'].append({
        "text": button_text,
        "callback_data": callback_data
    })
    save_config(config)
    await message.answer(f"Кнопка оплаты '{button_text}' добавлена к уровню '{level_name}'.")
    await state.clear()
@dp.callback_query(F.data == "help")
@dp.message(Command(commands=["help"]))
async def help_command(update):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return

    help_text = (
        "Доступные команды для администратора:\n\n"
        "/add_level - Добавить новый уровень с сообщением\n"
        "/edit_level - Редактировать сообщение существующего уровня\n"
        "/delete_level - Удалить уровень\n"
        "/add_button - Добавить кнопку перехода между уровнями\n"
        "/add_button_with_link - Добавить кнопку с внешней ссылкой\n"
        "/add_payment_button - Добавить кнопку оплаты\n"
        "/delete_button - Удалить кнопку из уровня\n"
        "/list_levels - Показать список всех уровней\n"
        "/list_buttons - Показать кнопки выбранного уровня\n"
        "/help - Показать это сообщение помощи\n"
        "/inline_mode - Управление с помощью инлайн-кнопок\n"
    )
    await message_obj.answer(help_text)

@dp.callback_query(F.data == "list_levels")
@dp.message(Command(commands=["list_levels"]))
async def list_levels_command(update):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return
    config = load_config()
    levels = config.get('levels', {})
    if not levels:
        await message_obj.answer("Уровней нет.")
        return
    text = "Список уровней:\n"
    for level_name, level in levels.items():
        text += f"- {level_name} (сообщение: {len(level['message'])} символов, кнопок: {len(level.get('buttons', []))})\n"
    await message_obj.answer(text)

@dp.callback_query(F.data == "list_buttons")
@dp.message(Command(commands=["list_buttons"]))
async def list_buttons_command(update, state: FSMContext):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    if not is_admin(update.from_user.id):
        await message_obj.answer("Доступ запрещен.")
        return
    await message_obj.answer("Введите название уровня, чтобы посмотреть его кнопки:")
    await state.set_state(ListButtomstate.waiting_for_level_name)

@dp.message(ListButtomstate.waiting_for_level_name)
async def list_buttons_level_name(message: types.Message, state: FSMContext):
    level_name = message.text.strip()
    config = load_config()
    if level_name not in config['levels']:
        await message.answer("Уровень не найден.")
        await state.clear()
        return
    buttons = config['levels'][level_name].get('buttons', [])
    if not buttons:
        await message.answer(f"В уровне '{level_name}' нет кнопок.")
        await state.clear()
        return
    text = f"Кнопки уровня '{level_name}':\n"
    for i, btn in enumerate(buttons, 1):
        text += f"{i}. {btn['text']} (callback_data: {btn.get('callback_data', 'нет')}, url: {btn.get('url', 'нет')})\n"
    await message.answer(text)
    await state.clear()

@dp.callback_query(F.data == "delete_button")
@dp.message(Command(commands=["delete_button"]))
async def delete_button_command(update, state: FSMContext):
    message_obj = None
    if isinstance(update, types.CallbackQuery):
        message_obj = update.message
    elif isinstance(update, types.Message):
        message_obj = update
    else:
        return
    config = load_config()
    if not config['levels']:
        await message_obj.answer("Уровней нет.")
        return
    await message_obj.answer("Введите название уровня, из которого хотите удалить кнопку:")
    await state.set_state(DeleteButtonState.waiting_for_level_name)

@dp.message(DeleteButtonState.waiting_for_level_name)
async def delete_button_level_name(message: types.Message, state: FSMContext):
    level_name = message.text.strip()
    config = load_config()
    if level_name not in config['levels']:
        await message.answer("Уровень не найден.")
        await state.clear()
        return
    buttons = config['levels'][level_name].get('buttons', [])
    if not buttons:
        await message.answer(f"В уровне '{level_name}' нет кнопок для удаления.")
        await state.clear()
        return
    text = f"Кнопки уровня '{level_name}':\n"
    for i, btn in enumerate(buttons, 1):
        text += f"{i}. {btn['text']} (callback_data: {btn.get('callback_data', 'нет')})\n"
    await message.answer(text)
    await state.update_data(level_name=level_name)
    await message.answer("Введите номер кнопки, которую хотите удалить:")
    await state.set_state(DeleteButtonState.waiting_for_button_index)

@dp.message(DeleteButtonState.waiting_for_button_index)
async def delete_button_index(message: types.Message, state: FSMContext):
    data = await state.get_data()
    level_name = data['level_name']
    try:
        index = int(message.text.strip()) - 1
    except ValueError:
        await message.answer("Введите корректный номер.")
        return
    config = load_config()
    buttons = config['levels'][level_name].get('buttons', [])
    if index < 0 or index >= len(buttons):
        await message.answer("Номер кнопки вне диапазона.")
        return
    removed = buttons.pop(index)
    save_config(config)
    await message.answer(f"Кнопка '{removed['text']}' удалена из уровня '{level_name}'.")
    await state.clear()

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data
    config = load_config()

    if data.startswith("go_"):
        target_level = data[3:]
        level = config['levels'].get(target_level)
        if level:
            await callback.message.edit_text(level['message'], reply_markup=build_keyboard(level.get('buttons', [])))
            await callback.answer()
        else:
            await callback.answer("Уровень не найден.", show_alert=True)

    elif data.startswith("buy_"):
        product_info = data[4:]
        user_id = callback.from_user.id
        username = callback.from_user.username or "Не указано"
        full_name = callback.from_user.full_name
        notification_text = (
            f"Пользователь @{username} (ID: {user_id}, Имя: {full_name}) хочет купить:\n{product_info}"
        )
        await bot.send_message(NOTIFICATION_CHAT_ID, notification_text)
        await callback.answer("Ваш запрос на покупку отправлен администратору.", show_alert=True)

    else:
        await callback.answer("Неизвестная кнопка.", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
