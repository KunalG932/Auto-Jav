from typing import Iterable, List, Optional

STAGE_ICONS = {
    "download": "📥",
    "metadata": "📄",
    "encode": "🔄",
    "remux": "🔁",
    "upload": "📤",
    "split": "🔀",
    "cleanup": "🧹",
    "completed": "✅",
}


def _clamp_percent(percent: Optional[float]) -> Optional[float]:
    if percent is None:
        return None
    try:
        value = float(percent)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(100.0, value))


def build_progress_bar(percent: Optional[float], length: int = 20) -> str:
    percent = _clamp_percent(percent)
    if percent is None:
        return ""
    filled = max(0, min(length, int(round(length * percent / 100.0))))
    empty = length - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {percent:.1f}%"


def _stage_header(stage: str, title: str) -> str:
    icon = STAGE_ICONS.get(stage, "ℹ️")
    stage_label = stage.replace("_", " ").title()
    return f"{icon} {stage_label} · {title}"


def format_stage_status(
    stage: str,
    title: str,
    status: Optional[str] = None,
    *,
    percent: Optional[float] = None,
    extra_lines: Optional[Iterable[str]] = None,
    show_bar: bool = True,
) -> str:
    lines: List[str] = [_stage_header(stage, title)]
    if status:
        lines.append(status)

    bar_text = build_progress_bar(percent) if show_bar else ""
    if bar_text:
        lines.append(bar_text)

    if extra_lines:
        for line in extra_lines:
            if line:
                lines.append(line)

    return "\n".join(lines)


def format_download_progress(
    title: str,
    *,
    percent: Optional[float],
    stage: str,
    speed: Optional[float] = None,
    peers: Optional[int] = None,
    elapsed: Optional[int] = None,
) -> str:
    stage_label_map = {
        "metadata": "Gathering metadata",
        "downloading": "Downloading",
        "completed": "Download complete",
    }
    label = stage_label_map.get(stage.lower(), stage.replace("_", " ").title())

    details = []
    if speed is not None:
        details.append(f"Speed: {speed:.1f} kB/s")
    if peers is not None:
        details.append(f"Peers: {int(peers)}")
    if elapsed is not None:
        details.append(f"Elapsed: {elapsed}s")

    return format_stage_status(
        "download",
        title,
        status=label,
        percent=percent,
        extra_lines=details,
        show_bar=True,
    )


def _format_time(seconds: Optional[float]) -> str:
    if seconds is None:
        return "00:00"
    seconds = max(0, int(seconds))
    mins, sec = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours:02d}:{mins:02d}:{sec:02d}"
    return f"{mins:02d}:{sec:02d}"


def format_encoding_progress(
    title: str,
    *,
    percent: Optional[float],
    current_sec: Optional[float],
    total_sec: Optional[float],
    status: str = "Encoding to 720p",
) -> str:
    details = [
        f"Time: {_format_time(current_sec)} / {_format_time(total_sec)}"
    ]
    return format_stage_status(
        "encode",
        title,
        status=status,
        percent=percent,
        extra_lines=details,
        show_bar=True,
    )


def format_upload_status(
    title: str,
    *,
    percent: Optional[float] = None,
    uploaded: Optional[float] = None,
    total: Optional[float] = None,
    status: str = "Uploading",
) -> str:
    details = []
    if uploaded is not None and total:
        details.append(f"Transferred: {uploaded:.2f} / {total:.2f} GB")
    return format_stage_status(
        "upload",
        title,
        status=status,
        percent=percent,
        extra_lines=details,
        show_bar=percent is not None,
    )


def should_emit_progress(
    now: float,
    last_time: float,
    last_percent: float,
    current_percent: Optional[float],
    *,
    min_interval: float = 5.0,
    min_progress: float = 5.0,
    force: bool = False,
) -> bool:
    if force:
        return True

    if current_percent is None:
        return (now - last_time) >= min_interval

    current_percent = _clamp_percent(current_percent) or 0.0

    if current_percent >= 100.0:
        return True

    if (now - last_time) < min_interval and abs(current_percent - last_percent) < min_progress:
        return False

    return True
