"""
vidmoly.py - Extracteur Vidmoly (et ansembed.net alias).
"""
import re
from .base import BaseExtractor
from ..client import make_request


class VidmolyExtractor(BaseExtractor):
    name = "vidmoly"

    def extract(self, video_id_or_url: str) -> str:
        # Extrait l'id si une URL complète est passée
        match = re.search(r'embed-([^.]+)\.html', video_id_or_url)
        video_id = match.group(1) if match else video_id_or_url.strip("/")

        hls_patterns = [
            r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]

        domains = ["vidmoly.biz", "vidmoly.net", "vidmoly.to", "ansembed.net"]
        for domain in domains:
            embed_url = f"https://{domain}/embed-{video_id}.html"
            html = make_request(embed_url)
            if not html:
                continue

            for pattern in hls_patterns:
                match_url = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match_url:
                    video_url = match_url.group(1)
                    if video_url.startswith("//"):
                        video_url = "https:" + video_url
                    return video_url

        return f"https://vidmoly.net/embed-{video_id}.html"
