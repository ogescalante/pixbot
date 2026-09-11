"""A Telegram bot that turns a Pix key into a copia-e-cola, in any chat.

Two ways in. `/pix <chave> <valor>` in a direct chat answers with the code and
a copy button. `@bot <chave> <valor>` from inside any conversation posts the
same thing where the payment is actually being discussed — which is the point
of the inline mode: the person asking you to pay is right there, and the key
never makes a round trip through another app where a clipboard hijacker can
swap it.

Nothing is stored. No key, no amount, no chat id. The bot holds a payment
intent for exactly as long as it takes to answer.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

from aiogram import F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
)

from bot import bot, dp
from pix.banks import Button
from pix.render import USAGE, Quote, quotes, render

logging.basicConfig(level=logging.INFO)

HELP = (
    USAGE
    + "\n\n"
    "Em qualquer conversa, sem me adicionar no grupo:\n"
    "   @{username} gabriel.escsilva@gmail.com 120"
)


def _markup(rows: list[list[Button]]) -> InlineKeyboardMarkup:
    """Framework-free buttons -> Telegram's keyboard.

    `copy_text` is a client-side clipboard write: the payload never becomes a
    message, so a code posted in a group is copied by whoever needs it without
    being quoted, forwarded, or scraped out of the chat history.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=b.label, url=b.url, style=b.style)
            if b.url
            else InlineKeyboardButton(
                text=b.label,
                copy_text=types.CopyTextButton(text=b.copy or ""),
                style=b.style,
            )
            for b in row
        ]
        for row in rows
    ])


def _result_id(quote: Quote) -> str:
    """Stable per (key, amount, reading) — Telegram caps result ids at 64 bytes.

    A hash rather than the key itself: the id travels back in the
    chosen_inline_result update, and there is no reason for a Pix key to sit in
    telemetry that the payment does not need.
    """
    return hashlib.sha256(quote.code.encode()).hexdigest()[:32]


@dp.message(Command(commands=["start", "help"]))
async def start(message: types.Message) -> None:
    logging.info("start from chat_id=%s", message.chat.id)
    me = await bot.get_me()
    await message.answer(HELP.format(username=me.username))


@dp.message(Command(commands=["pix"]))
async def pix(message: types.Message) -> None:
    text, rows = render(message.text or "")
    await message.answer(text, reply_markup=_markup(rows) if rows else None)


@dp.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def bare_key(message: types.Message) -> None:
    """In a direct chat the command is optional — a pasted key is the request.

    Restricted to private chats on purpose. Added to a group, a bot that reads
    every message and answers anything key-shaped is a nuisance at best; there
    the inline mode is the way in, and it needs no group membership at all.
    """
    text, rows = render(message.text or "")
    await message.answer(text, reply_markup=_markup(rows) if rows else None)


@dp.inline_query()
async def inline(query: types.InlineQuery) -> None:
    """One card per defensible reading of the key.

    Ambiguity is where inline mode beats a chat reply: when eleven digits pass
    the CPF checksum *and* look like a mobile, there is no warning to write —
    there are two cards, and the person who knows whose key it is picks one.
    """
    # Chat type and sizes only — never the key itself. This is the line that
    # says whether Telegram is delivering inline queries at all, which is the
    # first thing to know when a card does not appear.
    logging.info(
        "inline_query from=%s chat_type=%s len=%d",
        query.from_user.id, query.chat_type, len(query.query),
    )
    found, error = quotes(query.query)
    if error is not None:
        await query.answer(
            results=[],
            cache_time=5,
            is_personal=True,
            button=InlineQueryResultsButton(
                text=("Manda a chave e o valor: 45999999999 120"
                      if not query.query.strip()
                      else "Não reconheci essa chave — toca pra ver como usar"),
                start_parameter="ajuda",
            ),
        )
        return

    await query.answer(
        results=[
            InlineQueryResultArticle(
                id=_result_id(q),
                title=q.title,
                description=q.description,
                input_message_content=InputTextMessageContent(
                    message_text=q.message
                ),
                reply_markup=_markup(q.buttons),
            )
            for q in found
        ],
        # Short and per-user: the query carries a key and an amount, and there
        # is nothing to gain from Telegram holding either for five minutes.
        cache_time=5,
        is_personal=True,
    )
    logging.info("inline_query answered with %d card(s)", len(found))


async def _run() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(_run())
