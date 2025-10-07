from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ..db import add_user

img = "AAB/utils/thumb.jpeg"

async def start_cmd(client: Client, message: Message):
    
    try:
        user = message.from_user
        if user:
            user_id = user.id
            name = user.first_name or "Unknown"
            if user.last_name:
                name += f" {user.last_name}"
            username = user.username
            
            is_new = add_user(user_id, name, username)
            if is_new:
                print(f"✅ New user started bot: {name} (@{username or 'no_username'})")
    except Exception as e:
        print(f"Error tracking user: {e}")

    welcome = list("WELCOME")
    welcome_row = [InlineKeyboardButton(text=ch, callback_data=f"welcome_{ch}") for ch in welcome]

    main_channel_url = "https://t.me/Awakeners_Gateway_TheBot?start=req_LTEwMDI3MjI1NTcwOTY"
    support_url = "https://t.me/Wyvern_Gateway_Bot?start=NQ=="
    backup_url = "https://t.me/Awakeners_Gateway_TheBot?start=OA=="

    action_row = [
        InlineKeyboardButton("𝗖𝗛𝗔𝗡𝗡𝗘𝗟", url=main_channel_url),
        InlineKeyboardButton("𝗦𝗨𝗣𝗣𝗢𝗥𝗧", url=support_url),
    ]

    backup_row = [
        InlineKeyboardButton("𝗕𝗔𝗖𝗞𝗨𝗣", url=backup_url),
    ]

    kb = InlineKeyboardMarkup([welcome_row, action_row, backup_row])

    text = (
        f">👋 hey, {user.mention()}🎉\n\n"
        "I'm File Provider Bot..\n"
        "Use the buttons below to stay connected with our community!"
    )

    await message.reply_photo(photo=img,caption=text, reply_markup=kb)
