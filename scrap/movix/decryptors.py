"""
decryptors.py - Algorithmes d'extraction et de déchiffrement pour les lecteurs vidéo movix.

Contient :
  - extract_sibnet    : lecteur Sibnet (redirection MP4)
  - extract_vidmoly   : lecteur Vidmoly (M3U8)
  - extract_byse      : lecteurs Byse/SeekStreaming (AES-GCM v2 + AES-CBC v1)
  - extract_direct    : lecteur embed générique (fallback M3U8)
  - _follow_redirect  : utilitaire de suivi de redirection HTTP
"""
import re
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
import sys

from .client import make_request, HEADERS


# ---------------------------------------------------------------------------
#  Sibnet
# ---------------------------------------------------------------------------

def extract_sibnet(video_id):
    """
    Extrait le lien MP4 direct depuis sibnet en suivant la redirection 302.
    Retourne l'URL ou None en cas d'échec.
    """
    url = f"https://video.sibnet.ru/shell.php?videoid={video_id}"
    html = make_request(url, headers={"Referer": "https://video.sibnet.ru/"})
    if not html:
        return None

    m = re.search(r'player\.src\(\[\{src:\s*["\']\/v\/([^/]+)\/', html)
    if not m:
        m = re.search(r'"src"\s*:\s*"/v/([^/]+)', html)
    if not m:
        m = re.search(r'src:\s*["\']\/v\/([^/]+)\/(\d+)\.mp4', html)
        if m:
            video_hash = m.group(1)
            mp4_url = f"https://video.sibnet.ru/v/{video_hash}/{video_id}.mp4"
            return _follow_redirect(mp4_url, "https://video.sibnet.ru/")

    if not m:
        return None

    video_hash = m.group(1)
    mp4_url = f"https://video.sibnet.ru/v/{video_hash}/{video_id}.mp4"
    return _follow_redirect(mp4_url, "https://video.sibnet.ru/")


# ---------------------------------------------------------------------------
#  Vidmoly
# ---------------------------------------------------------------------------

