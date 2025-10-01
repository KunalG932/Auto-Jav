# Auto JAV Bot
<div align="center">
  <img src="https://graph.org/file/8bb750efbe7f08176e2ae.png" alt="Auto JAV Bot">
</div>

Auto JAV Bot is a Telegram bot that automatically discovers and uploads JAV releases to a Telegram channel. It integrates with an external API to fetch new items, downloads via magnet when available, and posts a channel message containing Magnet/Torrent links. Users can retrieve uploaded files via deep-link buttons.


## Features

- Automatic discovery of new JAV items via API.
- Magnet-based downloading and upload to a files channel.
- Single "Download Now" deep-link button (no external Magnet/Torrent buttons).
- Deep-link button to receive the uploaded file in DM.
- Update channel receives either the message link of the posted video or "Notfile" when no file was uploaded.

## Requirements

- VPS or machine with Python 3.11.
- MongoDB (for state and file index).
- System libtorrent (python3-libtorrent) available.

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
   - Create your Telegram bots and obtain API credentials.
   - Fill `AAB/config.json` with required values:
     - `production_chat`, `files_channel`, `main_channel`, `owner`, `database_url`, `api_id`, `api_hash`, `main_bot`, `client_bot`, `thumbnail_url`.

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
   - Users can tap the "Get File" button in the channel post (deep-links to `/start <hash>`), and the bot forwards the file from the files channel.

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

- Ensure libtorrent is installed and accessible.
- The bot no longer performs anime-specific auto-downloads or encoding; the workflow is focused on JAV items.

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
