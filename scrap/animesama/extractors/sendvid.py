"""
sendvid.py - Extracteur Sendvid.
"""
import re
from .base import BaseExtractor
from ..client import make_request


class SendvidExtractor(BaseExtractor):
    name = "sendvid"

    def extract(self, video_id_or_url: str) -> str:
        match = re.search(r'sendvid\.com/(?:embed/)?([a-zA-Z0-9]+)', video_id_or_url)
        video_id = match.group(1) if match else video_id_or_url

        embed_url = f"https://sendvid.com/embed/{video_id}"
        html = make_request(embed_url)
        if not html:
            return ""

        patterns = [
            r'var\s+video_source\s*=\s*["\']([^"\']+)["\']',
            r'<source\s+src=["\']([^"\']+)["\']',
            r'file:\s*["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match_src = re.search(pattern, html, re.IGNORECASE)
            if match_src:
                video_url = match_src.group(1)
                if video_url.startswith("//"):
                    video_url = "https:" + video_url
                return video_url

        return embed_url
