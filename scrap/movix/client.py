"""
client.py - Requêtes HTTP, constantes globales et résolution de domaine pour movix.

Ce module est le seul à initialiser les variables globales de domaine.
Il est importé par tous les autres modules du package movix.
"""
import re
import json
import urllib.request
import urllib.parse
import sys

# Clé API TMDB publique utilisée par le frontend movix.chat
TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"
TMDB_API_BASE = "https://api.themoviedb.org/3"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://movix.online",
    "Referer": "https://movix.online/",
    "Connection": "keep-alive",
}


def get_active_domain():
    """
    Résout dynamiquement le domaine actif via movix.online.
    Cherche un lien href pointant vers movix.* dans la page d'accueil.
    """
    fallback = "movix.date"
    req = urllib.request.Request("https://movix.online", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            match = re.search(
                r'href=["\'](https?://(?:www\.)?movix\.[a-z0-9]+)["\']', html
            )
            if match:
                domain_url = match.group(1)
                parsed = urllib.parse.urlparse(domain_url)
                if parsed.netloc:
                    return parsed.netloc
    except Exception as e:
        print(
            f"[movix] Impossible de résoudre le domaine via movix.online ({e}), fallback vers {fallback}",
            file=sys.stderr,
        )
    return fallback


# Résolution au moment de l'import (une seule fois par process)
ACTIVE_DOMAIN = get_active_domain()
API_BASE = f"https://api.{ACTIVE_DOMAIN}"
SITE_URL = f"https://{ACTIVE_DOMAIN}"


def make_request(url, headers=None):
    """Effectue une requête HTTP GET et retourne le texte brut."""
    dynamic_headers = {
        "Origin": SITE_URL,
        "Referer": SITE_URL + "/",
    }
    req_headers = {**HEADERS, **dynamic_headers, **(headers or {})}
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[movix] Erreur fetch {url}: {e}", file=sys.stderr)
        return ""


def fetch_json(url, headers=None):
    """Effectue une requête HTTP GET et retourne le JSON parsé (ou None)."""
    text = make_request(url, headers)
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None
