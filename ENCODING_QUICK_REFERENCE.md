# 🎬 Video Encoding Quick Reference

## 🚀 Quick Start (3 Steps)

1. **Install FFmpeg**
   ```bash
   # Linux
   sudo apt install ffmpeg
   
   # Windows (Chocolatey)
   choco install ffmpeg
   ```

2. **Configure .env**
   ```env
   ENABLE_ENCODING=true
   MAX_RESOLUTION_WIDTH=1280
   ENCODE_CRF=23
   ENCODE_PRESET=medium
   ```

3. **Run Bot**
   ```bash
   python -m AABv2
   ```

---

## ⚙️ Common Configurations

### 🎯 Default (Recommended)
```env
ENABLE_ENCODING=true
ENCODE_CRF=23
ENCODE_PRESET=medium
ENCODE_VIDEO_CODEC=libx264
```
**Best for:** General use, balanced quality/size/speed

### 💎 High Quality
```env
ENCODE_CRF=20
ENCODE_PRESET=slow
```
**Best for:** Premium content, archival

### 🚀 Fast Processing
```env
ENCODE_CRF=26
ENCODE_PRESET=fast
```
**Best for:** High volume, quick turnaround

### 📦 Maximum Compression
```env
ENCODE_CRF=26
ENCODE_VIDEO_CODEC=libx265
ENCODE_PRESET=medium
```
**Best for:** Storage-constrained environments

### 🔌 GPU Accelerated (NVIDIA)
```env
ENCODE_VIDEO_CODEC=h264_nvenc
ENCODE_PRESET=fast
```
**Best for:** Fastest encoding with NVIDIA GPU

---

## 🎛️ Settings Explained

### CRF (Quality)
| Value | Quality | File Size | Use Case |
|-------|---------|-----------|----------|
| 18    | Excellent | Large | Archival |
| 20    | Very Good | Medium-Large | Premium |
| 23    | Good (default) | Medium | General |
| 26    | Acceptable | Small | Storage-limited |
| 28    | Fair | Very Small | Low priority |

### Preset (Speed)
| Preset | Speed | File Size | Quality |
|--------|-------|-----------|---------|
| ultrafast | Fastest | Largest | Lower |
| fast | Fast | Large | Good |
| medium | Moderate | Medium | Good |
| slow | Slow | Small | Better |
| veryslow | Slowest | Smallest | Best |

### Video Codec
| Codec | Compatibility | Compression | Speed |
|-------|---------------|-------------|-------|
| libx264 | Excellent | Good | Fast |
| libx265 | Good | Excellent | Slow |
| h264_nvenc | Excellent | Good | Very Fast (GPU) |

---

## 🔍 Troubleshooting

### Problem: Encoding is slow
```env
# Solution 1: Faster preset
ENCODE_PRESET=fast

# Solution 2: Use GPU (if available)
ENCODE_VIDEO_CODEC=h264_nvenc
```

### Problem: Files too large
```env
# Solution: Higher CRF (lower quality)
ENCODE_CRF=26
```

### Problem: Poor quality
```env
# Solution: Lower CRF (higher quality)
ENCODE_CRF=20
ENCODE_PRESET=slow
```

### Problem: Disable encoding temporarily
```env
ENABLE_ENCODING=false
```

---

## 📊 Expected Results

### File Size Reduction (1080p → 720p)
| Original | CRF 20 | CRF 23 | CRF 26 |
|----------|--------|--------|--------|
| 3.0 GB   | 1.8 GB | 1.5 GB | 1.2 GB |
| 2.0 GB   | 1.2 GB | 1.0 GB | 800 MB |
| 1.0 GB   | 600 MB | 500 MB | 400 MB |

### Encoding Time (2GB video)
| Preset | Time |
|--------|------|
| fast   | ~8 min |
| medium | ~12 min |
| slow   | ~18 min |

---

## 🎯 Resolution Behavior

| Input | Output | Action |
|-------|--------|--------|
| 3840x2160 (4K) | 1280x720 | ⬇️ Downscaled |
| 1920x1080 (FHD) | 1280x720 | ⬇️ Downscaled |
| 1280x720 (HD) | 1280x720 | 🔄 Re-encoded |
| 854x480 (SD) | 854x480 | 🔄 Re-encoded |

*Note: Videos are never upscaled, only downscaled or re-encoded*

---

## 📝 Progress Messages

What users see:
```
📥 Downloading: [Video Title]
✅ Download complete
🔁 Remuxing .ts → .mp4
🔄 Encoding to 720p: video.mp4
✅ Encoded to 720p: video_encoded.mp4
📤 Uploading...
```

---

## 🧪 Testing Commands

### Check FFmpeg installation
```bash
ffmpeg -version
```

### Test encoding manually
```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium -vf "scale='min(1280,iw)':-2" -c:a aac -b:a 128k output.mp4
```

### Check video info
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json input.mp4
```

---

## 🔗 More Information

- 📖 **Full Guide:** [ENCODING_SETUP.md](ENCODING_SETUP.md)
- 📊 **Implementation:** [VIDEO_ENCODING_IMPLEMENTATION.md](VIDEO_ENCODING_IMPLEMENTATION.md)
- 📘 **Main Docs:** [README.md](README.md)

---

## 💡 Pro Tips

1. **Start with defaults** - Don't optimize prematurely
2. **Monitor first encodes** - Check quality and size
3. **Adjust incrementally** - Change one setting at a time
4. **Test with samples** - Before processing large batches
5. **Keep logs** - Useful for troubleshooting

---

## ✅ Verification Checklist

After setup, verify:
- [ ] FFmpeg installed and working
- [ ] `.env` configured with encoding settings
- [ ] Bot runs without errors
- [ ] First video encodes successfully
- [ ] Output resolution is ≤ 720p
- [ ] File size is reduced
- [ ] Video quality is acceptable

---

**Quick Help:**
- FFmpeg not found? → Install from ffmpeg.org
- Encoding too slow? → Use `ENCODE_PRESET=fast`
- Files too large? → Increase `ENCODE_CRF` to 26
- Need to disable? → Set `ENABLE_ENCODING=false`
