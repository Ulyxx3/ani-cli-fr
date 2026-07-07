"""
scrap/movix/scrapers/__init__.py
Interface commune pour les scrapers movix.

Expose les fonctions de haut niveau search, episodes et extract
qui seront utilisées par scrap/movix/__init__.py.
"""
import sys
import urllib.parse

from .anime_sama import search_anime, get_anime_episodes
from .main_api import search_tmdb, get_tv_episodes
from ..decryptors import extract_sibnet, extract_vidmoly, extract_direct


# ---------------------------------------------------------------------------
#  RECHERCHE
# ---------------------------------------------------------------------------

def search(query, content_type="multi", lang_mode="sub"):
    """
    Recherche unifiée : anime + films + séries.
    Affiche au format TSV : ID\\tTitre  (compatible ani-cli)

    content_type : 'multi' | 'anime' | 'movie' | 'tv'
    """
    if content_type == "anime":
        results = search_anime(query)
        for r in results:
            print(f"anime:{r['id']}\t{r['name']} ({r['seasons_count']} saison(s))")

    elif content_type in ("movie", "tv"):
        results = search_tmdb(query, media_type=content_type)
        for r in results:
            suffix = "(Film)" if r["type"] == "movie" else "(Serie)"
            year_str = f" [{r['year']}]" if r["year"] else ""
            print(f"{r['type']}:{r['id']}\t{r['name']}{year_str} {suffix}")

    else:  # multi : animes d'abord, puis films/séries
        anime_results = search_anime(query)
        tmdb_results = search_tmdb(query, media_type="multi")

        for r in anime_results:
            print(f"anime:{r['id']}\t{r['name']} ({r['seasons_count']} saison(s)) [Anime]")
        for r in tmdb_results:
            suffix = "(Film)" if r["type"] == "movie" else "(Serie)"
            year_str = f" [{r['year']}]" if r["year"] else ""
            print(f"{r['type']}:{r['id']}\t{r['name']}{year_str} {suffix}")


# ---------------------------------------------------------------------------
#  LISTE DES ÉPISODES
# ---------------------------------------------------------------------------

def episodes(content_id, season_num=1, lang_mode="sub"):
    """
    Liste les épisodes d'un contenu.
    content_id format : 'anime:slug' | 'tv:12345' | 'movie:67890'
    """
    if ":" not in content_id:
        # Compatibilité ascendante : assume anime
        get_anime_episodes(content_id, lang_mode=lang_mode)
        return

    content_type, real_id = content_id.split(":", 1)

    if content_type == "anime":
        get_anime_episodes(
            real_id,
            season_filter=season_num if season_num > 1 else None,
            lang_mode=lang_mode,
        )
    elif content_type == "tv":
        get_tv_episodes(real_id, season_num=season_num, content_type="tv", lang_mode=lang_mode)
    elif content_type == "movie":
        get_tv_episodes(real_id, season_num=1, content_type="movie", lang_mode=lang_mode)
    else:
        print(f"[movix] Type inconnu: {content_type}", file=sys.stderr)


# ---------------------------------------------------------------------------
#  EXTRACTION DE LIENS VIDÉO
# ---------------------------------------------------------------------------

def extract(server_data):
    """
    Extrait le lien vidéo direct depuis les données du serveur.
    Format server_data : 'server_type,data'
    Supporte : sibnet | vidmoly | direct
    """
    if "," not in server_data:
        print("[movix] Format server_data invalide.", file=sys.stderr)
        return

    server_type, data = server_data.split(",", 1)

    if server_type == "sibnet":
        url = extract_sibnet(data)
        print(url if url else f"https://video.sibnet.ru/shell.php?videoid={data}")

    elif server_type == "vidmoly":
        url = extract_vidmoly(data)
        if url:
            print(url)

    elif server_type == "direct":
        url = extract_direct(data)
        print(url if url else data)

    else:
        print(data)
