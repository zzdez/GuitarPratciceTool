import urllib.request
import re

req = urllib.request.Request(
    "https://www.songsterr.com/",
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
)
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        print("HTML LENGTH:", len(html))
        match = re.search(r'"user":\s*(\{.*?\})', html)
        if match:
            print("USER REGEX MATCH:", match.group(1)[:1000])
        else:
            print("USER REGEX NOT FOUND")
            # print first 500 chars to check
            print(html[:500])
except Exception as e:
    print("ERROR:", e)
