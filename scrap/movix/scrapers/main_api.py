"""
scrapers/main_api.py - Scraper principal pour films et séries TV via movix (TMDB IDs).

Fonctions :
  - search_tmdb(query, media_type)
  - sort_links_by_lang(links, lang_mode)
  - get_tv_episodes(tmdb_id, season_num, content_type, lang_mode)
  - _try_alt_movie_sources(tmdb_id)
  - _try_alt_tv_sources(tmdb_id, season_num, lang_mode)
"""
import sys

from ..client import fetch_json, API_BASE, TMDB_API_BASE, TMDB_API_KEY
import urllib.parse


# ---------------------------------------------------------------------------
#  RECHERCHE TMDB
# ---------------------------------------------------------------------------

def search_tmdb(query, media_type="multi"):
    """
    Recherche un film ou une série via l'API TMDB (utilisée par movix.chat).

    media_type : 'multi' | 'movie' | 'tv'
    Retourne une liste de dicts : {id, name, year, type, overview}
    """
    encoded = urllib.parse.quote(query)
    url = (
        f"{TMDB_API_BASE}/search/{media_type}"
        f"?api_key={TMDB_API_KEY}&query={encoded}&language=fr-FR&page=1"
    )
    data = fetch_json(url)
    results = []
    if not data or "results" not in data:
        return results
    for item in data["results"]:
        item_type = item.get("media_type", media_type)
        if item_type == "person":
            continue
        title = item.get("title") or item.get("name", "")
        date = item.get("release_date") or item.get("first_air_date", "")
        year = date[:4] if date else ""
        results.append({
            "id": str(item.get("id", "")),
            "name": title,
            "year": year,
            "type": item_type,
            "overview": item.get("overview", "")[:100],
        })
    return results


# ---------------------------------------------------------------------------
#  TRI PAR LANGUE
# ---------------------------------------------------------------------------

def sort_links_by_lang(links, lang_mode="sub"):
    """
    Trie une liste de liens par langue préférée.

    lang_mode 'sub'/'vostfr' (défaut) → VOSTFR en tête (movix met souvent VF par défaut).
    lang_mode 'vf'/'dub'              → VF en tête.
    """
    if not isinstance(links, list) or len(links) <= 1:
        return links

    def get_priority(link_item):
        if not isinstance(link_item, dict):
            return 99
        lang = str(link_item.get("lang") or link_item.get("language") or "").upper()
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

    return sorted(links, key=get_priority)


# ---------------------------------------------------------------------------
#  LISTE DES ÉPISODES (films + séries)
# ---------------------------------------------------------------------------

def get_tv_episodes(tmdb_id, season_num=1, content_type="tv", lang_mode="sub"):
    """
    Récupère et affiche les liens d'un film ou d'une série via movix.

    content_type : 'movie' | 'tv'
    lang_mode    : 'sub'/'vostfr' (défaut VOSTFR) | 'vf'/'dub' (VF)

    Affiche : idx\\tidx\\tNomEpisode\\tdirect,url
    """
    if content_type == "movie":
        _get_movie(tmdb_id, lang_mode)
    else:
        _get_tv_series(tmdb_id, season_num, lang_mode)


def _get_movie(tmdb_id, lang_mode="sub"):
    """Récupère le lien principal d'un film (API /api/links/movie/{tmdb_id})."""
    url = f"{API_BASE}/api/links/movie/{tmdb_id}"
    data = fetch_json(url)
    if data and data.get("success"):
        movie_obj = data.get("data", {})
        links = []
        if isinstance(movie_obj, dict):
            links = movie_obj.get("links", [])
        elif isinstance(movie_obj, list) and movie_obj:
            links = movie_obj[0].get("links", [])

        links = sort_links_by_lang(links, lang_mode)
        if links:
            first_link = links[0]
            link_url = first_link.get("url", "") if isinstance(first_link, dict) else (first_link if isinstance(first_link, str) else "")
            if link_url:
                print(f"1\t1\tFilm (Principal)\tdirect,{link_url}")
                return

    # Fallback sources alternatives
    _try_alt_movie_sources(tmdb_id)


