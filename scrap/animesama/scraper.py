"""
scraper.py - Fonctions de scraping pour anime-sama : search, episodes, extract, chapters, pages.

Langue par défaut : VOSTFR. Passer vf=True (ou --vf en CLI) pour la VF.
"""
import json
import re
import sys
import urllib.parse
from bs4 import BeautifulSoup

from .client import make_request, get_active_domain
from .extractors import extract_video_url


SERVER_PRIORITY = ["vidmoly", "uqload", "earnvids", "voe", "sendvid", "vk"]
DEAD_HOSTS = {
    "sibnet.ru",
    "embed4me.com",
    "player4me.com",
    "4meplayer.com",
    "oneupload.to",
    "myvi.top",
    "myvi.tv",
}

_LIST_TOKEN_RE = re.compile(
    r"(?<!function\s)\b(?:"
    r"(resetListe)\s*\(\s*\)"
    r"|(creerListe)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)"
    r'|(newSPF|newSP)\s*\(\s*(?:"([^"]*)"|\'([^\']*)\')\s*\)'
    r"|(finirListeOP|finirListe)\s*\(\s*(\d+)\s*\)"
    r")"
)


# ---------------------------------------------------------------------------
#  RECHERCHE
# ---------------------------------------------------------------------------

def search(query, vf=False, scans=False):
    """
    Recherche un anime ou scan sur anime-sama.
    Affiche au format : URL\tTitre  (compatible ani-cli).
    vf=True pour filtrer uniquement les résultats VF.
    scans=True pour filtrer uniquement les résultats Scans.
    """
    domain = get_active_domain()
    url = f"https://{domain}/catalogue/"
    params = {"search": query}
    if vf:
        params["langue[]"] = "VF"
    if scans:
        params["type[]"] = "Scans"

    html = make_request(url, params)
    soup = BeautifulSoup(html, "html.parser")

    results = []
    for card in soup.find_all("a", href=True):
        titre_tag = card.find(["h1", "h2", "h3"]) or card.find(class_=re.compile(r"titre", re.I))
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
#  UTILITAIRES HTML / JS / SERVEURS
# ---------------------------------------------------------------------------

def _strip_comments(html):
    """Supprime les commentaires HTML et JS sans toucher aux URLs (https://)."""
    cleaned = re.sub(r"<!--[\s\S]*?-->", "", html)
    cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*//.*$", "", cleaned)
    return cleaned


def _extract_js_object(html, var_name):
    """Extrait un objet JSON assigné à `var <var_name> = {...}`."""
    match = re.search(rf"\bvar\s+{re.escape(var_name)}\s*=\s*", html)
    if not match:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(html, match.end())
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def _host_in_set(host, host_set):
    h = host.lower().removeprefix("www.")
    parts = h.split(".")
    for k in range(len(parts) - 1):
        if ".".join(parts[k:]) in host_set:
            return True
    return h in host_set


def _lookup_lecteur_info(host, lecteurs_infos):
    if not host or not lecteurs_infos:
        return None
    h = host.lower().removeprefix("www.")
    parts = h.split(".")
    for k in range(len(parts) - 1):
        d = ".".join(parts[k:])
        if d in lecteurs_infos:
            return lecteurs_infos[d]
    return lecteurs_infos.get(h)


def _identify_server(url_or_host):
    """Identifie le type de serveur canonique depuis un nom d'hôte ou une URL."""
    h = url_or_host.lower()
    if "://" in h:
        h = urllib.parse.urlparse(h).netloc.lower()
    if _host_in_set(h, DEAD_HOSTS):
        return None
    if "vidmoly" in h or "ansembed" in h:
        return "vidmoly"
    if "uqload" in h:
        return "uqload"
    if any(
        k in h
        for k in (
            "smoothpre",
            "morencius",
            "movearnpre",
            "dingtezuni",
            "earnvids",
            "minochinos",
            "callistanise",
        )
    ):
        return "earnvids"
    if "voe." in h or any(
        k in h
        for k in (
            "teresapoliticallearn",
            "megankiddifference",
            "jeremyparticipantanything",
            "jamesbornmain",
            "claireguessthousand",
            "derricknationtop",
            "shanelocaldog",
            "jamespatterncamera",
            "shannoncoldalready",
            "susanexpectcare",
            "arianathankspecial",
        )
    ):
        return "voe"
    if "sendvid" in h:
        return "sendvid"
    if "vk.com" in h or "vkvideo.ru" in h:
        return "vk"
    if "dailymotion" in h:
        return "dailymotion"
    if "youtube" in h:
        return "youtube"
    if "ok.ru" in h:
        return "okru"
    return "other"


