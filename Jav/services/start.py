from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ..db import add_user

img = "AAB/utils/thumb.jpeg"

async def start_cmd(client: Client, message: Message):
    
    # Track user in database
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

    main_channel_url = "https://t.me/AutoMangaCampus"
    support_url = "https://t.me/AutoMangaCampus"
    backup_url = "https://t.me/AutoMangaCampus"

    action_row = [
        InlineKeyboardButton("𝗖𝗛𝗔𝗡𝗡𝗘𝗟", url=main_channel_url),
        InlineKeyboardButton("𝗦𝗨𝗣𝗣𝗢𝗥𝗧", url=support_url),
    ]

    backup_row = [
        InlineKeyboardButton("𝗕𝗔𝗖𝗞𝗨𝗣", url=backup_url),
    ]

    kb = InlineKeyboardMarkup([welcome_row, action_row, backup_row])

    text = (
        "👋 𝑯𝒆𝒚, 𝑾𝒆𝒍𝒄𝒐𝒎𝒆 𝒕𝒐 𝒕𝒉𝒆 <b>𝗝𝗔𝗩 𝗕𝗼𝘁</b> 🎉\n\n"
        "✨ Explore unlimited fun, updates & spicy content.\n"
        "⚡ Use the buttons below to stay connected with our community!"
    )

    await message.reply_photo(photo=img,caption=text, reply_markup=kb)
