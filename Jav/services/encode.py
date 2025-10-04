from os import path as ospath, makedirs
from aiofiles.os import rename as aiorename
from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE
import glob
import logging

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
    def __init__(self, path, name):
        self.__proc = None
        self.is_cancelled = False
        self.__name = name
        self.dl_path = path
        self.out_path = ospath.join("encode", name)

    async def start_encode(self):
        dl_npath = ospath.join("encode", "ffanimeadvin.mkv")
        out_npath = ospath.join("encode", "ffanimeadvout.mkv")

        try:
            if ospath.isdir(self.dl_path):
                files = glob.glob(ospath.join(self.dl_path, "*.mkv")) + glob.glob(ospath.join(self.dl_path, "*.mp4"))
                if not files:
                    LOG.error(f"❌ No video file found inside directory: {self.dl_path}")
                    raise FileNotFoundError(f"No video file found inside directory: {self.dl_path}")
                video_file = files[0]
            else:
                video_file = self.dl_path

            LOG.info(f"🔄 Renaming input: {video_file} -> {dl_npath}")
            await aiorename(video_file, dl_npath)

            ffcode = (
                f"ffmpeg -hide_banner -loglevel error -i '{dl_npath}' "
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

            LOG.info(f"🎬 Starting FFmpeg encoding...")
            LOG.debug(f"FFmpeg command: {ffcode}")
            
            self.__proc = await create_subprocess_shell(ffcode, stdout=PIPE, stderr=PIPE)
            stdout, stderr = await self.__proc.communicate()

            LOG.info(f"🔄 Renaming back: {dl_npath} -> {video_file}")
            await aiorename(dl_npath, video_file)

            if self.is_cancelled:
                LOG.warning("⚠️ Encoding was cancelled")
                return None

            if self.__proc.returncode == 0 and ospath.exists(out_npath):
                LOG.info(f"✅ FFmpeg completed successfully, renaming output: {out_npath} -> {self.out_path}")
                await aiorename(out_npath, self.out_path)
                return self.out_path
            else:
                LOG.error(f"❌ FFmpeg failed with return code: {self.__proc.returncode}")
                if stderr:
                    LOG.error(f"FFmpeg stderr: {stderr.decode('utf-8', errors='ignore')}")
                if stdout:
                    LOG.info(f"FFmpeg stdout: {stdout.decode('utf-8', errors='ignore')}")
                return None
                
        except Exception as e:
            LOG.error(f"❌ Encoding exception: {e}", exc_info=True)
            # Try to restore original file if it was renamed
            try:
                if ospath.exists(dl_npath) and not ospath.exists(self.dl_path):
                    await aiorename(dl_npath, self.dl_path)
                    LOG.info(f"🔄 Restored original file: {self.dl_path}")
            except Exception as restore_error:
                LOG.error(f"Failed to restore original file: {restore_error}")
            return None

    async def cancel_encode(self):
        self.is_cancelled = True
        if self.__proc is not None:
            try:
                self.__proc.kill()
            except:
                pass