def _canonical_server(host, lecteurs_infos):
    """
    Résout le nom canonique du serveur à partir de `lecteursInfos` puis du fallback statique.
    Retourne None si l'hébergeur est marqué mort (`mort: true` ou `DEAD_HOSTS`).
    """
    if not host:
        return None
    info = _lookup_lecteur_info(host, lecteurs_infos)
    if info:
        if info.get("mort"):
            return None
        nom = str(info.get("nom", "")).strip().lower()
        if nom in ("vidmoly", "uqload", "earnvids", "voe", "sendvid", "vk", "dailymotion", "youtube"):
            return nom
        if nom == "ok.ru":
            return "okru"
    return _identify_server(host)


def _parse_season_eps(content):
    """
    Extrait tous les tableaux eps1, eps2, ... en conservant l'alignement des index
    (y compris les chaînes vides "").
    Retourne un dict : {player_idx: [entry, ...]}
    """
    eps_dict = {}
    for idx_str, arr_str in re.findall(
        r"\bvar\s+eps(\d+)\s*=\s*(\[.*?\]);", content, re.DOTALL
    ):
        arr_clean = re.sub(r",\s*\]", "]", arr_str)
        try:
            items = json.loads(arr_clean)
        except Exception:
            items = re.findall(r'["\']([^"\']*)["\']', arr_str)
        eps_dict[int(idx_str)] = [str(x).strip() for x in items]
    return eps_dict


def _extract_list_names(html_or_js, total_count, prefix="Episode"):
    """
    Simule séquentiellement resetListe / creerListe / newSP / newSPF / finirListe
    pour obtenir la liste exacte des noms d'épisodes ou de chapitres.
    """
    cleaned = _strip_comments(html_or_js)
    names = []
    retards = 0
    matched_any = False

    for m in _LIST_TOKEN_RE.finditer(cleaned):
        matched_any = True
        if m.group(1):  # resetListe()
            names = []
            retards = 0
        elif m.group(2):  # creerListe(start, end)
            start, end = int(m.group(3)), int(m.group(4))
            for n in range(start, end + 1):
                names.append(f"{prefix} {n}")
        elif m.group(5):  # newSP / newSPF
            label = m.group(6) if m.group(6) is not None else m.group(7)
            if m.group(5) == "newSPF":
                names.append(label)
            else:
                names.append(f"{prefix} {label}")
            retards += 1
        elif m.group(8):  # finirListe / finirListeOP
            start = int(m.group(9))
            end = total_count - retards
            for n in range(start, end + 1):
                names.append(f"{prefix} {n}")

    if not matched_any and total_count > 0:
        return [f"{prefix} {n}" for n in range(1, total_count + 1)]
    return names


# ---------------------------------------------------------------------------
#  LISTE DES ÉPISODES ET SERVEURS
# ---------------------------------------------------------------------------

