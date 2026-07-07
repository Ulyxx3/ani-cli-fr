"""
client.py - Requêtes HTTP et résolution de domaine pour anime-sama.
"""
import urllib.request
import urllib.parse
import sys

HEADERS_BASE = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "connection": "keep-alive",
}


def make_request(url, params=None):
    """Effectue une requête HTTP GET et retourne le texte brut."""
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS_BASE)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return ""


def get_active_domain():
    """
    Résout dynamiquement le domaine actif parmi les domaines anime-sama connus.
    Retourne le premier domaine qui répond avec '/catalogue/' dans son URL.
    """
    domains = [
        "anime-sama.to",
        "anime-sama.tv",
        "anime-sama.si",
        "anime-sama.fr",
        "anime-sama.org",
        "anime-sama.net",
    ]
    for domain in domains:
        try:
            req = urllib.request.Request(
                f"https://{domain}/catalogue/", headers=HEADERS_BASE
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                url = response.geturl()
                if "catalogue" in url:
                    return urllib.parse.urlparse(url).netloc
        except Exception:
            pass
    return "anime-sama.to"
