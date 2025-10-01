"""
encode module removed.

This module previously provided ffmpeg-based encoding helpers. The project has been
configured to skip encoding; if any code still imports these functions they will
raise an explicit error so the issue is obvious at runtime.
"""

def encode_file(*_args, **_kwargs):
    raise RuntimeError("encode_file was removed: encoding is disabled in this build")

def encode_with_crf(*_args, **_kwargs):
    raise RuntimeError("encode_with_crf was removed: encoding is disabled in this build")

def get_video_info(*_args, **_kwargs):
    return {}