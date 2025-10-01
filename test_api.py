#!/usr/bin/env python3
"""
Quick test script to check if the JAV API is accessible
"""
import time
import requests

API_URL = "https://jav-api-w4od.onrender.com/api/latest?limit=10&sort_by_date=true&translate=true"

print("🧪 Testing JAV API Connection")
print(f"📡 URL: {API_URL}\n")

attempts = 3
for attempt in range(1, attempts + 1):
    print(f"Attempt {attempt}/{attempts}...")
    
    try:
        start_time = time.time()
        response = requests.get(
            API_URL,
            timeout=120,
            headers={'User-Agent': 'Auto-JAV-Bot/2.0-Test'}
        )
        elapsed = time.time() - start_time
        
        print(f"✅ Response received in {elapsed:.2f}s")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📦 Data type: {type(data)}")
            
            if isinstance(data, list):
                print(f"✅ Received {len(data)} items")
                
                if data:
                    first_item = data[0]
                    print(f"\n📝 First item sample:")
                    print(f"   Title: {first_item.get('title', 'N/A')}")
                    print(f"   Code: {first_item.get('code', 'N/A')}")
                    print(f"   Actresses: {first_item.get('actresses', [])}")
                    print(f"   Thumbnail: {first_item.get('thumbnail', 'N/A')[:50]}...")
                    
                    torrent_links = first_item.get('torrent_links', [])
                    if torrent_links and isinstance(torrent_links, list):
                        print(f"   Has magnet: {'✅' if torrent_links[0].get('magnet') else '❌'}")
                
                print("\n🎉 API Test PASSED!")
                break
            else:
                print(f"❌ Unexpected data type: {type(data)}")
        else:
            print(f"⚠️ HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️ Request timed out (120s)")
        if attempt < attempts:
            wait = 30 * attempt
            print(f"Waiting {wait}s before retry...\n")
            time.sleep(wait)
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        if attempt < attempts:
            wait = 30 * attempt
            print(f"Waiting {wait}s before retry...\n")
            time.sleep(wait)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        break
else:
    print("\n❌ API Test FAILED - All attempts exhausted")

print("\n" + "="*50)
print("Test complete!")
