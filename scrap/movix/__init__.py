"""
scrap/movix/__init__.py
Point d'entrée public du package movix.

Expose : search, episodes, extract
Ces trois fonctions constituent l'interface utilisée par movix_scraper.py (wrapper CLI).
"""
from .scrapers import search, episodes, extract

__all__ = ["search", "episodes", "extract"]
