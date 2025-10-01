# Auto JAV Bot
<div align="center">
  <img src="https://graph.org/file/8bb750efbe7f08176e2ae.png" alt="Auto JAV Bot">
</div>

Auto JAV Bot is a Telegram bot that automatically discovers and uploads JAV releases to a Telegram channel. It integrates with an external API to fetch new items, downloads via magnet when available, and posts a channel message containing Magnet/Torrent links. Users can retrieve uploaded files via deep-link buttons.


## Features

- **Automatic discovery** of new JAV items via API
- **Magnet-based downloading** with torrent support
- **Automatic video encoding** to 720p quality for optimal file size
- **Smart file size management** - Files >2GB automatically split into parts
- **Upload to Telegram** files channel with deep-link access
- **Single "Download Now" button** - No external Magnet/Torrent links exposed
- **Deep-link button** to receive uploaded files in DM
- **Thumbnail support** - Automatically downloads and displays video thumbnails
- **Retry mechanism** - API calls with exponential backoff for reliability

## Requirements

- **VPS or machine** with Python 3.11+
- **MongoDB** for state management and file index
- **FFmpeg** for video encoding and processing
- **System libtorrent** (python3-libtorrent) for torrent downloads
- **Sufficient disk space** for temporary video storage during processing

## Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Dhruv-Tara/Auto-Anime-Bot && cd Auto-Anime-Bot
   ```

2. **Install Dependencies:**
   
   - Remeber to Run the setup in sudo environment.

    ```bash
   bash setup.sh
   ```

3. **Configure Bot:**
   - Create your Telegram bots and obtain API credentials
   - Copy `.env.example` to `.env` and fill in your values:
     - **Required:** `API_ID`, `API_HASH`, `MAIN_BOT_TOKEN`, `CLIENT_BOT_TOKEN`
     - **Channels:** `MAIN_CHANNEL`, `FILES_CHANNEL`, `PRODUCTION_CHAT`
     - **Database:** `MONGO_URI`
     - **Encoding:** Configure video quality settings (see [ENCODING_SETUP.md](ENCODING_SETUP.md))
   
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

4. **API Used:**
   - The bot fetches items from: `https://jav-api-w4od.onrender.com/api/latest?limit=10&sort_by_date=true&translate=true`.
   - Example response:

```json
{
  "status": "success",
  "total": 17,
  "results": [
    {
      "Download": {
        "Magnet": "<magnet_link>",
        "Torrent": "<torrent_link>"
      },
      "title": "<video_title>",
      "parse": {
        "file_name": "<file_name>",
        "video_resolution": "1080p",
        "video_term": "HD",
        "other": "Uncensored",
        "anime_title": "<anime_title>"
      }
    }
  ]
}
```
4. **Run the Bot:**
   ```bash
   python3.11 -m AAB
   ```
   or
   ```bash
   bash start.sh
   ```

5. **Accessing Files:**
   - Users tap the "Get File" button in channel posts (deep-links to `/start <hash>`)
   - Bot forwards the file from the files channel to the user's DM

## Video Encoding (New Feature!)

The bot now includes **automatic video encoding** to ensure all videos are optimized to **720p quality** with reduced file sizes.

### Key Features:
- ✅ Automatic downscaling to 720p (1280x720)
- ✅ Maintains original aspect ratio
- ✅ Configurable quality settings (CRF 18-28)
- ✅ Typical file size reduction: 30-60%
- ✅ Can be toggled on/off via environment variable

### Quick Configuration:
Add to your `.env` file:
```env
ENABLE_ENCODING=true
MAX_RESOLUTION_WIDTH=1280
ENCODE_CRF=23
ENCODE_PRESET=medium
ENCODE_VIDEO_CODEC=libx264
```

📖 **Full documentation:** See [ENCODING_SETUP.md](ENCODING_SETUP.md) for detailed configuration guide, performance metrics, and troubleshooting.

## AABv2 (Safe Rewrite)

- A new modular version is available under `AABv2/`.
- It loads settings from a `.env` file (no secrets in repo).

### Migrate existing config to .env

1. Ensure `AAB/config.json` contains your current values.
2. Generate a `.env` file at the repo root:

```bash
python scripts/migrate_to_env.py
```

3. Review `.env` and adjust as needed. You can copy `.env.example` as a template.

### Run AABv2 locally

```bash
python -m AABv2
```

### Run AABv2 with Docker

```bash
docker build -f Dockerfile.v2 -t aabv2 .
docker run --env-file .env --name aabv2 --restart unless-stopped aabv2
```

## Notes

- **FFmpeg is required** for video encoding - install via `apt install ffmpeg` (Linux) or download from ffmpeg.org
- **Encoding can be disabled** by setting `ENABLE_ENCODING=false` in `.env`
- **Large files (>2GB)** are automatically split into two parts for upload
- **Disk space:** Ensure sufficient space for temporary video storage during encoding
- The bot workflow is optimized for JAV content processing

## Contributors
| ![**Dhruv-Tara**](https://github.com/Dhruv-Tara.png?size=50) | [**_Dhruv-Tara_**](https://github.com/Dhruv-Tara) |
| --- | --- |
| ![**illuminati-Dev**](https://github.com/illuminati-Dev.png?size=50) | [**_illuminati-Dev_**](https://github.com/illuminati-Dev) |
| --- | --- |
| ![**Qewertyy**](https://github.com/Qewertyy.png?size=50) | [**_Qewertyy_**](https://github.com/Qewertyy) |


## Support and Contribution

For any issues or feature requests, please open an issue on the [GitHub repository](https://github.com/Dhruv-Tara/Auto-Anime-Bot/issues). Contributions are welcome!

## License

This project is licensed under the [GNU General Public License v3.0](https://github.com/Dhruv-Tara/Auto-Anime-Bot/blob/main/LICENSE).
