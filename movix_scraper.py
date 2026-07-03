#!/usr/bin/env python3
"""
movix_scraper.py - Scraper pour movix.chat (films et séries)
Supporte : animes (via anime-sama), films et séries (via TMDB IDs)

Usage:
  python movix_scraper.py search <query> [--type anime|tv|movie]
  python movix_scraper.py episodes <id> [--type anime|tv|movie] [--season N]
  python movix_scraper.py extract <server_data>
"""
import sys
import re
import json
import urllib.request
import urllib.parse
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# TMDB API key (public, used by movix.chat frontend)
TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://movix.online",
    "Referer": "https://movix.online/",
    "Connection": "keep-alive",
}


def get_active_domain():
    """Résout dynamiquement le domaine actif via movix.online."""
    fallback = "movix.date"
    req = urllib.request.Request("https://movix.online", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            # Recherche d'un lien href pointant vers movix.*
            html = resp.read().decode("utf-8", errors="replace")
            # Cherche un lien externe vers movix (ex: https://movix.date ou similaire)
            match = re.search(r'href=["\'](https?://(?:www\.)?movix\.[a-z0-9]+)["\']', html)
            if match:
                domain_url = match.group(1)
                parsed = urllib.parse.urlparse(domain_url)
                if parsed.netloc:
                    return parsed.netloc
    except Exception as e:
        print(f"[movix] Impossible de résoudre le domaine via movix.online ({e}), fallback vers {fallback}", file=sys.stderr)
    return fallback


ACTIVE_DOMAIN = get_active_domain()
API_BASE = f"https://api.{ACTIVE_DOMAIN}"
TMDB_API_BASE = "https://api.themoviedb.org/3"
SITE_URL = f"https://{ACTIVE_DOMAIN}"


def make_request(url, headers=None):
    """Effectue une requête HTTP GET et retourne le texte brut."""
    dynamic_headers = {
        "Origin": SITE_URL,
        "Referer": SITE_URL + "/",
    }
    req_headers = {**HEADERS, **dynamic_headers, **(headers or {})}
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[movix] Erreur fetch {url}: {e}", file=sys.stderr)
        return ""


def fetch_json(url, headers=None):
    """Effectue une requête HTTP GET et retourne le JSON parsé."""
    text = make_request(url, headers)
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


# -------------------------------------------------
#  RECHERCHE
# -------------------------------------------------

def search_anime(query):
    """
    Recherche un anime sur l'API movix.chat.
    Retourne une liste de dicts : {id, name, seasons_count}
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
        # L'id pour les animes movix est le slug de l'URL anime-sama
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


def search_tmdb(query, media_type="multi"):
    """
    Recherche un film/série via TMDB (utilisé par movix.chat).
    media_type: 'multi', 'movie', 'tv'
    Retourne une liste de dicts : {id, name, year, type, overview}
    """
    encoded = urllib.parse.quote(query)
    url = f"{TMDB_API_BASE}/search/{media_type}?api_key={TMDB_API_KEY}&query={encoded}&language=fr-FR&page=1"
    data = fetch_json(url)
    results = []
    if not data or "results" not in data:
        return results
    for item in data["results"]:
        item_type = item.get("media_type", media_type)
        if item_type == "person":
            continue
        title = item.get("title") or item.get("name", "")
        year = ""
        date = item.get("release_date") or item.get("first_air_date", "")
        if date:
            year = date[:4]
        results.append({
            "id": str(item.get("id", "")),
            "name": title,
            "year": year,
            "type": item_type,
            "overview": item.get("overview", "")[:100],
        })
    return results


def search(query, content_type="multi"):
    """
    Recherche unifiée : anime + films/séries.
    Affiche au format : ID\tTitle (pour ani-cli)
    content_type: 'multi', 'anime', 'movie', 'tv'
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
    else:
        # multi : d'abord les animes, puis les films/séries
        anime_results = search_anime(query)
        tmdb_results = search_tmdb(query, media_type="multi")

        for r in anime_results:
            print(f"anime:{r['id']}\t{r['name']} ({r['seasons_count']} saison(s)) [Anime]")
        for r in tmdb_results:
            suffix = "(Film)" if r["type"] == "movie" else "(Serie)"
            year_str = f" [{r['year']}]" if r["year"] else ""
            print(f"{r['type']}:{r['id']}\t{r['name']}{year_str} {suffix}")


# -------------------------------------------------
#  LISTE DES EPISODES
# -------------------------------------------------

def get_anime_episodes(anime_id, season_filter=None):
    """
    Récupère les épisodes d'un anime depuis movix.chat.
    anime_id est le slug anime-sama (ex: 'naruto-shippuden')
    Affiche : index\tindex\tNom de l'episode\tserver,data
    """
    # Reconstruit le nom pour l'API à partir du slug
    anime_name = anime_id.replace("-", " ").title()
    encoded = urllib.parse.quote(anime_name)
    url = f"{API_BASE}/anime/search/{encoded}?includeSeasons=true&includeEpisodes=true"
    data = fetch_json(url)

    if not data or not isinstance(data, list):
        print(f"[movix] Aucun resultat pour anime_id={anime_id}", file=sys.stderr)
        return

    # Cherche la meilleure correspondance
    best = None
    for item in data:
        item_url = item.get("url", "")
        if anime_id in item_url:
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
        episodes = season.get("episodes", [])

        for ep in episodes:
            ep_idx = ep.get("index", global_idx)
            ep_name = ep.get("name", f"Episode {ep_idx}")
            streaming_links = ep.get("streaming_links", [])
            players = ep.get("players", [])

            # Cherche la meilleure source (sibnet > vidmoly > autres)
            best_player = None
            best_server = None

            # Priorité aux streaming_links (avec langue préférée)
            def get_sl_priority(sl_item):
                lang = str(sl_item.get("type") or sl_item.get("language") or "").upper()
                if LANG_MODE in ("vf", "dub"):
                    if "VF" in lang or "FRENCH" in lang:
                        return 0
                    if "VOSTFR" in lang:
                        return 1
                else:
                    if "VOSTFR" in lang:
                        return 0
                    if "VF" in lang or "FRENCH" in lang:
                        return 1
                return 9

            sorted_sl = sorted(streaming_links, key=get_sl_priority)
            for sl in sorted_sl:
                sl_players = sl.get("players", [])
                for p in sl_players:
                    if "sibnet" in p:
                        best_player = p
                        best_server = "sibnet"
                        break
                    elif "vidmoly" in p and not best_player:
                        best_player = p
                        best_server = "vidmoly"
                if best_server == "sibnet":
                    break

            # Fallback aux players directs
            if not best_player:
                for p in players:
                    if isinstance(p, str):
                        url_p = p
                    elif isinstance(p, dict):
                        url_p = p.get("url", "")
                    else:
                        continue
                    if "sibnet" in url_p:
                        best_player = url_p
                        best_server = "sibnet"
                        break
                    elif "vidmoly" in url_p and not best_player:
                        best_player = url_p
                        best_server = "vidmoly"

            if not best_player:
                global_idx += 1
                continue

            # Extrait l'ID du player
            server_data = _encode_player(best_server, best_player)
            prefix = f"[{season_name}] " if len(seasons) > 1 else ""
            print(f"{global_idx}\t{global_idx}\t{prefix}{ep_name}\t{server_data}")
            global_idx += 1


def _encode_player(server_type, player_url):
    """Encode les infos du player pour la phase extract."""
    if server_type == "sibnet":
        m = re.search(r"videoid=(\d+)", player_url)
        if m:
            return f"sibnet,{m.group(1)}"
    elif server_type == "vidmoly":
        m = re.search(r"embed-([^.]+)\.html", player_url)
        if m:
            return f"vidmoly,{m.group(1)}"
    # Fallback : encode l'URL entière
    return f"direct,{player_url}"


def sort_links_by_lang(links):
    if not isinstance(links, list) or len(links) <= 1:
        return links

    def get_link_priority(link_item):
        if not isinstance(link_item, dict):
            return 99
        lang = str(link_item.get("lang") or link_item.get("language") or "").upper()
        if LANG_MODE in ("vf", "dub"):
            if "VF" in lang or "FRENCH" in lang:
                return 0
            if "VOSTFR" in lang:
                return 1
        else:
            if "VOSTFR" in lang:
                return 0
            if "VF" in lang or "FRENCH" in lang:
                return 1
        return 9

    return sorted(links, key=get_link_priority)


def get_tv_episodes(tmdb_id, season_num=1, content_type="tv"):
    """
    Récupère les liens d'un film ou d'une série via movix.
    Pour les films : content_type='movie'
    Pour les séries : content_type='tv', season_num=numéro de saison
    Affiche : index\tindex\tNom de l'episode\tserver_data
    """
    if content_type == "movie":
        # Films : via /api/links/movie/{tmdb_id}
        url = f"{API_BASE}/api/links/movie/{tmdb_id}"
        data = fetch_json(url)
        if data and data.get("success"):
            # L'API renvoie { success: true, data: { id: ..., links: [...] } }
            movie_obj = data.get("data", {})
            links = []
            if isinstance(movie_obj, dict):
                links = movie_obj.get("links", [])
            elif isinstance(movie_obj, list) and len(movie_obj) > 0:
                links = movie_obj[0].get("links", [])

            links = sort_links_by_lang(links)
            if isinstance(links, list) and len(links) > 0:
                link_url = ""
                first_link = links[0]
                if isinstance(first_link, dict):
                    link_url = first_link.get("url", "")
                elif isinstance(first_link, str):
                    link_url = first_link

                if link_url:
                    server_data = f"direct,{link_url}"
                    print(f"1\t1\tFilm (Principal)\t{server_data}")
                    return

        # Fallback vers les autres sources pour les films
        _try_alt_movie_sources(tmdb_id)

    else:
        # Series TV : via /api/links/tv/{tmdb_id}
        url = f"{API_BASE}/api/links/tv/{tmdb_id}"
        data = fetch_json(url)

        if not data or not data.get("success"):
            # Fallback vers les autres sources
            _try_alt_tv_sources(tmdb_id, season_num)
            return

        episodes_data = data.get("data", [])

        # Filtre par saison
        season_episodes = [
            ep for ep in episodes_data
            if ep.get("season_number") == season_num
        ]

        if not season_episodes:
            season_episodes = episodes_data

        global_idx = 1
        for ep in season_episodes:
            ep_num = ep.get("episode_number", global_idx)
            season_num_ep = ep.get("season_number", season_num)
            links = ep.get("links", [])
            links = sort_links_by_lang(links)

            if not links:
                global_idx += 1
                continue

            # Récupère les infos épisode depuis TMDB (TMDB prend l'ID non encodé)
            ep_info = fetch_json(
                f"{TMDB_API_BASE}/tv/{tmdb_id}/season/{season_num_ep}/episode/{ep_num}?api_key={TMDB_API_KEY}&language=fr-FR"
            )
            ep_name = f"S{season_num_ep:02d}E{ep_num:02d}"
            if ep_info:
                ep_name_tmdb = ep_info.get("name", "")
                if ep_name_tmdb:
                    ep_name = f"S{season_num_ep:02d}E{ep_num:02d} - {ep_name_tmdb}"

            link_url = ""
            first_link = links[0]
            if isinstance(first_link, dict):
                link_url = first_link.get("url", "")
            elif isinstance(first_link, str):
                link_url = first_link

            if link_url:
                server_data = f"direct,{link_url}"
                print(f"{global_idx}\t{global_idx}\t{ep_name}\t{server_data}")
                global_idx += 1


def _try_alt_movie_sources(tmdb_id):
    """Essaie les sources alternatives pour les films."""
    sources = [
        (f"{API_BASE}/api/j1f/movie/{tmdb_id}", "j1f"),
        (f"{API_BASE}/api/fstream/movie/{tmdb_id}", "fstream"),
    ]
    for url, source_name in sources:
        data = fetch_json(url)
        if data and data.get("success"):
            link = data.get("link") or data.get("url", "")
            if link:
                server_data = f"direct,{link}"
                print(f"1\t1\tFilm ({source_name})\t{server_data}")
                return
    print("[movix] Aucune source disponible pour ce film.", file=sys.stderr)


def _try_alt_tv_sources(tmdb_id, season_num):
    """Essaie les sources alternatives pour les séries."""
    sources = [
        (f"{API_BASE}/api/j1f/tv/{tmdb_id}/season/{season_num}", "j1f"),
        (f"{API_BASE}/api/fstream/tv/{tmdb_id}/season/{season_num}", "fstream"),
        (f"{API_BASE}/api/wiflix/tv/{tmdb_id}/{season_num}", "wiflix"),
    ]
    for url, source_name in sources:
        data = fetch_json(url)
        if data and data.get("success"):
            # Structure 1 : Dictionnaire d'épisodes (fstream, wiflix)
            episodes_dict = data.get("episodes") or data.get("data")
            if isinstance(episodes_dict, dict):
                # Trie les clés numériquement
                sorted_eps = sorted(episodes_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0)
                global_idx = 1
                for ep_key in sorted_eps:
                    ep_data = episodes_dict[ep_key]
                    ep_num = ep_data.get("number") or ep_key
                    # Combine les liens selon la langue demandée
                    langs = ep_data.get("languages", {})
                    all_providers = []
                    lang_order = ["VOSTFR", "VF", "VOENG", "Default"]
                    if LANG_MODE in ("vf", "dub"):
                        lang_order = ["VF", "VOSTFR", "VOENG", "Default"]
                    for lang_label in lang_order:
                        if isinstance(langs.get(lang_label), list):
                            all_providers.extend(langs.get(lang_label))
                    
                    if all_providers:
                        first_provider = all_providers[0]
                        link_url = first_provider.get("url") or first_provider.get("link", "")
                        player_name = first_provider.get("player") or first_provider.get("label") or "Lecteur"
                        if link_url:
                            server_data = f"direct,{link_url}"
                            print(f"{global_idx}\t{global_idx}\tEpisode {ep_num} ({player_name} - {source_name})\t{server_data}")
                            global_idx += 1
                if global_idx > 1:
                    return
            
            # Structure 2 : Liste plate d'items (j1f ou autre)
            links = data.get("data") or data.get("links", [])
            if isinstance(links, list) and links:
                for i, item in enumerate(links, 1):
                    link_url = item.get("url") or item.get("link", "")
                    if link_url:
                        server_data = f"direct,{link_url}"
                        ep_num = item.get("episode_number", i)
                        print(f"{i}\t{i}\tEpisode {ep_num} ({source_name})\t{server_data}")
                return
    print("[movix] Aucune source disponible pour cette serie.", file=sys.stderr)


def episodes(content_id, season_num=1):
    """
    Point d'entrée pour lister les épisodes.
    content_id format : 'anime:slug', 'tv:12345', 'movie:67890'
    """
    if ":" not in content_id:
        # Assume anime pour la compatibilité
        get_anime_episodes(content_id)
        return

    content_type, real_id = content_id.split(":", 1)
    if content_type == "anime":
        get_anime_episodes(real_id, season_filter=season_num if season_num > 1 else None)
    elif content_type == "tv":
        get_tv_episodes(real_id, season_num=season_num, content_type="tv")
    elif content_type == "movie":
        get_tv_episodes(real_id, season_num=1, content_type="movie")
    else:
        print(f"[movix] Type inconnu: {content_type}", file=sys.stderr)


# -------------------------------------------------
#  EXTRACTION DE LIENS VIDEO
# -------------------------------------------------

def extract_sibnet(video_id):
    """Extrait le lien direct depuis sibnet."""
    url = f"https://video.sibnet.ru/shell.php?videoid={video_id}"
    html = make_request(url, headers={"Referer": "https://video.sibnet.ru/"})
    if not html:
        return None

    m = re.search(r'player\.src\(\[\{src:\s*["\']\/v\/([^/]+)\/', html)
    if not m:
        m = re.search(r'"src"\s*:\s*"/v/([^/]+)', html)
    if not m:
        m = re.search(r'src:\s*["\']\/v\/([^/]+)\/(\d+)\.mp4', html)
        if m:
            video_hash = m.group(1)
            mp4_url = f"https://video.sibnet.ru/v/{video_hash}/{video_id}.mp4"
            return _follow_redirect(mp4_url, "https://video.sibnet.ru/")

    if not m:
        return None

    video_hash = m.group(1)
    mp4_url = f"https://video.sibnet.ru/v/{video_hash}/{video_id}.mp4"
    return _follow_redirect(mp4_url, "https://video.sibnet.ru/")


def extract_vidmoly(video_id):
    """Extrait le lien M3U8 depuis vidmoly."""
    for domain in ["vidmoly.to", "vidmoly.net"]:
        embed_url = f"https://{domain}/embed-{video_id}.html"
        html = make_request(embed_url, headers={"Referer": f"https://{domain}/"})
        if not html:
            continue

        patterns = [
            r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pattern in patterns:
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if m:
                video_url = m.group(1)
                if video_url.startswith("//"):
                    video_url = "https:" + video_url
                return video_url

    return f"https://vidmoly.to/embed-{video_id}.html"


def extract_byse(embed_url):
    """
    Extrait l'URL m3u8 directe depuis un lecteur Byse/SeekStreaming
    en supportant à la fois la nouvelle API (AES-GCM) et l'ancienne API (AES-CBC).
    """
    import urllib.parse
    import urllib.request
    import json
    import base64
    import sys
    from Crypto.Cipher import AES

    def decode_base64_url(s):
        s = s.replace("-", "+").replace("_", "/")
        padding = len(s) % 4
        if padding:
            s += "=" * (4 - padding)
        return base64.b64decode(s)

    # 1. Extrait le video ID et le domaine
    decoded = urllib.parse.unquote(embed_url)
    video_id = None
    if "#" in decoded:
        video_id = decoded.split("#")[-1].strip()
    elif "/embed/" in decoded.lower():
        video_id = decoded.rstrip("/").split("/")[-1].strip()
    elif "/e/" in decoded.lower():
        video_id = decoded.rstrip("/").split("/")[-1].strip()
    else:
        try:
            parsed = urllib.parse.urlparse(decoded)
            if parsed.fragment:
                video_id = parsed.fragment.strip()
            elif parsed.path and parsed.path != "/":
                video_id = parsed.path.rstrip("/").split("/")[-1].strip()
        except:
            pass

    if not video_id:
        return embed_url

    try:
        parsed_url = urllib.parse.urlparse(decoded)
        api_domain = parsed_url.netloc
        if not api_domain:
            api_domain = "bysebuho.com"
    except:
        api_domain = "bysebuho.com"

    # STRATÉGIE 1 : Essayer la nouvelle API (AES-GCM)
    api_url_new = f"https://{api_domain}/api/videos/{video_id}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://{api_domain}/",
    }

    try:
        req = urllib.request.Request(api_url_new, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        playback = data.get("playback", {})
        if playback and "payload" in playback:
            version = playback.get("version")
            key_parts = playback.get("key_parts", [])
            iv_bytes = decode_base64_url(playback.get("iv", ""))
            payload_bytes = decode_base64_url(playback.get("payload", ""))

            # Reconstruire la table vi
            vi = {}
            for n in range(1, 21):
                vi[str(n)] = [n, 31 - n]

            indices = vi.get(version, [])
            selected_parts = []
            for idx in indices:
                if 1 <= idx <= len(key_parts):
                    selected_parts.append(key_parts[idx - 1])

            # Concaténer la clé AES
            key_bytes = b""
            for part in selected_parts:
                key_bytes += decode_base64_url(part)

            if len(key_bytes) in (16, 24, 32):
                tag_len = 16
                ciphertext = payload_bytes[:-tag_len]
                tag = payload_bytes[-tag_len:]

                cipher = AES.new(key_bytes, AES.MODE_GCM, nonce=iv_bytes)
                decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)
                decrypted_text = decrypted_bytes.decode("utf-8")
                decrypted_json = json.loads(decrypted_text)

                sources = decrypted_json.get("sources", [])
                if sources:
                    video_url = sources[0].get("url", "")
                    if video_url:
                        return video_url
    except Exception:
        # Fallback vers la stratégie 2
        pass

    # STRATÉGIE 2 : Essayer l'ancienne API (AES-CBC)
    api_url_old = f"https://{api_domain}/api/v1/video?id={video_id}&w=1920&h=1080&r="
    headers_old = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": f"https://{api_domain}/",
        "Origin": f"https://{api_domain}",
    }

    try:
        import binascii
        from Crypto.Util.Padding import unpad

        req = urllib.request.Request(api_url_old, headers=headers_old)
        with urllib.request.urlopen(req, timeout=8) as resp:
            encrypted_text = resp.read().decode("utf-8").strip().replace('"', '')

        key = b"kiemtienmua911ca"
        iv = b"1234567890oiuytr"
        data = binascii.unhexlify(encrypted_text)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_bytes = unpad(cipher.decrypt(data), AES.block_size)
        decrypted_text = decrypted_bytes.decode("utf-8")
        data_json = json.loads(decrypted_text)

        cf_url = data_json.get("cf", "")
        source_url = data_json.get("source", "")
        return cf_url or source_url or embed_url
    except Exception:
        pass

    return embed_url


