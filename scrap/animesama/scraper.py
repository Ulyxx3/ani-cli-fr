"""
scraper.py - Fonctions de scraping pour anime-sama : search, episodes, extract.

Langue par défaut : VOSTFR.  Passer vf=True (ou --vf en CLI) pour la VF.
"""
import re
import sys
import urllib.parse
from bs4 import BeautifulSoup

from .client import make_request, get_active_domain


# ---------------------------------------------------------------------------
#  RECHERCHE
# ---------------------------------------------------------------------------

def search(query, vf=False):
    """
    Recherche un anime sur anime-sama.
    Affiche au format : URL\\tTitre  (compatible ani-cli).
    vf=True pour filtrer uniquement les résultats VF.
    """
    domain = get_active_domain()
    url = f"https://{domain}/catalogue/"
    params = {"search": query}
    if vf:
        params["langue[]"] = "VF"

    html = make_request(url, params)
    soup = BeautifulSoup(html, "html.parser")

    results = []
    for card in soup.find_all("a", href=True):
        titre_tag = card.find(["h1", "h2"])
        if titre_tag and "catalogue" in card["href"]:
            titre = titre_tag.text.strip()
            href = card["href"]
            if vf and "vostfr" in href:
                href = href.replace("vostfr", "vf")
            results.append((href, titre))

    query_unquoted = urllib.parse.unquote_plus(query)
    for url_path, title in results:
        if query_unquoted and query_unquoted.lower() not in title.lower():
            continue
        print(f"{url_path}\t{title}")


# ---------------------------------------------------------------------------
#  LISTE DES ÉPISODES
# ---------------------------------------------------------------------------

def _extract_episodes_from_js(content):
    """
    Parse le fichier episodes.js d'anime-sama pour extraire les noms d'épisodes.
    Gère les cas spéciaux (OAV, films, etc.) via creerListe / newSPF / finirListeOP.
    """
    episode_list = []
    special_matches = re.findall(
        r'creerListe\((\d+),\s*(\d+)\);\s*newSPF?\(["\']([^"\']+)["\']\);?', content
    )
    regular_matches = re.findall(r'creerListe\((\d+),\s*(\d+)\);', content)
    finir_match = re.search(r'finirListeOP?\((\d+)\);', content)

    all_special_ranges = set()
    for start_ep, end_ep, special_name in special_matches:
        start_num, end_num = int(start_ep), int(end_ep)
        for ep_num in range(start_num, end_num + 1):
            episode_list.append(f"Episode {ep_num}")
            all_special_ranges.add(ep_num)
        episode_list.append(special_name)

    for start_ep, end_ep in regular_matches:
        start_num, end_num = int(start_ep), int(end_ep)
        if start_num not in all_special_ranges:
            for ep_num in range(start_num, end_num + 1):
                episode_list.append(f"Episode {ep_num}")

    if finir_match:
        start_finir = int(finir_match.group(1))
        end_finir = start_finir + 50  # fallback 50 épisodes

        taille_match = re.search(r'var\s+tailleEpisodes\s*=\s*(\d+)', content)
        if taille_match:
            total = int(taille_match.group(1))
            retards_match = re.search(r'var\s+epRetards\s*=\s*(\d+)', content)
            retards = int(retards_match.group(1)) if retards_match else 0
            end_finir = total - retards
        else:
            length_match = re.search(r'episodes\.length\s*=\s*(\d+)', content)
            if length_match:
                end_finir = int(length_match.group(1))

        for ep_num in range(start_finir, end_finir + 1):
            episode_list.append(f"Episode {ep_num}")

    return episode_list


