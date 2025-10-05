"""
Button utilities for Telegram messages.

This module provides reusable functions for adding various types of buttons
to Telegram messages, eliminating code duplication.
"""

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
    """
    Add download button(s) to a message with automatic FloodWait handling.
    
    This unified function handles all button configurations:
    - Single download button (file_hash)
    - Part 1 & Part 2 buttons (part_hashes)
    - Telegraph preview button (telegraph_url)
    - Custom additional buttons
    
    Args:
        bot_client: Telegram bot client
        message: Message to add buttons to
        bot_username: Bot username for deep links
        file_hash: Hash for single file download (optional)
        part_hashes: List of hashes for multi-part downloads (optional)
        telegraph_url: URL for Telegraph preview button (optional)
        additional_buttons: Custom button rows to append (optional)
        
    Returns:
        True if buttons were added successfully, False otherwise
        
    Example:
        # Single file download
        await add_download_buttons(bot, msg, "mybot", file_hash="abc123")
        
        # Multi-part download with preview
        await add_download_buttons(
            bot, msg, "mybot",
            part_hashes=["hash1", "hash2"],
            telegraph_url="https://telegra.ph/preview"
        )
    """
    from ..utils import handle_flood_wait
    
    try:
        buttons = []
        
        # Add part buttons if multi-part download
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
        
        # Add single download button if file_hash provided and no parts
        elif file_hash:
            download_row = [
                InlineKeyboardButton(
                    text="𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 𝗡𝗢𝗪",
                    url=f"https://t.me/{bot_username}?start={file_hash}"
                )
            ]
            buttons.append(download_row)
            LOG.debug("Added single download button")
        
        # Add Telegraph preview button if URL provided
        if telegraph_url:
            preview_row = [
                InlineKeyboardButton(
                    text="📺 Video Preview",
                    url=telegraph_url
                )
            ]
            buttons.append(preview_row)
            LOG.debug("Added Telegraph preview button")
        
        # Add any custom buttons
        if additional_buttons:
            buttons.extend(additional_buttons)
            LOG.debug(f"Added {len(additional_buttons)} custom button row(s)")
        
        # If no buttons to add, return success
        if not buttons:
            LOG.warning("No buttons to add to message")
            return True
        
        # Create markup and add to message
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
    """
    Add source and/or magnet link buttons to a message.
    
    Args:
        bot_client: Telegram bot client
        message: Message to add buttons to
        source_url: URL to source page (optional)
        magnet_url: Magnet link URL (optional)
        
    Returns:
        True if buttons were added successfully, False otherwise
    """
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


# Export button utilities
__all__ = [
    'add_download_buttons',
    'add_source_and_magnet_buttons',
]
