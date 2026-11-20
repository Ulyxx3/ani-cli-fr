"""
earnvids.py - Extracteur Earnvids (smoothpre, minochinos, movearnpre, morencius, dingtezuni, callistanise, ...).
"""
import re
import urllib.parse
from .base import BaseExtractor
from .unpacker import unpack_all
from ..client import make_request_with_url


class EarnvidsExtractor(BaseExtractor):
    name = "earnvids"

    def extract(self, video_id_or_url: str) -> str:
        if video_id_or_url.startswith("http"):
            embed_url = video_id_or_url
        else:
            embed_url = f"https://smoothpre.com/embed/{video_id_or_url.strip('/')}"

        final_url, html = make_request_with_url(
            embed_url, referer="https://anime-sama.to/"
        )
        if not html:
            return ""

        base_url = final_url or embed_url
        candidates = unpack_all(html) + [html]

        patterns = [
            r'["\']hls2["\']\s*:\s*["\']([^"\']+)["\']',
            r'["\']hls4["\']\s*:\s*["\']([^"\']+)["\']',
            r'(?:file|src)\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'["\']((?:https?:)?//[^"\']+\.m3u8[^"\']*|/[^"\']+\.m3u8[^"\']*)["\']',
            r'["\']hls3["\']\s*:\s*["\']([^"\']+)["\']',
        ]

        for text in candidates:
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    video_url = m.group(1).strip()
                    if not video_url:
                        continue
                    if video_url.startswith("//"):
                        return "https:" + video_url
                    if not video_url.startswith("http"):
                        return urllib.parse.urljoin(base_url, video_url)
                    return video_url

        return ""
