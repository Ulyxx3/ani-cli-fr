"""
sibnet.py - Extracteur de liens vidéo direct Sibnet.
"""
import re
import urllib.request
import urllib.error
from .base import BaseExtractor
from ..client import make_request


class SibnetExtractor(BaseExtractor):
    name = "sibnet"

    def extract(self, video_id_or_url: str) -> str:
        if "videoid=" in video_id_or_url:
            match_id = re.search(r'videoid=(\d+)', video_id_or_url)
            video_id = match_id.group(1) if match_id else video_id_or_url
        else:
            video_id = video_id_or_url

        url = f"https://video.sibnet.ru/shell.php?videoid={video_id}"
        html = make_request(url)
        if not html:
            return ""

        match = re.search(r'player\.src\(\[\{src: "/v/([^/]+)/', html)
        if match:
            video_hash = match.group(1)
            mp4_url = f"https://video.sibnet.ru/v/{video_hash}/{video_id}.mp4"

            req = urllib.request.Request(
                mp4_url,
                headers={
                    "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
                    "referer": "https://video.sibnet.ru/",
                },
            )

            class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            opener = urllib.request.build_opener(NoRedirectHandler())
            try:
                opener.open(req, timeout=10)
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    video_url = e.headers.get("Location", "")
                    if video_url.startswith("//"):
                        video_url = "https:" + video_url
                    return video_url
            except Exception:
                pass

        return ""
