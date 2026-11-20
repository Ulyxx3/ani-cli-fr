"""
vidmoly.py - Extracteur Vidmoly (et ansembed.net alias).
"""
import re
import urllib.parse
from .base import BaseExtractor
from .unpacker import unpack_all
from ..client import make_request


class VidmolyExtractor(BaseExtractor):
    name = "vidmoly"

    def extract(self, video_id_or_url: str) -> str:
        match = re.search(r'embed-([^.]+)\.html', video_id_or_url)
        video_id = match.group(1) if match else video_id_or_url.strip("/")

        hls_patterns = [
            r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]

        base_domains = ["ansembed.net", "vidmoly.biz", "vidmoly.net", "vidmoly.to"]
        domains = list(base_domains)
        if video_id_or_url.startswith("http"):
            input_domain = urllib.parse.urlparse(video_id_or_url).netloc.lower()
            if input_domain:
                domains = [input_domain] + [d for d in base_domains if d != input_domain]

        for domain in domains:
            embed_url = f"https://{domain}/embed-{video_id}.html"
            html = make_request(embed_url, referer="https://anime-sama.to/")
            if not html:
                continue

            for text in [html] + unpack_all(html):
                for pattern in hls_patterns:
                    match_url = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                    if match_url:
                        video_url = match_url.group(1)
                        if video_url.startswith("//"):
                            video_url = "https:" + video_url
                        return video_url

        return ""
