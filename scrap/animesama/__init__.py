"""
scrap/animesama/__init__.py
Point d'entrée du package animesama.
Expose : search, episodes, extract
"""
from .scraper import search, episodes, extract

__all__ = ["search", "episodes", "extract"]
