#!/usr/bin/env python3
"""
Test script for video encoding functionality.
This script verifies that the encoding module works correctly.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    print("🔍 Checking FFmpeg installation...")
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg found: {version_line}")
            return True
        else:
            print("❌ FFmpeg not working properly")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found. Please install FFmpeg:")
        print("   Linux: sudo apt install ffmpeg")
        print("   Windows: choco install ffmpeg")
        print("   macOS: brew install ffmpeg")
        return False
    except Exception as e:
        print(f"❌ Error checking FFmpeg: {e}")
        return False

def check_imports():
    """Check if all required modules can be imported."""
    print("\n🔍 Checking Python imports...")
    try:
        from AABv2.config import SETTINGS
        print("✅ Config module imported")
        
        from AABv2.services.encode import encode_file, get_video_info, encode_with_crf
        print("✅ Encode module imported")
        
        print(f"\n📋 Current encoding settings:")
        print(f"   Enable encoding: {SETTINGS.enable_encoding}")
        print(f"   Max resolution: {SETTINGS.max_resolution_width}x{SETTINGS.max_resolution_height}")
        print(f"   CRF: {SETTINGS.encode_crf}")
        print(f"   Preset: {SETTINGS.encode_preset}")
        print(f"   Video codec: {SETTINGS.encode_video_codec}")
        print(f"   Audio codec: {SETTINGS.encode_audio_codec}")
        print(f"   Audio bitrate: {SETTINGS.encode_audio_bitrate}")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_test_video():
    """Create a small test video using FFmpeg."""
    print("\n🎬 Creating test video...")
    test_video = "test_input.mp4"
    
    if os.path.exists(test_video):
        print(f"✅ Test video already exists: {test_video}")
        return test_video
    
    try:
        # Create a 5-second 1920x1080 test video
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'testsrc=duration=5:size=1920x1080:rate=30',
            '-f', 'lavfi',
            '-i', 'sine=frequency=1000:duration=5',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-c:a', 'aac',
            test_video
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(test_video):
            size_mb = os.path.getsize(test_video) / (1024 * 1024)
            print(f"✅ Test video created: {test_video} ({size_mb:.2f} MB)")
            return test_video
        else:
            print(f"❌ Failed to create test video")
            print(f"   stderr: {result.stderr.decode()[:200]}")
            return None
    except Exception as e:
        print(f"❌ Error creating test video: {e}")
        return None

def test_get_video_info(video_file):
    """Test get_video_info function."""
    print(f"\n🔍 Testing get_video_info()...")
    try:
        from AABv2.services.encode import get_video_info
        
        info = get_video_info(video_file)
        
        if info:
            print("✅ get_video_info() successful")
            print(f"   Width: {info.get('width', 'N/A')}")
            print(f"   Height: {info.get('height', 'N/A')}")
            print(f"   Duration: {info.get('duration', 'N/A')}s")
            print(f"   Bitrate: {info.get('bit_rate', 'N/A')} bps")
            return True
        else:
            print("❌ get_video_info() returned empty dict")
            return False
    except Exception as e:
        print(f"❌ Error in get_video_info(): {e}")
        return False

def test_encode_file(video_file):
    """Test encode_file function."""
    print(f"\n🎬 Testing encode_file()...")
    try:
        from AABv2.services.encode import encode_file
        
        output_file = "test_output_encoded.mp4"
        
        # Remove old output if exists
        if os.path.exists(output_file):
            os.remove(output_file)
        
        print("   Encoding (this may take a moment)...")
        result = encode_file(video_file, output_file)
        
        if result and os.path.exists(result):
            input_size = os.path.getsize(video_file) / (1024 * 1024)
            output_size = os.path.getsize(result) / (1024 * 1024)
            reduction = ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
            
            print("✅ encode_file() successful")
            print(f"   Input: {input_size:.2f} MB")
            print(f"   Output: {output_size:.2f} MB")
            print(f"   Reduction: {reduction:+.1f}%")
            
            # Check resolution
            from AABv2.services.encode import get_video_info
            output_info = get_video_info(result)
            if output_info:
                width = output_info.get('width', 0)
                height = output_info.get('height', 0)
                print(f"   Output resolution: {width}x{height}")
                
                if width <= 1280 and height <= 720:
                    print("   ✅ Resolution is 720p or less")
                else:
                    print("   ⚠️ Resolution exceeds 720p")
            
            return True
        else:
            print("❌ encode_file() failed or output not created")
            return False
    except Exception as e:
        print(f"❌ Error in encode_file(): {e}")
        import traceback
        traceback.print_exc()
        return False

def test_encode_with_crf(video_file):
    """Test encode_with_crf function."""
    print(f"\n🎬 Testing encode_with_crf()...")
    try:
        from AABv2.services.encode import encode_with_crf
        
        output_file = "test_output_crf28.mp4"
        
        # Remove old output if exists
        if os.path.exists(output_file):
            os.remove(output_file)
        
        print("   Encoding with CRF=28 (this may take a moment)...")
        result = encode_with_crf(video_file, crf=28, output_path=output_file)
        
        if result and os.path.exists(result):
            output_size = os.path.getsize(result) / (1024 * 1024)
            print("✅ encode_with_crf() successful")
            print(f"   Output: {output_size:.2f} MB")
            return True
        else:
            print("❌ encode_with_crf() failed or output not created")
            return False
    except Exception as e:
        print(f"❌ Error in encode_with_crf(): {e}")
        return False

def cleanup():
    """Remove test files."""
    print("\n🧹 Cleaning up test files...")
    test_files = [
        "test_input.mp4",
        "test_output_encoded.mp4",
        "test_output_crf28.mp4"
    ]
    
    for file in test_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"   Removed: {file}")
        except Exception as e:
            print(f"   Failed to remove {file}: {e}")

def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 VIDEO ENCODING TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Check FFmpeg
    results.append(("FFmpeg Installation", check_ffmpeg()))
    
    if not results[0][1]:
        print("\n❌ Cannot continue without FFmpeg. Please install it first.")
        return False
    
    # Test 2: Check imports
    results.append(("Python Imports", check_imports()))
    
    if not results[1][1]:
        print("\n❌ Cannot continue with import errors.")
        return False
    
    # Test 3: Create test video
    test_video = create_test_video()
    if test_video:
        results.append(("Test Video Creation", True))
    else:
        results.append(("Test Video Creation", False))
        print("\n❌ Cannot continue without test video.")
        return False
    
    # Test 4: get_video_info
    results.append(("get_video_info()", test_get_video_info(test_video)))
    
    # Test 5: encode_file
    results.append(("encode_file()", test_encode_file(test_video)))
    
    # Test 6: encode_with_crf
    results.append(("encode_with_crf()", test_encode_with_crf(test_video)))
    
    # Cleanup
    cleanup()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 All tests passed! Encoding is working correctly.")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
