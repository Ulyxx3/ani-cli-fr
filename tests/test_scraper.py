import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re

HEADERS_BASE = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "connection": "keep-alive"
}

def make_request(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS_BASE)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def get_active_domain():
    try:
        html = make_request("https://anime-sama.pw")
        match = re.search(r"return\s+['\"](anime-sama\.[a-z]+)['\"]", html)
        if match:
            return match.group(1)
    except:
        pass
    return "anime-sama.si"

domain = get_active_domain()
print(f"Active domain: {domain}")
url = f"https://{domain}/catalogue/"
params = {"search": "jujutsu kaisen"}
html = make_request(url, params)
print(f"HTML length: {len(html)}")
soup = BeautifulSoup(html, 'html.parser')
cards = soup.find_all('a', href=True)
print(f"Found {len(cards)} links")
for card in cards[:5]:
    h1 = card.find('h1')
    print(f"Href: {card['href']}, H1: {h1.text if h1 else 'None'}")
