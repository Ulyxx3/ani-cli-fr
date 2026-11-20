"""
client.py - Requêtes HTTP et résolution de domaine pour anime-sama.
"""
import urllib.error
import urllib.parse
import urllib.request
import sys

HEADERS_BASE = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "connection": "keep-alive",
}

_CACHED_DOMAIN = None


def make_request_with_url(url, params=None, referer=None, silent_404=False):
    """
    Effectue une requête HTTP GET et retourne (final_url, texte_brut).
    Retourne ("", "") en cas d'erreur.
    """
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = dict(HEADERS_BASE)
    parsed = urllib.parse.urlparse(url)
    headers["Referer"] = referer if referer is not None else f"{parsed.scheme}://{parsed.netloc}/"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            final_url = response.geturl() or url
            body = response.read().decode("utf-8", errors="ignore")
            return final_url, body
    except urllib.error.HTTPError as e:
        if not (silent_404 and e.code == 404):
            print(f"Error fetching {url}: {e}", file=sys.stderr)
        return "", ""
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return "", ""


def make_request(url, params=None, referer=None, silent_404=False):
    """Effectue une requête HTTP GET et retourne le texte brut."""
    _, body = make_request_with_url(
        url, params=params, referer=referer, silent_404=silent_404
    )
    return body


def get_active_domain():
    """
    Résout dynamiquement le domaine actif parmi les domaines anime-sama connus.
    Met en cache le domaine trouvé pour la durée du processus.
    """
    global _CACHED_DOMAIN
    if _CACHED_DOMAIN:
        return _CACHED_DOMAIN

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
                    _CACHED_DOMAIN = urllib.parse.urlparse(url).netloc
                    return _CACHED_DOMAIN
        except Exception:
            pass

    _CACHED_DOMAIN = "anime-sama.to"
    return _CACHED_DOMAIN
