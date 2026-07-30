"""
extractors package - Registre central des extracteurs vidéo.
"""
from typing import Dict, Type
from .base import BaseExtractor
from .sibnet import SibnetExtractor
from .vidmoly import VidmolyExtractor
from .sendvid import SendvidExtractor
from .streamtape import StreamtapeExtractor
from .vk import VkExtractor

EXTRACTORS: Dict[str, Type[BaseExtractor]] = {
    "sibnet": SibnetExtractor,
    "vidmoly": VidmolyExtractor,
    "sendvid": SendvidExtractor,
    "streamtape": StreamtapeExtractor,
    "vk": VkExtractor,
}


def get_extractor(server_name: str) -> BaseExtractor:
    server_lower = server_name.lower()
    for key, extractor_cls in EXTRACTORS.items():
        if key in server_lower:
            return extractor_cls()
    return None


def extract_video_url(server_type: str, video_id_or_url: str) -> str:
    extractor = get_extractor(server_type)
    if extractor:
        url = extractor.extract(video_id_or_url)
        if url:
            return url
    # Fallback si l'URL est déjà directe ou non gérée
    if video_id_or_url.startswith("http"):
        return video_id_or_url
    return video_id_or_url
