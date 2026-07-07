"""
scrapers/fstream.py - Stub pour le scraper alternatif FStream.

Ce module est prévu pour extraire les liens directement depuis l'API FStream
lorsque des fonctionnalités avancées seront nécessaires (ex: sélection de source
à la volée dans le menu change_quality d'ani-cli).

La logique actuelle de FStream est gérée dans main_api._try_alt_movie_sources
et main_api._try_alt_tv_sources via l'endpoint /api/fstream/*.

Endpoints connus :
  GET {API_BASE}/api/fstream/movie/{tmdb_id}
  GET {API_BASE}/api/fstream/tv/{tmdb_id}/season/{season_num}

Réponse attendue :
  { "success": true, "episodes": { "1": { "number": 1, "languages": { "VOSTFR": [...], "VF": [...] } } } }
"""

# TODO: implémenter get_fstream_movie(tmdb_id, lang_mode) -> list[dict]
# TODO: implémenter get_fstream_tv(tmdb_id, season_num, lang_mode) -> list[dict]
