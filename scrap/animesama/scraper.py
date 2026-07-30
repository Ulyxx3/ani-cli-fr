"""
scraper.py - Fonctions de scraping pour anime-sama : search, episodes, extract, servers.

Langue par défaut : VOSTFR. Passer vf=True (ou --vf en CLI) pour la VF.
"""
import re
import sys
import urllib.parse
from bs4 import BeautifulSoup

from .client import make_request, get_active_domain
from .extractors import extract_video_url


# ---------------------------------------------------------------------------
#  RECHERCHE
# ---------------------------------------------------------------------------

def search(query, vf=False):
    """
    Recherche un anime sur anime-sama.
    Affiche au format : URL\tTitre  (compatible ani-cli).
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
#  UTILITAIRES DE SERVEUR
# ---------------------------------------------------------------------------

def _identify_server(url):
    """Identifie le type de serveur depuis une URL embed/script."""
    url_lower = url.lower()
    if "sibnet.ru" in url_lower:
        return "sibnet"
    elif "vidmoly" in url_lower or "ansembed" in url_lower:
        return "vidmoly"
    elif "sendvid.com" in url_lower:
        return "sendvid"
    elif "streamtape" in url_lower:
        return "streamtape"
    elif "vk.com" in url_lower:
        return "vk"
    elif "myvi." in url_lower:
        return "myvi"
    elif "ok.ru" in url_lower:
        return "okru"
    return "other"


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


def _parse_season_js(content):
    """
    Extrait tous les tableaux eps1, eps2, eps3... depuis le JS de la saison.
    Retourne un dict: {server_index: [(url, server_type), ...]}
    """
    servers_dict = {}
    arrays = re.findall(r'var eps(\d+)\s*=\s*\[(.*?)\];', content, re.DOTALL)
    for array_idx, array_content in arrays:
        urls = re.findall(r'https?://[^\s\'",]+', array_content)
        if urls:
            server_type = _identify_server(urls[0])
            servers_dict[int(array_idx)] = [(u, server_type) for u in urls]
    return servers_dict


# ---------------------------------------------------------------------------
#  LISTE DES ÉPISODES ET SERVEURS
# ---------------------------------------------------------------------------

def episodes(url_path, vf=False, target_source=None):
    """
    Liste les épisodes d'un anime depuis une URL de catalogue anime-sama.
    Affiche au format : idx\tidx\t[Saison] NomEp\tserver_type,video_url_or_id
    target_source permet de forcer un serveur spécifique (ex: 'vidmoly', 'sibnet', etc.).
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

        servers_dict = _parse_season_js(content)
        if not servers_dict:
            continue

        selected_server_idx = None
        if target_source:
            for s_idx, ep_list in servers_dict.items():
                if ep_list and target_source.lower() in ep_list[0][1].lower():
                    selected_server_idx = s_idx
                    break

        if selected_server_idx is None:
            # Ordre de priorité par défaut : sibnet > vidmoly > sendvid > streamtape > vk > premier dispo
            priority = ["sibnet", "vidmoly", "sendvid", "streamtape", "vk"]
            for p in priority:
                for s_idx, ep_list in sorted(servers_dict.items()):
                    if ep_list and ep_list[0][1] == p:
                        selected_server_idx = s_idx
                        break
                if selected_server_idx is not None:
                    break

        if selected_server_idx is None:
            selected_server_idx = min(servers_dict.keys())

        best_episodes = servers_dict[selected_server_idx]
        episode_names = _extract_episodes_from_js(content)

        for i, (video_url, server_type) in enumerate(best_episodes):
            ep_name = episode_names[i] if i < len(episode_names) else f"Episode {i+1}"
            prefix = f"[{season_name}] " if season_name else ""
            print(f"{global_i}\t{global_i}\t{prefix}{ep_name}\t{server_type},{video_url}")
            global_i += 1


def servers(server_data):
    """
    Extrait tous les serveurs disponibles pour un épisode spécifique.
    Format server_data : 'server_type,video_url'
    Affiche la liste de tous les serveurs disponibles pour cet épisode.
    Format de sortie : server_name\tserver_type,video_url
    """
    # Si server_data contient juste server_type et url/id
    print(f"Default ({server_data.split(',', 1)[0]})\t{server_data}")


# ---------------------------------------------------------------------------
#  EXTRACTION DE LIENS VIDÉO
# ---------------------------------------------------------------------------

def extract(server_data):
    """
    Extrait l'URL vidéo directe depuis les données du serveur.
    Format server_data : 'server_type,video_url_or_id'
    """
    if "," not in server_data:
        print(f"[anime-sama] Format server_data invalide : {server_data}", file=sys.stderr)
        return

    server_type, video_id_or_url = server_data.split(",", 1)
    video_url = extract_video_url(server_type, video_id_or_url)
    print(video_url)