def _get_tv_series(tmdb_id, season_num=1, lang_mode="sub"):
    """Récupère les épisodes d'une série (API /api/links/tv/{tmdb_id})."""
    url = f"{API_BASE}/api/links/tv/{tmdb_id}"
    data = fetch_json(url)

    if not data or not data.get("success"):
        _try_alt_tv_sources(tmdb_id, season_num, lang_mode)
        return

    episodes_data = data.get("data", [])
    season_episodes = [
        ep for ep in episodes_data if ep.get("season_number") == season_num
    ]
    if not season_episodes:
        season_episodes = episodes_data

    global_idx = 1
    for ep in season_episodes:
        ep_num = ep.get("episode_number", global_idx)
        season_num_ep = ep.get("season_number", season_num)
        links = sort_links_by_lang(ep.get("links", []), lang_mode)

        if not links:
            global_idx += 1
            continue

        # Nom de l'épisode via TMDB
        ep_info = fetch_json(
            f"{TMDB_API_BASE}/tv/{tmdb_id}/season/{season_num_ep}/episode/{ep_num}"
            f"?api_key={TMDB_API_KEY}&language=fr-FR"
        )
        ep_name = f"S{season_num_ep:02d}E{ep_num:02d}"
        if ep_info:
            ep_name_tmdb = ep_info.get("name", "")
            if ep_name_tmdb:
                ep_name = f"S{season_num_ep:02d}E{ep_num:02d} - {ep_name_tmdb}"

        first_link = links[0]
        link_url = first_link.get("url", "") if isinstance(first_link, dict) else (first_link if isinstance(first_link, str) else "")

        if link_url:
            print(f"{global_idx}\t{global_idx}\t{ep_name}\tdirect,{link_url}")
            global_idx += 1


# ---------------------------------------------------------------------------
#  SOURCES ALTERNATIVES
# ---------------------------------------------------------------------------

def _try_alt_movie_sources(tmdb_id):
    """Essaie les sources alternatives (j1f, fstream) pour les films."""
    sources = [
        (f"{API_BASE}/api/j1f/movie/{tmdb_id}", "j1f"),
        (f"{API_BASE}/api/fstream/movie/{tmdb_id}", "fstream"),
    ]
    for url, source_name in sources:
        data = fetch_json(url)
        if data and data.get("success"):
            link = data.get("link") or data.get("url", "")
            if link:
                print(f"1\t1\tFilm ({source_name})\tdirect,{link}")
                return
    print("[movix] Aucune source disponible pour ce film.", file=sys.stderr)


def _try_alt_tv_sources(tmdb_id, season_num, lang_mode="sub"):
    """
    Essaie les sources alternatives (j1f, fstream, wiflix) pour les séries.
    Gère deux structures de réponse :
      - dict d'épisodes : {'episodes': {'1': {...}, '2': {...}}}
      - liste plate    : {'data': [{...}, {...}]}
    """
    sources = [
        (f"{API_BASE}/api/j1f/tv/{tmdb_id}/season/{season_num}", "j1f"),
        (f"{API_BASE}/api/fstream/tv/{tmdb_id}/season/{season_num}", "fstream"),
        (f"{API_BASE}/api/wiflix/tv/{tmdb_id}/{season_num}", "wiflix"),
    ]
    lang_order = ["VOSTFR", "VF", "VOENG", "Default"]
    if lang_mode in ("vf", "dub"):
        lang_order = ["VF", "VOSTFR", "VOENG", "Default"]

    for url, source_name in sources:
        data = fetch_json(url)
        if not data or not data.get("success"):
            continue

        # Structure 1 : dict d'épisodes (fstream, wiflix)
        episodes_dict = data.get("episodes") or data.get("data")
        if isinstance(episodes_dict, dict):
            sorted_eps = sorted(
                episodes_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0
            )
            global_idx = 1
            for ep_key in sorted_eps:
                ep_data = episodes_dict[ep_key]
                ep_num = ep_data.get("number") or ep_key
                langs = ep_data.get("languages", {})
                all_providers = []
                for lang_label in lang_order:
                    if isinstance(langs.get(lang_label), list):
                        all_providers.extend(langs[lang_label])

                if all_providers:
                    first = all_providers[0]
                    link_url = first.get("url") or first.get("link", "")
                    player_name = first.get("player") or first.get("label") or "Lecteur"
                    if link_url:
                        print(
                            f"{global_idx}\t{global_idx}\t"
                            f"Episode {ep_num} ({player_name} - {source_name})\t"
                            f"direct,{link_url}"
                        )
                        global_idx += 1
            if global_idx > 1:
                return

        # Structure 2 : liste plate (j1f ou autre)
        links = data.get("data") or data.get("links", [])
        if isinstance(links, list) and links:
            for i, item in enumerate(links, 1):
                link_url = item.get("url") or item.get("link", "")
                if link_url:
                    ep_num = item.get("episode_number", i)
                    print(f"{i}\t{i}\tEpisode {ep_num} ({source_name})\tdirect,{link_url}")
            return

    print("[movix] Aucune source disponible pour cette série.", file=sys.stderr)
