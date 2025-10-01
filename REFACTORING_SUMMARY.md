# Auto-JAV Bot - Refactored Codebase Structure

## Overview
The codebase has been refactored from a monolithic `runtime.py` (880 lines) into a clean, modular structure.

## New Directory Structure

```
AABv2/
├── __init__.py
├── __main__.py
├── clients.py
├── config.py
├── db.py
├── runtime.py (153 lines - simplified!)
├── utils.py
│
├── handlers/                    [NEW]
│   ├── __init__.py
│   ├── commands.py             # Bot commands (alive, logs, status, start)
│   └── utils.py                # Helper functions (send_logs_to_user)
│
├── processors/                  [NEW]
│   ├── __init__.py
│   ├── feed_checker.py         # Check for new items from API
│   ├── item_processor.py       # Main item processing logic
│   └── video_processor.py      # Video download, remux, upload logic
│
└── services/
    ├── ai_caption.py
    ├── downloader.py
    ├── encode.py
    ├── feed.py                 # API fetching (cleaned up)
    ├── start.py
    ├── translator.py
    └── uploader.py             # File upload logic (cleaned up)
```

## Module Breakdown

### 1. **handlers/** - Bot Command Handlers
- `commands.py`: All Telegram bot commands
  - `/alive` - Check if bot is running
  - `/logs` - Get log file
  - `/status` - Get bot status
  - `/start` - Handle file sharing via deep links
- `utils.py`: Helper functions for handlers

### 2. **processors/** - Core Business Logic
- `feed_checker.py`: Checks for new items from API, handles deduplication
- `item_processor.py`: Main processing logic, decides download vs thumbnail-only post
- `video_processor.py`: Handles video download, remuxing, splitting large files, uploading

### 3. **services/** - External Services
- `feed.py`: API communication (cleaned, comments removed)
- `uploader.py`: File upload to Telegram (cleaned)
- `downloader.py`: Torrent download
- `ai_caption.py`: AI caption generation
- Other services remain unchanged

### 4. **runtime.py** - Application Entry Point
- Simplified to 153 lines (from 880 lines!)
- Handles:
  - MongoDB connection
  - Telegram client initialization
  - Command handler registration
  - Worker loop coordination

## Key Improvements

### ✅ Separation of Concerns
- Each module has a single, clear responsibility
- Easy to locate and modify specific functionality

### ✅ Reduced Complexity
- Main runtime file is now 82% smaller
- Each file is focused and maintainable

### ✅ Better Organization
- Handlers separate from processors
- Business logic separate from infrastructure
- Clear import paths

### ✅ Clean Code
- Removed unnecessary comments
- Kept only important comments
- Consistent structure across modules

## Import Structure

```python
# Old (everything in runtime.py)
from .runtime import process_item, check_for_new_items, alive_command, ...

# New (organized imports)
from .handlers import alive_command, logs_command, status_command, start_command
from .processors import process_item, check_for_new_items
```

## Migration Notes

- Old runtime.py backed up as `runtime_old_backup.py`
- All functionality preserved
- No breaking changes to external interfaces
- Database and API interactions unchanged

## Testing Checklist

- [ ] Bot starts successfully
- [ ] MongoDB connection works
- [ ] Telegram commands respond
- [ ] Feed checking works
- [ ] Video download and upload works
- [ ] Thumbnail-only posts work
- [ ] File forwarding via /start works
- [ ] Large file splitting works
- [ ] AI caption generation works

## Next Steps

1. Test the refactored code thoroughly
2. Remove `runtime_old_backup.py` if everything works
3. Consider adding unit tests for each module
4. Add type hints throughout
5. Consider adding async context managers for cleanup
