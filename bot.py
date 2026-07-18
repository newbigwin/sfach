import os
import asyncio
import logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN
from database import (
    init_db, get_pending_reminders, mark_reminder_sent,
    get_all_active_recurring_events, mark_recurring_event_created,
    track_known_user, get_due_posts, mark_post_published
)
from handlers import admin, user

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = "/webhook"
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", 8000))

reminder_task = None
recurring_task = None


async def check_reminders(bot: Bot):
    while True:
        try:
            reminders = await get_pending_reminders()
            for reminder in reminders:
                try:
                    await bot.send_message(
                        chat_id=reminder['chat_id'],
                        text=f"Напоминание: {reminder['title']}"
                    )
                    await mark_reminder_sent(reminder['id'])
                    logger.info(f"Reminder sent: {reminder['title']}")
                except Exception as e:
                    logger.error(f"Failed to send reminder: {e}")
                    await mark_reminder_sent(reminder['id'])
        except Exception as e:
            logger.error(f"Reminder check error: {e}")
        await asyncio.sleep(60)


async def check_recurring_events(bot: Bot):
    while True:
        try:
            now = datetime.now()
            events = await get_all_active_recurring_events()
            for event in events:
                if (event['day_of_week'] == now.weekday() and
                    event['hour'] == now.hour and
                    event['minute'] == now.minute):

                    last_created = event['last_created']
                    if last_created:
                        from datetime import timedelta
                        last_dt = datetime.fromisoformat(last_created)
                        if (now - last_dt) < timedelta(hours=1):
                            continue

                    try:
                        text = f"{event['title']}"
                        if event['description']:
                            text += f"\n\n{event['description']}"

                        if event['photo']:
                            await bot.send_photo(
                                chat_id=event['chat_id'],
                                photo=event['photo'],
                                caption=text
                            )
                        else:
                            await bot.send_message(
                                chat_id=event['chat_id'],
                                text=text
                            )
                        await mark_recurring_event_created(event['id'])
                        logger.info(f"Recurring event created: {event['title']}")
                    except Exception as e:
                        logger.error(f"Failed to create recurring event: {e}")
        except Exception as e:
            logger.error(f"Recurring event check error: {e}")
        await asyncio.sleep(60)


async def check_scheduled_posts(bot: Bot):
    while True:
        try:
            posts = await get_due_posts()
            for post in posts:
                try:
                    if post['image']:
                        await bot.send_photo(
                            chat_id=post['chat_id'],
                            photo=post['image'],
                            caption=post['text']
                        )
                    else:
                        await bot.send_message(
                            chat_id=post['chat_id'],
                            text=post['text']
                        )
                    await mark_post_published(post['id'])
                    logger.info(f"Scheduled post #{post['id']} published")
                except Exception as e:
                    logger.error(f"Failed to publish scheduled post #{post['id']}: {e}")
        except Exception as e:
            logger.error(f"Scheduled posts check error: {e}")
        await asyncio.sleep(60)


scheduled_task = None


async def on_startup(bot: Bot):
    global reminder_task, recurring_task, scheduled_task
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}")
    await init_db()
    reminder_task = asyncio.create_task(check_reminders(bot))
    recurring_task = asyncio.create_task(check_recurring_events(bot))
    scheduled_task = asyncio.create_task(check_scheduled_posts(bot))
    logger.info(f"Бот запущен! Webhook: {BASE_WEBHOOK_URL}{WEBHOOK_PATH}")


async def on_shutdown(bot: Bot):
    global reminder_task, recurring_task, scheduled_task
    if reminder_task:
        reminder_task.cancel()
    if recurring_task:
        recurring_task.cancel()
    if scheduled_task:
        scheduled_task.cancel()
    await bot.delete_webhook()
    logger.info("Бот остановлен.")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return

    if not BASE_WEBHOOK_URL:
        logger.warning("WEBHOOK_URL не установлен! Бот может не работать.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()

    @dp.message.outer_middleware()
    async def track_user_middleware(handler, event: Message, data):
        if event.from_user and event.from_user.id:
            await track_known_user(
                event.from_user.id,
                event.from_user.username,
                event.from_user.first_name
            )
        return await handler(event, data)

    dp.include_router(admin.router)
    dp.include_router(user.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    async def health_check(request):
        return web.Response(text="ok")

    async def debug_info(request):
        return web.json_response({
            "status": "running",
            "webhook_url": BASE_WEBHOOK_URL,
            "bot_token_set": bool(BOT_TOKEN),
        })

    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/debug", debug_info)

    logger.info(f"Сервер запускается на порту {WEB_SERVER_PORT}")
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    main()
