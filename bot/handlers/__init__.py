from aiogram import Dispatcher
from bot.handlers.download import router as download_router
from bot.handlers.admin import router as admin_router
from bot.handlers.cookies import router as cookies_router


def register_all_handlers(dp: Dispatcher):
    dp.include_router(admin_router)
    dp.include_router(cookies_router)
    dp.include_router(download_router)