def extract_direct(embed_url):
    """
    Gère les liens embed directs (neocine, fstream, etc.)
    Retourne l'URL embed directement pour le player.
    """
    if not embed_url:
        return None

    # Si c'est un embed Byse / SeekStreaming (embedseek, seekplayer, seeks.cloud, seekplays, embed4me, bysebuho, etc.)
    lower_url = embed_url.lower()
    byse_patterns = ["embedseek", "seekplayer", "seeks.cloud", "seekplays", "embed4me", "bysebuho"]
    if any(pattern in lower_url for pattern in byse_patterns):
        direct_url = extract_byse(embed_url)
        if direct_url:
            return direct_url

    # Sinon, essaie de récupérer un M3U8 depuis la page embed (fallback standard)
    html = make_request(embed_url)
    if html:
        m3u8_patterns = [
            r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"src"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'hls["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pattern in m3u8_patterns:
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if m:
                url = m.group(1)
                if url.startswith("//"):
                    url = "https:" + url
                return url

    return embed_url


def _follow_redirect(url, referer=""):
    """Suit une redirection HTTP pour obtenir l'URL finale."""
    headers = {**HEADERS}
    if referer:
        headers["Referer"] = referer

    req = urllib.request.Request(url, headers=headers)

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        opener.open(req, timeout=10)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            location = e.headers.get("Location", "")
            if location:
                if location.startswith("//"):
                    location = "https:" + location
                return location
    except Exception:
        pass
    return None


def extract(server_data):
    """
    Extrait le lien vidéo direct depuis les données du serveur.
    Format server_data : 'type,data'
    """
    if "," not in server_data:
        print("[movix] Format server_data invalide.", file=sys.stderr)
        return

    server_type, data = server_data.split(",", 1)

    if server_type == "sibnet":
        url = extract_sibnet(data)
        if url:
            print(url)
        else:
            print(f"https://video.sibnet.ru/shell.php?videoid={data}")

    elif server_type == "vidmoly":
        url = extract_vidmoly(data)
        if url:
            print(url)

    elif server_type == "direct":
        url = extract_direct(data)
        if url:
            print(url)
        else:
            print(data)

    else:
        print(data)


LANG_MODE = "sub"

# -------------------------------------------------
#  MAIN
# -------------------------------------------------

def main():
    global LANG_MODE
    if len(sys.argv) < 3:
        print("Usage: python movix_scraper.py [search|episodes|extract] [arg] [options]")
        sys.exit(1)

    action = sys.argv[1]
    arg = sys.argv[2]

    # Parse options supplementaires
    content_type = "multi"
    season_num = 1
    args_rest = sys.argv[3:]

    i = 0
    while i < len(args_rest):
        a = args_rest[i]
        if a == "--type" and i + 1 < len(args_rest):
            content_type = args_rest[i + 1]
            i += 2
        elif a == "--season" and i + 1 < len(args_rest):
            try:
                season_num = int(args_rest[i + 1])
            except ValueError:
                pass
            i += 2
        elif a == "--mode" and i + 1 < len(args_rest):
            LANG_MODE = args_rest[i + 1]
            i += 2
        elif a in ("movie", "tv", "anime", "multi"):
            content_type = a
            i += 1
        else:
            i += 1

    if action == "search":
        search(arg, content_type)
    elif action == "episodes":
        episodes(arg, season_num)
    elif action == "extract":
        extract(arg)
    else:
        print(f"[movix] Action inconnue: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
