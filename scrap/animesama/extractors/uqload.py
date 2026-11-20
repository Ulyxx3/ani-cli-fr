"""
uqload.py - Extracteur Uqload (.vc / miroirs).
"""
import re
import urllib.parse
from .base import BaseExtractor
from .unpacker import unpack_all
from ..client import make_request_with_url


class UqloadExtractor(BaseExtractor):
    name = "uqload"

    def extract(self, video_id_or_url: str) -> str:
        if video_id_or_url.startswith("http"):
            embed_url = video_id_or_url
        else:
            embed_url = f"https://uqload.vc/embed-{video_id_or_url.strip('/')}.html"

        final_url, html = make_request_with_url(
            embed_url, referer="https://anime-sama.to/"
        )
        if not html:
            return ""

        base_url = final_url or embed_url

        # Stratégie 1 : JS packé Dean Edwards (actuel sur uqload.vc)
        packed_patterns = [
            r'(?:file|src)\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
            r'https?://[^\s\'"<>]+\.(?:m3u8|mp4)[^\s\'"<>]*',
        ]
        for unpacked in unpack_all(html):
            for pattern in packed_patterns:
                m = re.search(pattern, unpacked, re.IGNORECASE)
                if m:
                    url = m.group(1) if m.lastindex else m.group(0)
                    return self._normalize_url(url, base_url)

        # Stratégie 2 : HTML non packé (anciens embeds Uqload)
        raw_patterns = [
            r'sources\s*:\s*\[\s*["\']([^"\']+\.(?:mp4|m3u8)[^"\']*)["\']',
            r'(?:file|src)\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
            r'<source[^>]+src=["\']([^"\']+\.(?:mp4|m3u8)[^"\']*)["\']',
        ]
        for pattern in raw_patterns:
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if m:
                return self._normalize_url(m.group(1), base_url)

        return ""

    @staticmethod
    def _normalize_url(url: str, base_url: str) -> str:
        if url.startswith("//"):
            return "https:" + url
        if not url.startswith("http"):
            return urllib.parse.urljoin(base_url, url)
        return url
