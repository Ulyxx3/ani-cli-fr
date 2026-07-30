"""
streamtape.py - Extracteur Streamtape.
"""
import re
from .base import BaseExtractor
from ..client import make_request


class StreamtapeExtractor(BaseExtractor):
    name = "streamtape"

    def extract(self, video_id_or_url: str) -> str:
        if "streamtape.com" in video_id_or_url:
            embed_url = video_id_or_url
        else:
            embed_url = f"https://streamtape.com/e/{video_id_or_url}"

        html = make_request(embed_url)
        if not html:
            return ""

        # Obfuscated streamtape link construction in JS
        match = re.search(r"document\.getElementById\('robotlink'\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]\s*\+\s*\(['\"]([^'\"]+)['\"]\)", html)
        if match:
            part1 = match.group(1)
            part2 = match.group(2)
            # Remove leading characters according to streamtape obf logic
            if part2.startswith("//"):
                video_url = "https:" + part1 + part2[3:]
            else:
                video_url = "https:" + part1 + part2
            return video_url

        # Secondary regex fallback
        match_norobot = re.search(r"id=['\"]norobotlink['\"][^>]*>([^<]+)<", html)
        if match_norobot:
            video_url = match_norobot.group(1).strip()
            if video_url.startswith("//"):
                video_url = "https:" + video_url
            return video_url

        return embed_url
