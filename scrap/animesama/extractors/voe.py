"""
voe.py - Extracteur VOE (voe.sx et tous ses domaines miroirs rotatifs).
"""
import base64
import codecs
import json
import re
import urllib.parse
from .base import BaseExtractor
from ..client import make_request_with_url

_VOE_TOKENS = ("@$", "^^", "~@", "%?", "*~", "!!", "#&")
_BAIT_MARKERS = ("test-videos.co.uk", "big_buck_bunny", "bigbuckbunny")


def _is_bait_url(url: str) -> bool:
    if not url:
        return True
    lower = url.lower()
    return any(marker in lower for marker in _BAIT_MARKERS)


def _normalize_url(url: str, base_url: str) -> str:
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urllib.parse.urljoin(base_url, url)
    return url


def _decode_b64_str(s: str) -> str:
    pad = len(s) % 4
    if pad:
        s += "=" * (4 - pad)
    return base64.b64decode(s).decode("utf-8")


def _decode_voe_blob(raw: str) -> str:
    s = codecs.decode(raw, "rot_13")
    for tok in _VOE_TOKENS:
        s = s.replace(tok, "")
    s = _decode_b64_str(s)
    s = "".join(chr(ord(c) - 3) for c in s)
    s = s[::-1]
    data = json.loads(_decode_b64_str(s))
    if not isinstance(data, dict):
        return ""
    return data.get("source") or data.get("direct_access_url") or ""


class VoeExtractor(BaseExtractor):
    name = "voe"

    def extract(self, video_id_or_url: str) -> str:
        if video_id_or_url.startswith("http"):
            current_url = video_id_or_url
        else:
            current_url = f"https://voe.sx/e/{video_id_or_url.strip('/')}"

        visited = set()
        for _ in range(4):
            if current_url in visited:
                break
            visited.add(current_url)

            final_url, html = make_request_with_url(
                current_url, referer="https://anime-sama.to/"
            )
            if not html:
                return ""

            base_url = final_url or current_url

            # Stratégie 1 : Script JSON obfusqué actuel de VOE
            for m_json in re.finditer(
                r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
                html,
                re.DOTALL | re.IGNORECASE,
            ):
                try:
                    payload = json.loads(m_json.group(1).strip())
                except Exception:
                    continue
                items = payload if isinstance(payload, list) else [payload]
                for item in items:
                    if not isinstance(item, str):
                        continue
                    try:
                        candidate = _decode_voe_blob(item)
                    except Exception:
                        continue
                    if candidate and not _is_bait_url(candidate):
                        return _normalize_url(candidate, base_url)

            # Stratégie 2 : Ancien format VOE ('hls'/'mp4' ou lien .m3u8 direct)
            legacy_patterns = [
                r"['\"]hls['\"]\s*:\s*['\"]([^'\"]+)['\"]",
                r"['\"]mp4['\"]\s*:\s*['\"]([^'\"]+)['\"]",
                r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*",
            ]
            for pattern in legacy_patterns:
                for m in re.finditer(pattern, html, re.IGNORECASE):
                    val = m.group(1) if m.lastindex else m.group(0)
                    if not val.startswith("http") and not val.startswith("//"):
                        try:
                            val = _decode_b64_str(val)
                        except Exception:
                            continue
                    if val.startswith(("http", "//")) and not _is_bait_url(val):
                        return _normalize_url(val, base_url)

            # Suivre les redirections JS (ex: derricknationtop.com -> arianathankspecial.com)
            redir = re.search(
                r"window\.location\.href\s*=\s*['\"](https?://[^'\"]+)['\"]",
                html,
            )
            if redir:
                current_url = redir.group(1)
                continue
            break

        return ""
