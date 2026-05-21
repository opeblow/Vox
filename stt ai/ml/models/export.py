import json
import os


class ExportEngine:
    @staticmethod
    def to_srt(segments: list[dict]) -> str:
        lines = []
        for i, seg in enumerate(segments, 1):
            start = ExportEngine._seconds_to_srt_time(seg["start"])
            end = ExportEngine._seconds_to_srt_time(seg["end"])
            text = seg.get("labeled_text", seg["text"])
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def to_vtt(segments: list[dict]) -> str:
        lines = ["WEBVTT", ""]
        for seg in segments:
            start = ExportEngine._seconds_to_vtt_time(seg["start"])
            end = ExportEngine._seconds_to_vtt_time(seg["end"])
            text = seg.get("labeled_text", seg["text"])
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def to_txt(segments: list[dict], speaker_labels: bool = True) -> str:
        if speaker_labels:
            return "\n".join([s.get("labeled_text", s["text"]) for s in segments])
        return " ".join([s["text"] for s in segments])

    @staticmethod
    def to_markdown(segments: list[dict], summary: str = "", chapters: list[dict] = None) -> str:
        lines = ["# Podcast Transcript", ""]
        if summary:
            lines.append("## Summary")
            lines.append(summary)
            lines.append("")
        if chapters:
            lines.append("## Chapters")
            for ch in chapters:
                start = ExportEngine._format_timestamp(ch.get("start_time", 0))
                lines.append(f"- **{ch.get('title', 'Untitled')}** ({start})")
                if ch.get("description"):
                    lines.append(f"  - {ch['description']}")
            lines.append("")
        lines.append("## Transcript")
        lines.append("")
        for seg in segments:
            ts = ExportEngine._format_timestamp(seg["start"])
            lines.append(f"**[{ts}]** {seg.get('labeled_text', seg['text'])}")
        return "\n".join(lines)

    @staticmethod
    def to_json(segments: list[dict], metadata: dict = None) -> str:
        output = {"segments": segments}
        if metadata:
            output["metadata"] = metadata
        return json.dumps(output, indent=2)

    @staticmethod
    def save_export(segments: list[dict], output_dir: str, basename: str, formats: list[str], metadata: dict = None):
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        for fmt in formats:
            if fmt == "srt":
                content = ExportEngine.to_srt(segments)
                ext = ".srt"
            elif fmt == "vtt":
                content = ExportEngine.to_vtt(segments)
                ext = ".vtt"
            elif fmt == "txt":
                content = ExportEngine.to_txt(segments)
                ext = ".txt"
            elif fmt == "md":
                content = ExportEngine.to_markdown(segments, summary=(metadata or {}).get("summary", ""), chapters=(metadata or {}).get("chapters"))
                ext = ".md"
            elif fmt == "json":
                content = ExportEngine.to_json(segments, metadata)
                ext = ".json"
            else:
                continue
            path = os.path.join(output_dir, f"{basename}{ext}")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            results[fmt] = path
        return results

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    @staticmethod
    def _seconds_to_vtt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"
