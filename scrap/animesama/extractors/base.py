"""
base.py - Classe de base pour les extracteurs de serveurs vidéo.
"""
from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """Classe abstraite de base pour tous les extracteurs de serveurs."""

    name = "base"

    @abstractmethod
    def extract(self, video_id_or_url: str) -> str:
        """
        Extrait l'URL vidéo directe (MP4, M3U8, etc.) depuis l'ID ou l'URL de l'embed.
        Retourne l'URL directe sous forme de string, ou "" si échec.
        """
        pass
