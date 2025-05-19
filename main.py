#Copyright (C) @TheSmartBisnu

#Channel: https://t.me/itsSmartDev

import os import shutil from time import time

import psutil from pyrogram import Client, filters from pyrogram.enums import ParseMode from pyrogram.errors import PeerIdInvalid, BadRequest from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton from pyleaves import Leaves

from helpers.utils import ( getChatMsgID, processMediaGroup, get_parsed_msg, fileSizeLimit, progressArgs, send_media, get_readable_file_size, get_readable_time, )

from config import PyroConf from logger import LOGGER

Initialize the bot client

bot = Client( "media_bot", api_id=PyroConf.API_ID, api_hash=PyroConf.API_HASH, bot_token=PyroConf.BOT_TOKEN, workers=1000, parse_mode=ParseMode.MARKDOWN, )

Client for user session

user = Client("user_session", workers=1000, session_string=PyroConf.SESSION_STRING)

Forced subscription check

target_channel = "zeedtek"

async def is_subscribed(bot: Client, user_id: int) -> bool: try: member = await bot.get_chat_member(target_channel, user_id) return member.status in ("member", "administrator", "creator") except Exception: return False

force_sub_markup = InlineKeyboardMarkup([ [InlineKeyboardButton("اشترك في القناة", url=f"https://t.me/{target_channel}")], [InlineKeyboardButton("✅ تحقّق من الاشتراك", callback_data="check_sub")] ])

@bot.on_message(filters.command("start") & filters.private) async def start(_, message: Message): if not await is_subscribed(bot, message.from_user.id): await message.reply( "⚠️ يجب عليك الاشتراك في القناة لمتابعة استخدام البوت.", reply_markup=force_sub_markup ) return

welcome_text = (
    "**👋 Welcome to the Media Downloader Bot!**\n\n"
    "This bot helps you download media from Restricted channel\n"
    "Use /help for more information on how to use this bot."
)
await message.reply(welcome_text)

@bot.on_message(filters.command("help") & filters.private) async def help_command(_, message: Message): if not await is_subscribed(bot, message.from_user.id): await message.reply( "⚠️ يجب عليك الاشتراك في القناة لمتابعة استخدام البوت.", reply_markup=force_sub_markup ) return

help_text = (
    "💡 **How to Use the Bot**\n\n"
    "1. Send the command `/dl post URL` to download media from a specific message.\n"
    "2. The bot will download the media (photos, videos, audio, or documents) also can copy message.\n"
    "3. Make sure the bot and the user client are part of the chat to download the media.\n\n"
    "**Example**: `/dl https://t.me/mypublicstuffs/3`"
)
await message.reply(help_text)

@bot.on_message(filters.command("dl") & filters.private) async def download_media(bot: Client, message: Message): if not await is_subscribed(bot, message.from_user.id): await message.reply( "⚠️ يجب عليك الاشتراك في القناة لمتابعة استخدام البوت.", reply_markup=force_sub_markup ) return

if len(message.command) < 2:
    await message.reply("**Provide a post URL after the /dl command.**")
    return

post_url = message.command[1]

try:
    chat_id, message_id = getChatMsgID(post_url)
    chat_message = await user.get_messages(chat_id=chat_id, message_ids=message_id)

    LOGGER(__name__).info(f"Downloading media from URL: {post_url}")

    if chat_message.document or chat_message.video or chat_message.audio:
        file_size = (
            chat_message.document.file_size
            if chat_message.document
            else chat_message.video.file_size
            if chat_message.video
            else chat_message.audio.file_size
        )

        if not await fileSizeLimit(
            file_size, message, "download", user.me.is_premium
        ):
            return

    parsed_caption = await get_parsed_msg(
        chat_message.caption or "", chat_message.caption_entities
    )
    parsed_text = await get_parsed_msg(
        chat_message.text or "", chat_message.entities
    )

    if chat_message.media_group_id:
        if not await processMediaGroup(chat_message, bot, message):
            await message.reply(
                "**Could not extract any valid media from the media group.**"
            )
        return

    elif chat_message.media:
        start_time = time()
        progress_message = await message.reply("**📅 Downloading Progress...**")

        media_path = await chat_message.download(
            progress=Leaves.progress_for_pyrogram,
            progress_args=progressArgs(
                "📅 Downloading Progress", progress_message, start_time
            ),
        )

        LOGGER(__name__).info(f"Downloaded media: {media_path}")

        media_type = (
            "photo"
            if chat_message.photo
            else "video"
            if chat_message.video
            else "audio"
            if chat_message.audio
            else "document"
        )
        await send_media(
            bot,
            message,
            media_path,
            media_type,
            parsed_caption,
            progress_message,
            start_time,
        )

        os.remove(media_path)
        await progress_message.delete()

    elif chat_message.text or chat_message.caption:
        await message.reply(parsed_text or parsed_caption)
    else:
        await message.reply("**No media or text found in the post URL.**")

except (PeerIdInvalid, BadRequest, KeyError):
    await message.reply("**Make sure the user client is part of the chat.**")
except Exception as e:
    error_message = f"**❌ {str(e)}**"
    await message.reply(error_message)
    LOGGER(__name__).error(e)

@bot.on_callback_query(filters.regex("check_sub")) async def recheck_subscription(client, callback_query): user_id = callback_query.from_user.id

if await is_subscribed(bot, user_id):
    await callback_query.message.edit_text(
        "**✅ تم التحقق من اشتراكك بنجاح، أعد إرسال الأمر الآن.**"
    )
else:
    await callback_query.answer(
        "❌ لم يتم العثور على اشتراكك. تأكد من أنك مشترك في القناة.", show_alert=True
    )

@bot.on_message(filters.command("stats") & filters.private) async def stats(_, message: Message): currentTime = get_readable_time(time() - PyroConf.BOT_START_TIME) total, used, free = shutil.disk_usage(".") total = get_readable_file_size(total) used = get_readable_file_size(used) free = get_readable_file_size(free) sent = get_readable_file_size(psutil.net_io_counters().bytes_sent) recv = get_readable_file_size(psutil.net_io_counters().bytes_recv) cpuUsage = psutil.cpu_percent(interval=0.5) memory = psutil.virtual_memory().percent disk = psutil.disk_usage("/").percent process = psutil.Process(os.getpid())

stats = (
    "**≧◉◡◉≦ Bot is Up and Running successfully.**\n\n"
    f"**➜ Bot Uptime:** `{currentTime}`\n"
    f"**➜ Total Disk Space:** `{total}`\n"
    f"**➜ Used:** `{used}`\n"
    f"**➜ Free:** `{free}`\n"
    f"**➜ Memory Usage:** `{round(process.memory_info()[0] / 1024**2)} MiB`\n\n"
    f"**➜ Upload:** `{sent}`\n"
    f"**➜ Download:** `{recv}`\n\n"
    f"**➜ CPU:** `{cpuUsage}%` | "
    f"**➜ RAM:** `{memory}%` | "
    f"**➜ DISK:** `{disk}%`"
)
await message.reply(stats)

@bot.on_message(filters.command("logs") & filters.private) async def logs(_, message: Message): if os.path.exists("logs.txt"): await message.reply_document(document="logs.txt", caption="Logs") else: await message.reply("Not exists")

if name == "main": try: LOGGER(name).info("Bot Started!") user.start() bot.run() except KeyboardInterrupt: pass except Exception as err: LOGGER(name).error(err) finally: LOGGER(name).info("Bot Stopped")

