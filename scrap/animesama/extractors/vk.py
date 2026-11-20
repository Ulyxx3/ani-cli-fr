"""
vk.py - Extracteur VK (VKontakte / vkvideo.ru).
"""
import re
from .base import BaseExtractor
from ..client import make_request


class VkExtractor(BaseExtractor):
    name = "vk"

    def extract(self, video_id_or_url: str) -> str:
        if "vk.com" in video_id_or_url or "vkvideo.ru" in video_id_or_url:
            embed_url = video_id_or_url
        else:
            embed_url = f"https://vk.com/video_ext.php?{video_id_or_url}"

        html = make_request(embed_url, referer="https://anime-sama.to/")
        if not html:
            return ""

        # Search for highest resolution MP4 in vk video params
        mp4_matches = re.findall(r'"url(\d+)":\s*"([^"]+)"', html)
        if mp4_matches:
            mp4_matches.sort(key=lambda x: int(x[0]), reverse=True)
            return mp4_matches[0][1].replace(r"\/", "/")

        hls_match = re.search(r'"hls":\s*"([^"]+)"', html)
        if hls_match:
            return hls_match.group(1).replace(r"\/", "/")

        return ""
