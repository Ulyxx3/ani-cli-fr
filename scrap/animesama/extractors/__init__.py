"""
extractors package - Registre central des extracteurs vidéo.
"""
from typing import Dict, Type
from .base import BaseExtractor
from .vidmoly import VidmolyExtractor
from .uqload import UqloadExtractor
from .earnvids import EarnvidsExtractor
from .voe import VoeExtractor
from .sendvid import SendvidExtractor
from .vk import VkExtractor

EXTRACTORS: Dict[str, Type[BaseExtractor]] = {
    "vidmoly": VidmolyExtractor,
    "uqload": UqloadExtractor,
    "earnvids": EarnvidsExtractor,
    "voe": VoeExtractor,
    "sendvid": SendvidExtractor,
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
        return extractor.extract(video_id_or_url)
    # Fallback uniquement si aucun extracteur dédié n'existe (ex: youtube, dailymotion)
    if video_id_or_url.startswith("http"):
        return video_id_or_url
    return video_id_or_url