def episodes(url_path, vf=False):
    """
    Liste les épisodes d'un anime depuis une URL de catalogue anime-sama.
    Affiche au format : idx\\tidx\\t[Saison] NomEp\\tserver_type,video_id

    Langue par défaut : VOSTFR.  vf=True pour forcer la VF.
    Priorité de serveur : sibnet > vidmoly.
    """
    domain = get_active_domain()
    complete_url = (
        f"https://{domain}{url_path}" if url_path.startswith("/") else url_path
    )

    html = make_request(complete_url)
    if not html:
        return

    seasons = []
    for match in re.finditer(
        r'panneauAnime\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)', html
    ):
        season_name = match.group(1)
        subpath = match.group(2)
        if subpath == "url" or season_name == "nom":
            continue
        if vf and "vostfr" in subpath:
            subpath = subpath.replace("vostfr", "vf")
        seasons.append((season_name, subpath))

    if not seasons:
        seasons.append(("", ""))

    global_i = 1
    for season_name, subpath in seasons:
        season_url = complete_url
        if subpath:
            if not season_url.endswith("/"):
                season_url += "/"
            season_url += subpath.strip("/") + "/"

        season_html = html if not subpath else make_request(season_url)
        if not season_html:
            continue

        filever = "1"
        match = re.search(r'episodes\.js\?filever=(\d+)', season_html)
        if match:
            filever = match.group(1)

        js_url = (
            f"{season_url}episodes.js?filever={filever}"
            if season_url.endswith("/")
            else f"{season_url}/episodes.js?filever={filever}"
        )

        content = make_request(js_url)
        if not content:
            continue

        arrays = re.findall(r'var eps(\d+) = \[(.*?)\];', content, re.DOTALL)
        best_server = None
        best_episodes = []

        if arrays:
            for _array_num, array_content in arrays:
                sibnet_matches = list(
                    re.finditer(
                        r'https://video\.sibnet\.ru/shell\.php\?videoid=(\d+)',
                        array_content,
                    )
                )
                if sibnet_matches and not best_server:
                    best_server = "sibnet"
                    best_episodes = [(m.group(1), "sibnet") for m in sibnet_matches]
                    break

                vidmoly_matches = list(
                    re.finditer(
                        r'https://vidmoly\.[a-z]+/embed-([^.]+)\.html', array_content
                    )
                )
                if vidmoly_matches and not best_server:
                    best_server = "vidmoly"
                    best_episodes = [(m.group(1), "vidmoly") for m in vidmoly_matches]

        if not best_episodes:
            sibnet_matches = list(
                re.finditer(
                    r'https://video\.sibnet\.ru/shell\.php\?videoid=(\d+)', content
                )
            )
            if sibnet_matches:
                best_server = "sibnet"
                best_episodes = [(m.group(1), "sibnet") for m in sibnet_matches]

        episode_names = _extract_episodes_from_js(content)

        for i, (video_id, server_type) in enumerate(best_episodes):
            ep_name = episode_names[i] if i < len(episode_names) else f"Episode {i+1}"
            prefix = f"[{season_name}] " if season_name else ""
            print(f"{global_i}\t{global_i}\t{prefix}{ep_name}\t{server_type},{video_id}")
            global_i += 1


# ---------------------------------------------------------------------------
#  EXTRACTION DE LIENS VIDÉO
# ---------------------------------------------------------------------------

def extract(server_data):
    """
    Extrait l'URL vidéo directe depuis les données du serveur.
    Format server_data : 'server_type,video_id'
    Supporte : sibnet, vidmoly.
    """
    if "," not in server_data:
        print(f"[anime-sama] Format server_data invalide : {server_data}", file=sys.stderr)
        return

    server_type, video_id = server_data.split(",", 1)

    if server_type == "sibnet":
        _extract_sibnet(video_id)
    elif server_type == "vidmoly":
        _extract_vidmoly(video_id)
    else:
        # Fallback : affiche l'ID tel quel
        print(video_id)


def _extract_sibnet(video_id):
    """Extrait l'URL directe MP4 depuis sibnet (suit la redirection 302)."""
    url = f"https://video.sibnet.ru/shell.php?videoid={video_id}"
    html = make_request(url)
    match = re.search(r'player\.src\(\[\{src: "/v/([^/]+)/', html)
    if match:
        video_hash = match.group(1)
        mp4_url = f"https://video.sibnet.ru/v/{video_hash}/{video_id}.mp4"

        import urllib.request
        import urllib.error

        req = urllib.request.Request(
            mp4_url,
            headers={
                "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
                "referer": "https://video.sibnet.ru/",
            },
        )

        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirectHandler())
        try:
            opener.open(req, timeout=10)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                video_url = e.headers["Location"]
                if video_url.startswith("//"):
                    video_url = "https:" + video_url
                print(video_url)
                return
        except Exception:
            pass


def _extract_vidmoly(video_id):
    """Extrait le lien M3U8 depuis vidmoly (essaie .net puis .to)."""
    hls_patterns = [
        r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
    ]
    for domain in ["vidmoly.net", "vidmoly.to"]:
        embed_url = f"https://{domain}/embed-{video_id}.html"
        html = make_request(embed_url)
        for pattern in hls_patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                video_url = match.group(1)
                if video_url.startswith("//"):
                    video_url = "https:" + video_url
                print(video_url)
                return
    print(f"https://vidmoly.net/embed-{video_id}.html")
