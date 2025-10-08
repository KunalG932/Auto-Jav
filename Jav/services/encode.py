from os import path as ospath, makedirs
from aiofiles.os import rename as aiorename
from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE
import glob
import re
import logging
from typing import Optional, Callable
import asyncio

LOG = logging.getLogger("Jav")

FFARGS_720P = (
    "-c:v libx264 -preset veryfast -crf 28 "
    "-pix_fmt yuv420p -movflags +faststart "
    "-c:a libopus -b:a 80k -vbr on -c:s copy"
)

SCALE_720P = "scale=1280:720"

if not ospath.exists("encode"):
    makedirs("encode", exist_ok=True)

class FFEncoder:
    def __init__(self, path, name, progress_callback: Optional[Callable] = None):
        self.__proc = None
        self.is_cancelled = False
        self.__name = name
        self.dl_path = path
        self.out_path = ospath.join("encode", name)
        self.progress_callback = progress_callback

    async def start_encode(self):
        dl_npath = ospath.join("encode", "ffanimeadvin.mkv")
        out_npath = ospath.join("encode", "ffanimeadvout.mkv")

        if ospath.isdir(self.dl_path):
            files = glob.glob(ospath.join(self.dl_path, "*.mkv")) + glob.glob(ospath.join(self.dl_path, "*.mp4"))
            if not files:
                raise FileNotFoundError(f"No video file found inside directory: {self.dl_path}")
            video_file = files[0]
        else:
            video_file = self.dl_path

        await aiorename(video_file, dl_npath)
        
        duration_seconds = await self._get_video_duration(dl_npath)
        LOG.info(f"Video duration: {duration_seconds}s")

        ffcode = (
            f"ffmpeg -hide_banner -progress pipe:1 -i '{dl_npath}' "
            f"-vf '{SCALE_720P}:flags=fast_bilinear' "
            f"-map 0:v -map 0:a -map 0:s? "
            f"{FFARGS_720P} "
            f"-metadata title='@The_Wyverns' "
            f"-metadata author='@The_Wyverns' "
            f"-metadata artist='@The_Wyverns' "
            f"-metadata album='@The_Wyverns' "
            f"-metadata description='Encoded by @The_Wyverns' "
            f"-metadata comment='@The_Wyverns' "
            f"-metadata:s:s title='@The_Wyverns' "
            f"-metadata:s:a title='@The_Wyverns' "
            f"-metadata:s:v title='@The_Wyverns' "
            f"'{out_npath}' -y"
        )

        self.__proc = await create_subprocess_shell(ffcode, stdout=PIPE, stderr=PIPE)
        
        if self.progress_callback and duration_seconds:
            asyncio.create_task(self._monitor_progress(self.__proc.stdout, duration_seconds))
        
        await self.__proc.wait()

        await aiorename(dl_npath, self.dl_path)

        if self.is_cancelled:
            return None

        if self.__proc.returncode == 0 and ospath.exists(out_npath):
            await aiorename(out_npath, self.out_path)
            return self.out_path
        else:
            return None
    
    async def _get_video_duration(self, video_path: str) -> Optional[float]:
        try:
            cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{video_path}'"
            proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
            stdout, _ = await proc.communicate()
            duration = float(stdout.decode().strip())
            return duration
        except Exception as e:
            LOG.warning(f"Failed to get video duration: {e}")
            return None
    
    async def _monitor_progress(self, stdout, total_duration: float):
        try:
            buffer = ""
            while True:
                chunk = await stdout.read(1024)
                if not chunk:
                    break
                
                buffer += chunk.decode('utf-8', errors='ignore')
                lines = buffer.split('\n')
                buffer = lines[-1]
                
                for line in lines[:-1]:
                    if line.startswith('out_time_ms='):
                        try:
                            time_ms = int(line.split('=')[1])
                            current_seconds = time_ms / 1000000.0
                            progress_pct = min((current_seconds / total_duration) * 100, 100.0)
                            
                            if self.progress_callback:
                                await self.progress_callback(progress_pct, current_seconds, total_duration)
                        except Exception as e:
                            LOG.debug(f"Progress parse error: {e}")
                            
        except Exception as e:
            LOG.warning(f"Progress monitoring error: {e}")

    async def cancel_encode(self):
        self.is_cancelled = True
        if self.__proc is not None:
            try:
                self.__proc.kill()
            except:
                pass