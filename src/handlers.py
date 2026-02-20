import asyncio
import logging
import json
from aiogram import Dispatcher, Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config
from database import (
    StaticProfile, get_user, create_user, get_all_users,
    create_static_profile, get_static_profiles, 
    User, Session, get_user_stats as db_user_stats,
)
from functions import (
    create_vless_profile, delete_client_by_email, generate_vless_url,
    get_user_stats, create_static_client, get_global_stats,
    get_online_users_count, check_if_user_chat_member, get_chat_name,
)

logger = logging.getLogger(__name__)

router = Router()

MAX_MESSAGE_LENGTH = 4096

class AdminStates(StatesGroup):
    CREATE_STATIC_PROFILE = State()
    SEND_MESSAGE = State()
    SEND_MESSAGE_TARGET = State()

def split_text(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list:
    """Разбивает текст на части указанной максимальной длины"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        part = text[:max_length]
        last_newline = part.rfind('\n')
        if last_newline != -1:
            part = part[:last_newline]
        parts.append(part)
        text = text[len(part):].lstrip()
    return parts

async def show_menu(bot: Bot, chat_id: int, message_id: int = None):
    """Функция для отображения меню (может как редактировать существующее сообщение, так и отправлять новое)"""
    user = await get_user(chat_id)
    if not user:
        return
    
    text = (
        f"**Имя профиля**: `{user.full_name}`\n"
        f"**Id**: `{user.telegram_id}`\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подключить", callback_data="connect")
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.button(text="ℹ️ Помощь", callback_data="help")
    
    if user.is_admin:
        builder.button(text="⚠️ Админ. меню", callback_data="admin_menu")
    
    builder.adjust(2, 2, 1)
    
    if message_id:
        # Редактируем существующее сообщение
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode='Markdown'
        )
    else:
        # Отправляем новое сообщение
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode='Markdown'
        )

def update_user_data(message: Message, user: User, update_data: dict) -> None:
    """
    Update user data in the database.
    
    This function updates the specified fields of a user record in the database
    and commits the changes. It's used to keep user information synchronized
    with their current Telegram profile data.
    
    Args:
        message: The Telegram message object containing user information
        user: The User database object to update
        update_data: Dictionary containing field names as keys and new values as values.
                     Valid fields include: full_name, username, telegram_id, etc.
    
    Returns:
        None
        
    Note:
        The function logs the update operation for debugging purposes.
        Only fields that exist in the User model can be updated.
    """
    with Session() as session:
        db_user = session.query(User).get(user.id)
        for key, value in update_data.items():
            setattr(db_user, key, value)
        session.commit()
        logger.info(f"🔄 Updated user data: {message.from_user.id}")

@router.message(Command("start"))
async def start_cmd(message: Message, bot: Bot):
    logger.info(f"ℹ️ Start command from {message.from_user.id}")
    is_user_chat_member = await check_if_user_chat_member(message.from_user.id, bot)

    if is_user_chat_member:
        user = await get_user(message.from_user.id)
        
        # Обновляем данные пользователя, если они изменились
        update_data = {}
        if user:
            if user.full_name != message.from_user.full_name:
                update_data["full_name"] = message.from_user.full_name
            if user.username != message.from_user.username:
                update_data["username"] = message.from_user.username
            if user.chat_member != is_user_chat_member:
                update_data["chat_member"] = is_user_chat_member
        else:
            is_admin = message.from_user.id in config.ADMINS
            user = await create_user(
                telegram_id=message.from_user.id, 
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                chat_member=is_user_chat_member,
                is_admin=is_admin
            )
            await message.answer(f"Добро пожаловать в VPN бота `{(await bot.get_me()).full_name}`!", parse_mode='Markdown')
            await asyncio.sleep(2)
    
        # Обновляем данные, если есть изменения
        if update_data:
            update_user_data(message, user, update_data)
        
        await show_menu(bot, message.from_user.id)
    else:
        await message.answer("Сервис недоступен.")
        logger.info(f"🛑 Denied access to {message.from_user.id}")

@router.message(Command("menu"))
async def menu_cmd(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user:
        await start_cmd(message, bot)
        return
    
    is_user_chat_member = await check_if_user_chat_member(message.from_user.id, bot)

    # Проверяем изменения данных
    update_data = {}
    if user.full_name != message.from_user.full_name:
        update_data["full_name"] = message.from_user.full_name
    if user.username != message.from_user.username:
        update_data["username"] = message.from_user.username
    if user.chat_member != is_user_chat_member:
        update_data["chat_member"] = is_user_chat_member
    
    # Обновляем данные если есть изменения
    if update_data:
        update_user_data(message, user, update_data)
    
    if is_user_chat_member:
        await show_menu(bot, message.from_user.id)
    else:
        await message.answer("Сервис недоступен.")
        logger.info(f"🛑 Denied access to {message.from_user.id}")

@router.callback_query(F.data == "help")
async def help_msg(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    chat_name = await get_chat_name(bot, config.CHAT_ID)
    text = f"Об ошибках в работе бота пиши в чат `{chat_name}`"
    await callback.message.answer(text, parse_mode='Markdown', reply_markup=builder.as_markup())

@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.is_admin:
        await callback.answer("🛑 Доступ запрещен!")
        return
    
    _, chat_members_count, strangers_count = await db_user_stats()
    online_users_count = await get_online_users_count()
    
    text = (
        "**Административное меню**\n\n"
        f"**Пользователей онлайн (по всем inbounds)**: `{online_users_count}`\n"
        f"**В чате / изгои**: `{chat_members_count}` / `{strangers_count}`\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Список пользователей", callback_data="admin_user_list")
    builder.button(text="📊 Статистика исп. сети", callback_data="admin_network_stats")
    builder.button(text="📢 Рассылка", callback_data="admin_send_message")
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    builder.adjust(2, 1, 1, 1, 1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode='Markdown')

# Обработчики для вывода списка пользователей
@router.callback_query(F.data == "admin_user_list")
async def admin_user_list(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Члены чата", callback_data="user_list_chat_members")
    builder.button(text="🛑 Изгои", callback_data="user_list_not_chat_members")
    builder.button(text="⏱️ Статические профили", callback_data="static_profiles_menu")
    builder.button(text="⬅️ Назад", callback_data="admin_menu")
    builder.adjust(1, 1, 1)
    await callback.message.edit_text("**Выберите фильтр**", reply_markup=builder.as_markup(), parse_mode='Markdown')

@router.callback_query(F.data == "user_list_chat_members")
async def handle_user_list_chat_members(callback: CallbackQuery, bot: Bot):
    """
    Показать список участников чата.
    Перед выводом список синхронизируется с реальным состоянием чата:
    пользователи, вышедшие из чата, помечаются как chat_member = False.
    """
    # Берем текущий список отмеченных как участники
    users = await get_all_users(chat_member=True)
    if not users:
        await callback.answer("Нет членов чата")
        return

    # Синхронизируем флаг chat_member с реальным статусом в Telegram
    has_changes = False
    with Session() as session:
        for user in users:
            is_member = await check_if_user_chat_member(user.telegram_id, bot)
            if not is_member:
                db_user = session.query(User).get(user.id)
                if db_user and db_user.chat_member:
                    db_user.chat_member = False
                    has_changes = True
        if has_changes:
            session.commit()

    # Повторно запрашиваем только тех, кто действительно остается участником
    users = await get_all_users(chat_member=True)
    if not users:
        await callback.answer("Нет членов чата")
        return

    text = "👤 <b>Члены чата:</b>\n\n"
    for user in users:
        username = f"@{user.username}" if user.username else "none"
        user_line = f"• {user.full_name} ({username} | <code>{user.telegram_id}</code>)\n"

        # Если текст становится слишком длинным, отправляем текущую часть и начинаем новую
        if len(text) + len(user_line) > MAX_MESSAGE_LENGTH:
            await callback.message.answer(text, parse_mode="HTML")
            text = "👤 <b>Члены чата (продолжение):</b>\n\n"

        text += user_line

    # Отправляем оставшуюся часть текста
    await callback.message.answer(text, parse_mode="HTML")

@router.callback_query(F.data == "user_list_not_chat_members")
async def handle_user_list_not_chat_members(callback: CallbackQuery):
    users = await get_all_users(chat_member=False)
    if not users:
        await callback.answer("Нет изгоев")
        return
    
    text = "👤 <b>Изгои:</b>\n\n"
    for user in users:
        username = f"@{user.username}" if user.username else "none"
        user_line = f"• {user.full_name} ({username} | <code>{user.telegram_id}</code>)\n"
        
        # Если текст становится слишком длинным, отправляем текущую часть и начинаем новую
        if len(text) + len(user_line) > MAX_MESSAGE_LENGTH:
            await callback.message.answer(text, parse_mode="HTML")
            text = "👤 <b>Изгои (продолжение):</b>\n\n"
        
        text += user_line
    
    # Отправляем оставшуюся часть текста
    await callback.message.answer(text, parse_mode="HTML")

# Обработчики для рассылки сообщений
@router.callback_query(F.data == "admin_send_message")
async def admin_send_message_start(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Членам чата", callback_data="target_chat_members")
    builder.button(text="🛑 Изгоям", callback_data="target_not_chat_members")
    builder.button(text="👥 Всем пользователям", callback_data="target_all")
    builder.button(text="↩️ Назад", callback_data="admin_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "Выберите целевую аудиторию для рассылки",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("target_"))
async def admin_send_message_target(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Снимаем анимацию
    target = callback.data.split("_")[1]
    await state.update_data(target=target)
    await callback.message.answer("Введите сообщение для рассылки")
    await state.set_state(AdminStates.SEND_MESSAGE)

@router.message(AdminStates.SEND_MESSAGE)
async def admin_send_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target = data['target']
    text = message.text
    
    users = []
    if target == "chat_members":
        users = await get_all_users(chat_member=True)
    elif target == "not_chat_memebers":
        users = await get_all_users(chat_member=False)
    else:  # all
        users = await get_all_users()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(user.telegram_id, text)
            success += 1
        except Exception as e:
            logger.error(f"🛑 Ошибка отправки сообщения {user.telegram_id}: {e}")
            failed += 1
    
    await message.answer(
        f"📨 Результаты рассылки:\n\n"
        f"• Успешно: {success}\n"
        f"• Не удалось: {failed}\n"
        f"• Всего: {len(users)}"
    )
    await state.clear()

# Остальные обработчики остаются без изменений
@router.callback_query(F.data == "static_profiles_menu")
async def static_profiles_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 Добавить статический профиль", callback_data="static_profile_add")
    builder.button(text="📋 Вывести статические профили", callback_data="static_profile_list")
    builder.button(text="⬅️ Назад", callback_data="admin_user_list")
    builder.adjust(1)
    await callback.message.edit_text("**Выберите действие**", reply_markup=builder.as_markup(), parse_mode='Markdown')

@router.callback_query(F.data == "static_profile_add")
async def static_profile_add(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Снимаем анимацию
    await callback.message.answer("Введите имя для статического профиля")
    await state.set_state(AdminStates.CREATE_STATIC_PROFILE)

@router.message(AdminStates.CREATE_STATIC_PROFILE)
async def process_static_profile_name(message: Message, state: FSMContext):
    profile_name = message.text
    profile_data = await create_static_client(profile_name)
    
    if profile_data:
        vless_url = generate_vless_url(profile_data)
        await create_static_profile(profile_name, vless_url)
        profiles = await get_static_profiles()
        for profile in profiles:
            if profile.name == profile_name:
                id = profile.id
        builder = InlineKeyboardBuilder()
        builder.button(text="🗑️ Удалить", callback_data=f"delete_static_{id}")
        await message.answer(f"Профиль создан!\n\n`{vless_url}`", reply_markup=builder.as_markup(), parse_mode='Markdown')
    else:
        await message.answer("Ошибка при создании профиля")
    
    await state.clear()

@router.callback_query(F.data == "static_profile_list")
async def static_profile_list(callback: CallbackQuery):
    profiles = await get_static_profiles()
    if not profiles:
        await callback.answer("Нет статических профилей")
        return
    
    for profile in profiles:
        builder = InlineKeyboardBuilder()
        builder.button(text="🗑️ Удалить", callback_data=f"delete_static_{profile.id}")
        await callback.message.answer(
            f"**{profile.name}**\n`{profile.vless_url}`", 
            reply_markup=builder.as_markup(), parse_mode='Markdown'
        )

@router.callback_query(F.data.startswith("delete_static_"))
async def handle_delete_static_profile(callback: CallbackQuery):
    try:
        profile_id = int(callback.data.split("_")[-1])
        
        with Session() as session:
            profile = session.query(StaticProfile).filter_by(id=profile_id).first()
            if not profile:
                await callback.answer("⚠️ Профиль не найден")
                return
            
            success = await delete_client_by_email(profile.name)
            if not success:
                logger.error(f"🛑 Ошибка удаления клиента из инбаунда: {profile.name}")
            
            session.delete(profile)
            session.commit()
        
        await callback.answer("✅ Профиль удален!")
        await callback.message.delete()
    except Exception as e:
        logger.error(f"🛑 Ошибка при удалении статического профиля: {e}")
        await callback.answer("⚠️ Ошибка при удалении профиля")

@router.callback_query(F.data == "connect")
async def connect_profile(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("🛑 Ошибка профиля")
        return
    
    if not user.chat_member:
        await callback.answer("Сервис недоступен.")
        return
    
    if not user.vless_profile_data:
        await callback.message.edit_text("⚙️ Создаем ваш VPN профиль...")
        profile_data = await create_vless_profile(user.telegram_id)
        
        if profile_data:
            with Session() as session:
                db_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
                if db_user:
                    db_user.vless_profile_data = json.dumps(profile_data)
                    session.commit()
            user = await get_user(user.telegram_id)
        else:
            await callback.message.answer("🛑 Ошибка при создании профиля. Попробуйте позже.")
            return
    
    profile_data = safe_json_loads(user.vless_profile_data, default={})
    if not profile_data:
        await callback.message.answer("⚠️ У вас пока нет созданного профиля.")
        return
    vless_url = generate_vless_url(profile_data)
    text = (
        "🎉 **Ваш VPN профиль готов!**\n\n"
        "ℹ️ **Инструкция по подключению:**\n"
        "1. Скачайте приложение для вашей платформы\n"
        "2. Скопируйте эту ссылку и импортируйте в приложение:\n\n"
        f"`{vless_url}`\n\n"
        "3. Активируйте соединение в приложении."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text='🖥️ Windows [Hiddify]', url='https://github.com/hiddify/hiddify-app/releases/latest/download/Hiddify-Windows-Setup-x64.Msix')
    builder.button(text='🐧 Linux [NekoBox]', url='https://github.com/MatsuriDayo/nekoray/releases/download/4.0.1/nekoray-4.0.1-2024-12-12-debian-x64.deb')
    builder.button(text='🍎 Mac [V2RayU]', url='https://github.com/yanue/V2rayU/releases/download/v4.2.6/V2rayU-64.dmg ')
    builder.button(text='🍏 iOS [V2RayTun]', url='https://apps.apple.com/ru/app/v2raytun/id6476628951')
    builder.button(text='🤖 Android [V2RayNG]', url='https://github.com/2dust/v2rayNG/releases/download/1.10.16/v2rayNG_1.10.16_arm64-v8a.apk')
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    builder.adjust(2, 2, 1, 1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode='Markdown')

@router.callback_query(F.data == "stats")
async def user_stats(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.vless_profile_data:
        await callback.answer("⚠️ Профиль не создан")
        return
    await callback.message.edit_text("⚙️ Загружаем вашу статистику...")
    profile_data = safe_json_loads(user.vless_profile_data, default={})
    stats = await get_user_stats(profile_data["email"])

    logger.debug(stats)
    upload = f"{stats.get('upload', 0) / 1024 / 1024:.2f}"
    upload_size = 'MB' if int(float(upload)) < 1024 else 'GB'
    if upload_size == "GB":
        upload = f"{int(float(upload) / 1024):.2f}"

    download = f"{stats.get('download', 0) / 1024 / 1024:.2f}"
    download_size = 'MB' if int(float(download)) < 1024 else 'GB'
    if download_size == "GB":
        download = f"{int(float(download) / 1024):.2f}"

    await callback.message.delete()
    text = (
        "📊 **Ваша статистика:**\n\n"
        f"🔼 Загружено: `{upload} {upload_size}`\n"
        f"🔽 Скачано: `{download} {download_size}`\n"
    )
    await callback.message.answer(text, parse_mode='Markdown')

@router.callback_query(F.data == "admin_network_stats")
async def network_stats(callback: CallbackQuery):
    stats = await get_global_stats()

    upload = f"{stats.get('upload', 0) / 1024 / 1024:.2f}"
    upload_size = 'MB' if int(float(upload)) < 1024 else 'GB'
    if upload_size == "GB":
        upload = f"{int(float(upload) / 1024):.2f}"

    download = f"{stats.get('download', 0) / 1024 / 1024:.2f}"
    download_size = 'MB' if int(float(download)) < 1024 else 'GB'
    if download_size == "GB":
        download = f"{int(float(download) / 1024):.2f}"
    
    await callback.answer()
    text = (
        "📊 **Статистика использования сети:**\n\n"
        f"🔼 Upload: `{upload} {upload_size}` | 🔽 Download: `{download} {download_size}`"
    )
    await callback.message.edit_text(text, parse_mode='Markdown')

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await show_menu(bot, callback.from_user.id, callback.message.message_id)

def setup_handlers(dp: Dispatcher):
    dp.include_router(router)
    logger.info("✅ Handlers setup completed")

def safe_json_loads(data, default=None):
    if not data:
        return default
    try:
        return json.loads(data)
    except Exception:
        return default
