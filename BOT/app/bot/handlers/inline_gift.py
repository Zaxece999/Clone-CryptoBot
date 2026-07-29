from aiogram.types import InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import os

from app.database import AsyncSessionLocal
from app.services.check import check_service

logger = structlog.get_logger(__name__)


async def create_gift_results(activation_code: str) -> list:
    try:
        logger.info("Creating gift results", activation_code=activation_code, activation_code_type=type(activation_code))
        async with AsyncSessionLocal() as db:
            logger.info("Database session created, searching for check")

            logger.info("Searching for check with activation_code", activation_code=activation_code)
            check = await check_service.get_check_by_activation_code(db, activation_code)
            logger.info("Check search completed",
                       check_found=check is not None,
                       check_id=check.check_id if check else None,
                       check_status=check.status if check else None)

            if not check:
                logger.warning("Gift not found", activation_code=activation_code)

                from sqlalchemy import select
                from app.models.check import Check
                all_checks_query = select(Check.activation_code, Check.status, Check.created_at).limit(10)
                result = await db.execute(all_checks_query)
                all_checks = result.fetchall()
                logger.info("Recent checks in DB", checks=[(c.activation_code, c.status) for c in all_checks])

                return [
                    InlineQueryResultArticle(
                        id="gift_not_found",
                        title="❌ Подарок не найден",
                        description=f"Код: {activation_code}",
                        input_message_content=InputTextMessageContent(
                            message_text=f"❌ Подарок не найден или уже активирован\nКод: {activation_code}"
                        )
                    )
                ]

            logger.info("Checking check status",
                       check_status=check.status,
                       is_active=check.status == "active")

            if check.status != "active":
                from app.config import settings
                bot_username = settings.bot_username
                start_url = f"https://t.me/{bot_username}?start=start"

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"✅ Получено {check.amount} {check.currency}",
                            callback_data=f"gift_received_{activation_code}_{check.amount}_{check.currency}"
                        )
                    ]
                ])

                return [
                    InlineQueryResultPhoto(
                        id=f"gift_used_{activation_code}",
                        photo_url="https://via.placeholder.com/400x300/90EE90/FFFFFF?text=✅",
                        thumbnail_url="https://via.placeholder.com/200x150/90EE90/FFFFFF?text=✅",
                        title="✅ Подарок уже получен",
                        description=f"Получено {check.amount} {check.currency}",
                        input_message_content=InputTextMessageContent(
                            message_text="✅ Этот подарок уже был получен",
                            parse_mode="HTML"
                        ),
                        reply_markup=keyboard
                    )
                ]

            logger.info("Creating active gift result",
                       activation_code=activation_code,
                       check_amount=check.amount,
                       check_currency=check.currency)

            from app.config import settings
            bot_username = settings.bot_username
            check_url = f"https://t.me/{bot_username}?start=activate_check_{activation_code}"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Получить",
                        url=check_url
                    )
                ]
            ])

            logger.info("Creating gift article result")

            results = [
                InlineQueryResultArticle(
                    id=f"gift_{activation_code}",
                    title="🎁 Подарок",
                    description=f"Получите {check.amount} {check.currency}",
                    input_message_content=InputTextMessageContent(
                        message_text="🎁 У меня для тебя подарок! Нажми на кнопку ниже, чтобы получить его.",
                        parse_mode="HTML"
                    ),
                    reply_markup=keyboard
                )
            ]

            logger.info("Gift results created successfully",
                       activation_code=activation_code,
                       results_count=len(results))

            return results

    except Exception as e:
        logger.error("Failed to create gift results",
                    activation_code=activation_code,
                    error=str(e),
                    exc_info=True)
        return [
            InlineQueryResultArticle(
                id="gift_error",
                title="❌ Ошибка загрузки подарка",
                description=f"Ошибка: {str(e)}",
                input_message_content=InputTextMessageContent(
                    message_text=f"❌ Произошла ошибка при загрузке подарка\nОшибка: {str(e)}"
                )
            )
        ]
