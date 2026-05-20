import requests

res = requests.get("https://www.songsterr.com/", headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})
print("STATUS CODE:", res.status_code)
print("HEADERS:", res.headers)
