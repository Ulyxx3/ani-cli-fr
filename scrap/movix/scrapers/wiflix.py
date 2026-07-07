"""
scrapers/wiflix.py - Stub pour le scraper alternatif Wiflix.

Ce module est prévu pour extraire les liens directement depuis l'API Wiflix
lorsque des fonctionnalités avancées seront nécessaires.

La logique actuelle de Wiflix est gérée dans main_api._try_alt_tv_sources
via l'endpoint /api/wiflix/*.

Endpoints connus :
  GET {API_BASE}/api/wiflix/tv/{tmdb_id}/{season_num}

Réponse attendue :
  { "success": true, "episodes": { "1": { "number": 1, "languages": { "VF": [...] } } } }

Note : Wiflix ne supporte généralement que la VF.
"""

# TODO: implémenter get_wiflix_tv(tmdb_id, season_num, lang_mode) -> list[dict]
