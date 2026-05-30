import os
import uuid
import logging
import yt_dlp

logger = logging.getLogger(__name__)

def download_audio(url: str, output_dir: str) -> tuple[str, str]:
    temp_id = str(uuid.uuid4())[:8]
    out_dir = os.path.join(output_dir, temp_id)
    os.makedirs(out_dir, exist_ok=True)

    safe_name = f"audio_{temp_id}"
    output_template = os.path.join(out_dir, f"{safe_name}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "audio")

    mp3_files = [f for f in os.listdir(out_dir) if f.endswith(".mp3")]
    if not mp3_files:
        raise FileNotFoundError(f"No MP3 file found after downloading {url}")

    audio_path = os.path.join(out_dir, mp3_files[0])
    return audio_path, title
