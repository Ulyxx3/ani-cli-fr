"""
scrapers/j1f.py - Stub pour le scraper alternatif 1jour1film (j1f).

Ce module est prévu pour extraire les liens directement depuis l'API 1jour1film
lorsque des fonctionnalités avancées seront nécessaires.

La logique actuelle de j1f est gérée dans main_api._try_alt_movie_sources
et main_api._try_alt_tv_sources via les endpoints /api/j1f/*.

Endpoints connus :
  GET {API_BASE}/api/j1f/movie/{tmdb_id}
  GET {API_BASE}/api/j1f/tv/{tmdb_id}/season/{season_num}

Réponse film attendue :
  { "success": true, "link": "https://..." }

Réponse série attendue :
  { "success": true, "data": [{ "episode_number": 1, "url": "https://..." }] }
"""

# TODO: implémenter get_j1f_movie(tmdb_id) -> str | None
# TODO: implémenter get_j1f_tv(tmdb_id, season_num) -> list[dict]