def episodes(url_path, vf=False, target_source=None):
    """
    Liste les épisodes d'un anime depuis une URL de catalogue anime-sama.
    Format : idx\tidx\t[Saison] NomEp\tserver_type,target\tavail_servers_csv
    target_source permet de forcer un serveur spécifique (ex: 'vidmoly', 'uqload', 'earnvids', 'voe').
    """
    domain = get_active_domain()
    complete_url = (
        f"https://{domain}{url_path}" if url_path.startswith("/") else url_path
    )

    html = make_request(complete_url)
    if not html:
        return

    cleaned_html = _strip_comments(html)
    seasons = []
    for match in re.finditer(
        r'panneauAnime\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
        cleaned_html,
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

        season_html = html if not subpath else make_request(
            season_url, referer=complete_url, silent_404=vf
        )
        if not season_html:
            continue

        raw_eps = _parse_season_eps(season_html)
        eps_meta = _extract_js_object(season_html, "epsMeta")
        lecteurs_infos = _extract_js_object(season_html, "lecteursInfos")
        jeton_match = re.search(
            r'var\s+epsJeton\s*=\s*["\']([^"\']+)["\']', season_html
        )
        eps_jeton = jeton_match.group(1) if jeton_match else ""

        js_content = ""
        if not raw_eps:
            # Fallback hérité uniquement si un <script src="...episodes.js..."> existe dans la page
            ep_js_match = re.search(
                r'<script[^>]+src=["\']([^"\']*episodes\.js[^"\']*)["\']',
                season_html,
                re.IGNORECASE,
            )
            if ep_js_match:
                ep_js_url = urllib.parse.urljoin(season_url, ep_js_match.group(1))
                js_content = make_request(ep_js_url, referer=season_url)
                if js_content:
                    raw_eps = _parse_season_eps(js_content)

        if not raw_eps:
            continue

        total_eps = max((len(arr) for arr in raw_eps.values()), default=0)
        if total_eps == 0:
            continue

        names_source = f"{season_html}\n{js_content}" if js_content else season_html
        episode_names = _extract_list_names(names_source, total_eps, prefix="Episode")
        sorted_player_keys = sorted(raw_eps.keys())

        for ep_idx in range(total_eps):
            candidates = []
            for p_idx in sorted_player_keys:
                arr = raw_eps[p_idx]
                if ep_idx >= len(arr):
                    continue
                entry = arr[ep_idx]
                if not entry:
                    continue

                if entry.startswith("lien:"):
                    link_id = entry[5:]
                    meta = eps_meta.get(link_id)
                    if not meta or not isinstance(meta, list):
                        continue
                    if len(meta) >= 2 and meta[1] in (1, 2):
                        continue
                    host = str(meta[0])
                    server_type = _canonical_server(host, lecteurs_infos)
                    if not server_type:
                        continue
                    target = f"lien:{link_id}|{eps_jeton}|{season_url}"
                    candidates.append((server_type, target))
                elif entry.startswith("http"):
                    host = urllib.parse.urlparse(entry).netloc
                    server_type = _canonical_server(host, lecteurs_infos)
                    if not server_type:
                        continue
                    candidates.append((server_type, entry))

            if not candidates:
                continue

            unique_servers = list(dict.fromkeys(srv for srv, _ in candidates))
            avail_servers = [srv for srv in SERVER_PRIORITY if srv in unique_servers]
            for srv in unique_servers:
                if srv not in avail_servers:
                    avail_servers.append(srv)
            avail_csv = ",".join(avail_servers)

            best_server, best_target = None, None
            if target_source:
                ts_low = target_source.lower()
                for srv, tgt in candidates:
                    if srv == ts_low or ts_low in srv:
                        best_server, best_target = srv, tgt
                        break

            if best_server is None:
                for p in SERVER_PRIORITY:
                    for srv, tgt in candidates:
                        if srv == p:
                            best_server, best_target = srv, tgt
                            break
                    if best_server is not None:
                        break

            if best_server is None:
                best_server, best_target = candidates[0]

            ep_name = (
                episode_names[ep_idx]
                if ep_idx < len(episode_names)
                else f"Episode {ep_idx + 1}"
            )
            prefix = f"[{season_name}] " if season_name else ""
            print(
                f"{global_i}\t{global_i}\t{prefix}{ep_name}\t{best_server},{best_target}\t{avail_csv}"
            )
            global_i += 1


def servers(server_data):
    """
    Affiche la liste de serveurs associée à une entrée server_data.
    Format de sortie : server_name\tserver_type,target
    """
    print(f"Default ({server_data.split(',', 1)[0]})\t{server_data}")


# ---------------------------------------------------------------------------
#  EXTRACTION DE LIENS VIDÉO
# ---------------------------------------------------------------------------

def _resolve_lien(link_id, jeton, season_url):
    """Résout un identifiant `lien:<id>` via `/api/lien.php` (avec rafraîchissement si expiré)."""
    if season_url and season_url.startswith("http"):
        parsed = urllib.parse.urlparse(season_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        referer = season_url
    else:
        domain = get_active_domain()
        origin = f"https://{domain}"
        referer = f"{origin}/"

    def _query(tok):
        api_url = (
            f"{origin}/api/lien.php?j={urllib.parse.quote(tok, safe='')}"
            f"&l={urllib.parse.quote(link_id, safe='')}"
        )
        raw = make_request(api_url, referer=referer)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    data = _query(jeton)
    if data and data.get("u"):
        return data["u"]

    if data and data.get("erreur") == "expire" and season_url:
        fresh_html = make_request(season_url, referer=f"{origin}/")
        if fresh_html:
            m = re.search(r'var\s+epsJeton\s*=\s*["\']([^"\']+)["\']', fresh_html)
            if m:
                data = _query(m.group(1))
                if data and data.get("u"):
                    return data["u"]

    err_msg = data.get("erreur") if isinstance(data, dict) else "reponse invalide"
    print(f"[anime-sama] Impossible de résoudre lien:{link_id} ({err_msg})", file=sys.stderr)
    return ""


def extract(server_data):
    """
    Extrait l'URL vidéo directe depuis les données du serveur.
    Format server_data : 'server_type,target'
    """
    if "," not in server_data:
        print(f"[anime-sama] Format server_data invalide : {server_data}", file=sys.stderr)
        return

    server_type, target = server_data.split(",", 1)
    if target.startswith("lien:"):
        parts = target[5:].split("|", 2)
        link_id = parts[0]
        jeton = parts[1] if len(parts) > 1 else ""
        season_url = parts[2] if len(parts) > 2 else ""
        resolved = _resolve_lien(link_id, jeton, season_url)
        if not resolved:
            return
        target = resolved

    video_url = extract_video_url(server_type, target)
    if video_url:
        print(video_url)


# ---------------------------------------------------------------------------
#  SCANS & CHAPITRES
# ---------------------------------------------------------------------------

def chapters(url_path, vf=False):
    """
    Liste les chapitres de scans d'une oeuvre depuis Anime-Sama.
    Affiche au format : idx\tidx\t[Section] Chapitre N (X pages)\tch_num,page_count,quoted_titre_oeuvre
    """
    domain = get_active_domain()
    complete_url = (
        f"https://{domain}{url_path}" if url_path.startswith("/") else url_path
    )

    html = make_request(complete_url)
    if not html:
        return

    cleaned_html = _strip_comments(html)
    scans_panels = []
    for match in re.finditer(
        r'panneauScan\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
        cleaned_html,
    ):
        scan_name = match.group(1)
        subpath = match.group(2)
        if subpath == "url" or scan_name == "nom":
            continue
        if vf and "vostfr" in subpath:
            subpath = subpath.replace("vostfr", "vf")
        scans_panels.append((scan_name, subpath))

    if not scans_panels:
        fallback_subpath = "scan/vf" if vf else "scan/vostfr"
        scans_panels.append(("Scans", fallback_subpath))

    global_i = 1
    for scan_name, subpath in scans_panels:
        scan_sub_url = complete_url
        if not scan_sub_url.endswith("/"):
            scan_sub_url += "/"
        scan_sub_url += subpath.strip("/") + "/"

        sub_html = make_request(scan_sub_url, referer=complete_url)
        if not sub_html:
            continue

        soup = BeautifulSoup(sub_html, "html.parser")
        titre_el = soup.find(id="titreOeuvre")
        # Préserver les espaces finaux exacts (ex: "One Piece ", "Naruto  ", "Bleach ")
        raw_titre = (
            titre_el.get_text().replace("\r", "").replace("\n", "")
            if titre_el
            else ""
        )
        slug = url_path.strip("/").split("/")[-1]
        slug_title = slug.replace("-", " ").title()

        candidates = []
        for cand in (raw_titre, raw_titre.strip(), slug_title):
            if cand and cand not in candidates:
                candidates.append(cand)

        chap_data = None
        working_titre = ""
        for cand in candidates:
            api_url = (
                f"https://{domain}/s2/scans/get_nb_chap_et_img.php"
                f"?oeuvre={urllib.parse.quote(cand, safe='')}"
            )
            api_res = make_request(api_url, referer=scan_sub_url)
            if not api_res or "error" in api_res:
                continue
            try:
                parsed = json.loads(api_res)
                if isinstance(parsed, dict) and parsed and "error" not in parsed:
                    chap_data = parsed
                    working_titre = cand
                    break
            except Exception:
                continue

        if not chap_data:
            continue

        max_chap = max((int(k) for k in chap_data.keys() if k.isdigit()), default=0)
        chap_names = _extract_list_names(sub_html, max_chap, prefix="Chapitre")

        def chap_key(k):
            try:
                return float(k)
            except ValueError:
                return float("inf")

        sorted_chaps = sorted(chap_data.keys(), key=chap_key)
        quoted_titre = urllib.parse.quote(working_titre, safe="")
        prefix = f"[{scan_name}] " if scan_name else ""

        for ch in sorted_chaps:
            pages_count = chap_data[ch]
            if ch.isdigit() and 1 <= int(ch) <= len(chap_names):
                chap_label = chap_names[int(ch) - 1]
            else:
                chap_label = f"Chapitre {ch}"
            print(
                f"{global_i}\t{global_i}\t{prefix}{chap_label} ({pages_count} pages)\t{ch},{pages_count},{quoted_titre}"
            )
            global_i += 1


def pages(chapter_data):
    """
    Extrait les URLs directes des images de chaque page pour un chapitre donné.
    chapter_data format: 'ch_num,page_count,quoted_titre_oeuvre'
    """
    domain = get_active_domain()
    parts = chapter_data.split(",")
    if len(parts) < 3:
        print(f"[anime-sama] Format chapter_data invalide : {chapter_data}", file=sys.stderr)
        return

    ch_num = parts[0]
    try:
        page_count = int(parts[1])
    except ValueError:
        page_count = 0
    quoted_titre = parts[2]

    for page in range(1, page_count + 1):
        print(f"https://{domain}/s2/scans/{quoted_titre}/{ch_num}/{page}.jpg")
