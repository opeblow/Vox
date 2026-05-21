import os
import subprocess
import logging
import uuid

logger = logging.getLogger(__name__)


class ClipGenerator:
    @staticmethod
    def extract_clip(audio_path: str, start_time: float, end_time: float, output_dir: str, label: str = "clip") -> str:
        os.makedirs(output_dir, exist_ok=True)
        clip_id = str(uuid.uuid4())[:8]
        output_path = os.path.join(output_dir, f"{label}_{clip_id}.mp3")

        try:
            subprocess.run(
                [
                    "ffmpeg", "-i", audio_path,
                    "-ss", str(start_time),
                    "-to", str(end_time),
                    "-c", "copy",
                    "-y",
                    output_path,
                ],
                check=True, capture_output=True, text=True,
            )
            logger.info(f"Clip extracted: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Clip extraction failed: {e.stderr}")
            raise
        except FileNotFoundError:
            logger.warning("FFmpeg not found, clip extraction unavailable")
            return ""

    @staticmethod
    def extract_key_moment_clips(audio_path: str, key_moments: list[dict], output_dir: str) -> list[dict]:
        clips = []
        for i, moment in enumerate(key_moments[:10]):
            ts = moment.get("timestamp", 0)
            start = max(0, float(ts) - 5)
            end = float(ts) + 15
            label = f"moment_{i+1}"
            try:
                clip_path = ClipGenerator.extract_clip(audio_path, start, end, output_dir, label)
                if clip_path:
                    clips.append({"index": i + 1, "quote": moment.get("quote", ""), "path": clip_path, "start": start, "end": end})
            except Exception as e:
                logger.warning(f"Failed to extract clip {i}: {e}")
        return clips
