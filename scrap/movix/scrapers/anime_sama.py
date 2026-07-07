"""
scrapers/anime_sama.py - Scraper animes pour movix (via l'API anime-sama de movix.chat).

Fonctions :
  - search_anime(query)                         → liste de résultats
  - get_anime_episodes(anime_id, season_filter, lang_mode)  → affiche les épisodes
  - _encode_player(server_type, player_url)     → encode les données du player
"""
import re
import urllib.parse
import sys

from ..client import fetch_json, API_BASE


# ---------------------------------------------------------------------------
#  RECHERCHE
# ---------------------------------------------------------------------------

def search_anime(query):
    """
    Recherche un anime sur l'API movix.chat (endpoint /anime/search).
    Retourne une liste de dicts : {id, name, url, seasons_count, type}
    """
    encoded = urllib.parse.quote(query)
    url = f"{API_BASE}/anime/search/{encoded}?includeSeasons=true&includeEpisodes=false"
    data = fetch_json(url)
    results = []
    if not data or not isinstance(data, list):
        return results
    for item in data:
        name = item.get("name", "")
        url_path = item.get("url", "")
        # L'ID pour les animes movix est le slug de l'URL anime-sama
        anime_id = url_path.rstrip("/").split("/")[-1] if url_path else name
        seasons = item.get("seasons", [])
        results.append({
            "id": anime_id,
            "name": name,
            "url": url_path,
            "seasons_count": len(seasons),
            "type": "anime",
        })
    return results


# ---------------------------------------------------------------------------
#  LISTE DES ÉPISODES
# ---------------------------------------------------------------------------

def get_anime_episodes(anime_id, season_filter=None, lang_mode="sub"):
    """
    Récupère et affiche les épisodes d'un anime depuis movix.chat.

    anime_id     : slug anime-sama (ex: 'naruto-shippuden')
    season_filter: None = toutes les saisons, int = saison spécifique
    lang_mode    : 'sub'/'vostfr' (défaut) → VOSTFR en priorité
                   'vf'/'dub'               → VF en priorité

    Affiche : idx\\tidx\\t[Saison] NomEp\\tserver_type,data
    Priorité de lecteur : sibnet > vidmoly > autres.
    """
    anime_name = anime_id.replace("-", " ").title()
    encoded = urllib.parse.quote(anime_name)
    url = f"{API_BASE}/anime/search/{encoded}?includeSeasons=true&includeEpisodes=true"
    data = fetch_json(url)

    if not data or not isinstance(data, list):
        print(f"[movix] Aucun résultat pour anime_id={anime_id}", file=sys.stderr)
        return

    # Cherche la meilleure correspondance (slug dans l'URL)
    best = None
    for item in data:
        if anime_id in item.get("url", ""):
            best = item
            break
    if not best:
        best = data[0]

    seasons = best.get("seasons", [])
    global_idx = 1

    for season_idx, season in enumerate(seasons, start=1):
        if season_filter is not None and season_idx != season_filter:
            continue

        season_name = season.get("name", f"Saison {season_idx}")
        ep_list = season.get("episodes", [])

        for ep in ep_list:
            ep_idx = ep.get("index", global_idx)
            ep_name = ep.get("name", f"Episode {ep_idx}")
            streaming_links = ep.get("streaming_links", [])
            players = ep.get("players", [])

            best_player = None
            best_server = None

            # Tri des streaming_links selon la langue préférée
            def get_sl_priority(sl_item):
                lang = str(sl_item.get("type") or sl_item.get("language") or "").upper()
                if lang_mode in ("vf", "dub"):
                    if "VF" in lang or "FRENCH" in lang:
                        return 0
                    if "VOSTFR" in lang:
                        return 1
                else:  # sub / vostfr (défaut)
                    if "VOSTFR" in lang:
                        return 0
                    if "VF" in lang or "FRENCH" in lang:
                        return 1
                return 9

            for sl in sorted(streaming_links, key=get_sl_priority):
                for p in sl.get("players", []):
                    if "sibnet" in p:
                        best_player, best_server = p, "sibnet"
                        break
                    elif "vidmoly" in p and not best_player:
                        best_player, best_server = p, "vidmoly"
                if best_server == "sibnet":
                    break

            # Fallback sur les players directs
            if not best_player:
                for p in players:
                    url_p = p if isinstance(p, str) else p.get("url", "") if isinstance(p, dict) else ""
                    if "sibnet" in url_p:
                        best_player, best_server = url_p, "sibnet"
                        break
                    elif "vidmoly" in url_p and not best_player:
                        best_player, best_server = url_p, "vidmoly"

            if not best_player:
                global_idx += 1
                continue

            server_data = _encode_player(best_server, best_player)
            prefix = f"[{season_name}] " if len(seasons) > 1 else ""
            print(f"{global_idx}\t{global_idx}\t{prefix}{ep_name}\t{server_data}")
            global_idx += 1


# ---------------------------------------------------------------------------
#  UTILITAIRE
# ---------------------------------------------------------------------------

def _encode_player(server_type, player_url):
    """
    Encode les informations du player pour la phase extract.
    Format retourné : 'server_type,data'
    """
    if server_type == "sibnet":
        m = re.search(r"videoid=(\d+)", player_url)
        if m:
            return f"sibnet,{m.group(1)}"
    elif server_type == "vidmoly":
        m = re.search(r"embed-([^.]+)\.html", player_url)
        if m:
            return f"vidmoly,{m.group(1)}"
    # Fallback : encode l'URL entière comme lien direct
    return f"direct,{player_url}"
