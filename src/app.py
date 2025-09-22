import json
import asyncio
import logging
import warnings
import coloredlogs
from config import config
from aiogram import Bot, Dispatcher
from handlers import setup_handlers
from functions import delete_client_by_email, check_if_user_chat_member
from database import Session, User, init_db, get_all_users, delete_user_profile

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Настройка логирования
coloredlogs.install(level='info')
logger = logging.getLogger(__name__)

async def check_users(bot: Bot):
    """Ревизия пользователей"""
    while True:
        try:
            users = await get_all_users()
            
            for user in users:
                # Проверяем, является ли пользователь участником чата (группы)
                user_chat_member = await check_if_user_chat_member(user.telegram_id, bot)

                if not user_chat_member and user.vless_profile_data:
                    try:
                        profile = json.loads(user.vless_profile_data)
                        # Удаляем из инбаунда
                        success = await delete_client_by_email(profile["email"])
                        if success:
                            # Удаляем профиль из БД
                            await delete_user_profile(user.telegram_id)
                            
                            await bot.send_message(
                                user.telegram_id,
                                "❌ Ваш профиль VPN был удален."
                            )
                        else:
                            logger.warning(f"⚠️ Failed to delete client {profile['email']} from inbound")
                    except Exception as e:
                        logger.warning(f"⚠️ Deletion error: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Users check error: {e}")
        
        await asyncio.sleep(3600)

async def update_admins_status():
    """Обновляет статус администраторов в базе данных"""
    with Session() as session:
        # Сбрасываем статус администратора у всех пользователей
        session.query(User).update({User.is_admin: False})
        
        # Устанавливаем статус администратора для пользователей из config.ADMINS
        for admin_id in config.ADMINS:
            user = session.query(User).filter_by(telegram_id=admin_id).first()
            if user:
                user.is_admin = True
            else:
                # Если администратора нет в базе, создаем запись
                new_admin = User(
                    telegram_id=admin_id,
                    full_name=f"Admin {admin_id}",
                    is_admin=True
                )
                session.add(new_admin)
        
        session.commit()
    logger.info("✅ Admin status updated in database")

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    try:
        await init_db()
        logger.info("✅ Database initialized")

        # Обновляем статус администраторов
        await update_admins_status()
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        return
    
    try:
        setup_handlers(dp)
        logger.info("✅ Handlers registered")
    except Exception as e:
        logger.error(f"❌ Handler registration error: {e}")
        return
    
    # Запускаем фоновую задачу проверки пользователей
    try:
        asyncio.create_task(check_users(bot))
    except Exception as e:
        logger.error(f"❌ Users check task failed to start: {e}")
    
    logger.info("ℹ️  Starting bot...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Bot start error: {e}")
        return

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Stopping bot...")
        exit(0)
    except Exception as e:
        logger.error(f"❌ Main loop error: {e}")
        exit(1)