def extract_vidmoly(video_id):
    """
    Extrait le lien M3U8 depuis vidmoly (essaie .to puis .net).
    Retourne l'URL ou l'URL embed en fallback.
    """
    for domain in ["vidmoly.to", "vidmoly.net"]:
        embed_url = f"https://{domain}/embed-{video_id}.html"
        html = make_request(embed_url, headers={"Referer": f"https://{domain}/"})
        if not html:
            continue

        patterns = [
            r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pattern in patterns:
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if m:
                video_url = m.group(1)
                if video_url.startswith("//"):
                    video_url = "https:" + video_url
                return video_url

    return f"https://vidmoly.to/embed-{video_id}.html"


# ---------------------------------------------------------------------------
#  Byse / SeekStreaming  (AES-GCM v2 + AES-CBC v1)
# ---------------------------------------------------------------------------

def extract_byse(embed_url):
    """
    Extrait l'URL m3u8 directe depuis un lecteur Byse/SeekStreaming.

    Stratégie 1 (nouvelle API) : AES-GCM avec key_parts + iv + payload.
    Stratégie 2 (ancienne API) : AES-CBC avec clé/IV fixes.

    Supporte : embedseek, seekplayer, seeks.cloud, seekplays, embed4me, bysebuho, …
    """
    from Crypto.Cipher import AES

    def decode_base64_url(s):
        s = s.replace("-", "+").replace("_", "/")
        padding = len(s) % 4
        if padding:
            s += "=" * (4 - padding)
        return base64.b64decode(s)

    # --- Extraction de l'identifiant vidéo et du domaine ---
    decoded = urllib.parse.unquote(embed_url)
    video_id = None
    if "#" in decoded:
        video_id = decoded.split("#")[-1].strip()
    elif "/embed/" in decoded.lower():
        video_id = decoded.rstrip("/").split("/")[-1].strip()
    elif "/e/" in decoded.lower():
        video_id = decoded.rstrip("/").split("/")[-1].strip()
    else:
        try:
            parsed = urllib.parse.urlparse(decoded)
            if parsed.fragment:
                video_id = parsed.fragment.strip()
            elif parsed.path and parsed.path != "/":
                video_id = parsed.path.rstrip("/").split("/")[-1].strip()
        except Exception:
            pass

    if not video_id:
        return embed_url

    try:
        parsed_url = urllib.parse.urlparse(decoded)
        api_domain = parsed_url.netloc or "bysebuho.com"
    except Exception:
        api_domain = "bysebuho.com"

    # --- Stratégie 1 : Nouvelle API AES-GCM ---
    api_url_new = f"https://{api_domain}/api/videos/{video_id}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://{api_domain}/",
    }
    try:
        req = urllib.request.Request(api_url_new, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        playback = data.get("playback", {})
        if playback and "payload" in playback:
            version = playback.get("version")
            key_parts = playback.get("key_parts", [])
            iv_bytes = decode_base64_url(playback.get("iv", ""))
            payload_bytes = decode_base64_url(playback.get("payload", ""))

            # Table de correspondance version → indices de key_parts
            vi = {str(n): [n, 31 - n] for n in range(1, 21)}
            indices = vi.get(version, [])
            selected_parts = [
                key_parts[idx - 1] for idx in indices if 1 <= idx <= len(key_parts)
            ]

            key_bytes = b""
            for part in selected_parts:
                key_bytes += decode_base64_url(part)

            if len(key_bytes) in (16, 24, 32):
                tag_len = 16
                ciphertext = payload_bytes[:-tag_len]
                tag = payload_bytes[-tag_len:]
                cipher = AES.new(key_bytes, AES.MODE_GCM, nonce=iv_bytes)
                decrypted_text = cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
                sources = json.loads(decrypted_text).get("sources", [])
                if sources:
                    video_url = sources[0].get("url", "")
                    if video_url:
                        return video_url
    except Exception:
        pass  # Fallback vers la stratégie 2

    # --- Stratégie 2 : Ancienne API AES-CBC ---
    api_url_old = f"https://{api_domain}/api/v1/video?id={video_id}&w=1920&h=1080&r="
    headers_old = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": f"https://{api_domain}/",
        "Origin": f"https://{api_domain}",
    }
    try:
        import binascii
        from Crypto.Util.Padding import unpad

        req = urllib.request.Request(api_url_old, headers=headers_old)
        with urllib.request.urlopen(req, timeout=8) as resp:
            encrypted_text = resp.read().decode("utf-8").strip().replace('"', '')

        key = b"kiemtienmua911ca"
        iv = b"1234567890oiuytr"
        raw = binascii.unhexlify(encrypted_text)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        data_json = json.loads(unpad(cipher.decrypt(raw), AES.block_size).decode("utf-8"))

        cf_url = data_json.get("cf", "")
        source_url = data_json.get("source", "")
        return cf_url or source_url or embed_url
    except Exception:
        pass

    return embed_url


# ---------------------------------------------------------------------------
#  Lecteur direct / embed générique
# ---------------------------------------------------------------------------

def extract_direct(embed_url):
    """
    Gère les liens embed directs (neocine, fstream, wiflix, etc.).

    Si l'URL appartient à un lecteur Byse/SeekStreaming connu, délègue à extract_byse.
    Sinon, tente d'extraire un M3U8 depuis la page embed (fallback standard).
    Retourne l'URL trouvée ou l'URL embed initiale.
    """
    if not embed_url:
        return None

    # Lecteurs Byse / SeekStreaming
    lower_url = embed_url.lower()
    byse_patterns = ["embedseek", "seekplayer", "seeks.cloud", "seekplays", "embed4me", "bysebuho"]
    if any(pattern in lower_url for pattern in byse_patterns):
        direct_url = extract_byse(embed_url)
        if direct_url:
            return direct_url

    # Fallback : cherche un M3U8 dans la page embed
    html = make_request(embed_url)
    if html:
        m3u8_patterns = [
            r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"src"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'hls["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pattern in m3u8_patterns:
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if m:
                url = m.group(1)
                if url.startswith("//"):
                    url = "https:" + url
                return url

    return embed_url


# ---------------------------------------------------------------------------
#  Utilitaire : suivi de redirection HTTP
# ---------------------------------------------------------------------------

def _follow_redirect(url, referer=""):
    """Suit une redirection HTTP (301/302/307/308) et retourne l'URL finale."""
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer

    req = urllib.request.Request(url, headers=headers)

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        opener.open(req, timeout=10)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            location = e.headers.get("Location", "")
            if location:
                if location.startswith("//"):
                    location = "https:" + location
                return location
    except Exception:
        pass
    return None
