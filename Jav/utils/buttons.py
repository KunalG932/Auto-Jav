
import logging
from typing import Optional, List
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

LOG = logging.getLogger("Jav")

async def add_download_buttons(
    bot_client,
    message: Message,
    bot_username: str,
    file_hash: Optional[str] = None,
    part_hashes: Optional[List[str]] = None,
    telegraph_url: Optional[str] = None,
    additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None
) -> bool:
    from ..utils import handle_flood_wait
    
    try:
        buttons = []
        
        if part_hashes and len(part_hashes) >= 2:
            part_row = [
                InlineKeyboardButton(
                    text="𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 𝗣𝗔𝗥𝗧 𝟭",
                    url=f"https://t.me/{bot_username}?start={part_hashes[0]}"
                ),
                InlineKeyboardButton(
                    text="𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 𝗣𝗔𝗥𝗧 𝟮",
                    url=f"https://t.me/{bot_username}?start={part_hashes[1]}"
                )
            ]
            buttons.append(part_row)
            LOG.debug("Added part download buttons")
        
        elif file_hash:
            download_row = [
                InlineKeyboardButton(
                    text="𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 𝗡𝗢𝗪",
                    url=f"https://t.me/{bot_username}?start={file_hash}"
                )
            ]
            buttons.append(download_row)
            LOG.debug("Added single download button")
        
        if telegraph_url:
            preview_row = [
                InlineKeyboardButton(
                    text="𝗩𝗜𝗗𝗘𝗢 𝗣𝗥𝗘𝗩𝗜𝗘𝗪",
                    url=telegraph_url
                ),
                InlineKeyboardButton(
                    text="𝗕𝗔𝗖𝗞𝗨𝗣",
                    url="https://t.me/Wyvern_Gateway_Bot?start=req_LTEwMDMxMjI5MDg0NjE"
                )
            ]
            buttons.append(preview_row)
            LOG.debug("Added Telegraph preview and backup buttons")
        
        if additional_buttons:
            buttons.extend(additional_buttons)
            LOG.debug(f"Added {len(additional_buttons)} custom button row(s)")
        
        if not buttons:
            LOG.warning("No buttons to add to message")
            return True
        
        markup = InlineKeyboardMarkup(buttons)
        
        await handle_flood_wait(
            message.edit_reply_markup,
            markup,
            operation_name="add buttons to message"
        )
        
        LOG.info(f"✅ Successfully added {len(buttons)} button row(s) to message")
        return True
        
    except Exception as e:
        LOG.error(f"Failed to add buttons to message: {e}", exc_info=True)
        return False

async def add_source_and_magnet_buttons(
    bot_client,
    message: Message,
    source_url: Optional[str] = None,
    magnet_url: Optional[str] = None
) -> bool:
    from ..utils import handle_flood_wait
    
    try:
        buttons = []
        
        if magnet_url:
            magnet_row = [
                InlineKeyboardButton(
                    text="📥 Magnet Link",
                    url=magnet_url
                )
            ]
            buttons.append(magnet_row)
        
        if source_url:
            source_row = [
                InlineKeyboardButton(
                    text="🔗 Source",
                    url=source_url
                )
            ]
            buttons.append(source_row)
        
        if not buttons:
            LOG.debug("No source or magnet buttons to add")
            return True
        
        markup = InlineKeyboardMarkup(buttons)
        
        await handle_flood_wait(
            message.edit_reply_markup,
            markup,
            operation_name="add source/magnet buttons"
        )
        
        LOG.info(f"✅ Successfully added source/magnet buttons")
        return True
        
    except Exception as e:
        LOG.error(f"Failed to add source/magnet buttons: {e}", exc_info=True)
        return False

__all__ = [
    'add_download_buttons',
    'add_source_and_magnet_buttons',
]
