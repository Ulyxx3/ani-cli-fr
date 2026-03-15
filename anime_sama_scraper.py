#!/usr/bin/env python3
import sys
import json
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

HEADERS_BASE = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "connection": "keep-alive"
}

def make_request(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS_BASE)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return ""

def get_active_domain():
    try:
        html = make_request("https://anime-sama.pw")
        match = re.search(r"return\s+['\"](anime-sama\.[a-z]+)['\"]", html)
        if match:
            return match.group(1)
    except:
        pass
    return "anime-sama.si"

def search(query, vf=False):
    domain = get_active_domain()
    url = f"https://{domain}/catalogue/"
    params = {"search": query}
    if vf:
        params["langue[]"] = "VF"
        
    html = make_request(url, params)
    soup = BeautifulSoup(html, 'html.parser')
    
    results = []
    for card in soup.find_all('a', href=True):
        titre_tag = card.find('h1')
        if titre_tag and 'catalogue' in card['href']:
            titre = titre_tag.text.strip()
            # href is something like "/catalogue/naruto/"
            href = card['href']
            # if VF is requested but not present in the link natively, add it
            if vf and "vostfr" in href:
                href = href.replace("vostfr", "vf")
            results.append((href, titre))
            
    # Output format compatible with ani-cli parser: "URL\tTITLE"
    for idx, (url, title) in enumerate(results):
        print(f"{url}\t{title}")

def _extract_episodes_from_js(content):
    episode_list = []
    special_matches = re.findall(r'creerListe\((\d+),\s*(\d+)\);\s*newSPF?\(["\']([^"\']+)["\']\);?', content)
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
        end_finir = start_finir + 50 # Fallback 50 episodes
        
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

def episodes(url_path):
    domain = get_active_domain()
    complete_url = f"https://{domain}{url_path}" if url_path.startswith('/') else url_path
    
    # Needs episodes.js version
    html = make_request(complete_url)
    filever = "1"
    match = re.search(r'episodes\.js\?filever=(\d+)', html)
    if match:
        filever = match.group(1)
        
    js_url = f"{complete_url}/episodes.js?filever={filever}"
    if not js_url.startswith('https://'):
        js_url = f"https://{domain}{url_path}/episodes.js?filever={filever}"
        
    content = make_request(js_url)
    
    # Parse arrays
    arrays = re.findall(r'var eps(\d+) = \[(.*?)\];', content, re.DOTALL)
    best_server = None
    best_episodes = []
    
    if arrays:
        for array_num, array_content in arrays:
            sibnet_matches = list(re.finditer(r'https://video\.sibnet\.ru/shell\.php\?videoid=(\d+)', array_content))
            if sibnet_matches and not best_server:
                best_server = 'sibnet'
                best_episodes = [(m.group(1), 'sibnet') for m in sibnet_matches]
                break
                
            vidmoly_matches = list(re.finditer(r'https://vidmoly\.[a-z]+/embed-([^.]+)\.html', array_content))
            if vidmoly_matches and not best_server:
                best_server = 'vidmoly'
                best_episodes = [(m.group(1), 'vidmoly') for m in vidmoly_matches]
                
    if not best_episodes:
        sibnet_matches = list(re.finditer(r'https://video\.sibnet\.ru/shell\.php\?videoid=(\d+)', content))
        if sibnet_matches:
            best_server = 'sibnet'
            best_episodes = [(m.group(1), 'sibnet') for m in sibnet_matches]
            
    episode_names = _extract_episodes_from_js(content)
    
    for i, (video_id, server_type) in enumerate(best_episodes):
        ep_name = episode_names[i] if i < len(episode_names) else f"Episode {i+1}"
        # Format: "server,video_id    ep_name"
        print(f"{server_type},{video_id}\t{ep_name}")

def extract(server_data):
    server_type, video_id = server_data.split(',')
    
    if server_type == 'sibnet':
        url = f"https://video.sibnet.ru/shell.php?videoid={video_id}"
        html = make_request(url)
        match = re.search(r'player\.src\(\[\{src: "/v/([^/]+)/', html)
        if match:
            video_hash = match.group(1)
            mp4_url = f"https://video.sibnet.ru/v/{video_hash}/{video_id}.mp4"
            req = urllib.request.Request(mp4_url, headers={**HEADERS_BASE, "referer": "https://video.sibnet.ru/"})
            try:
                # We expect a 302 redirect here to get the actual direct URL
                class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, req, fp, code, msg, headers, newurl):
                        return None
                opener = urllib.request.build_opener(NoRedirectHandler())
                opener.open(req, timeout=10)
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    print(e.headers['Location'])
                    return
            except Exception:
                pass
                
    elif server_type == 'vidmoly':
        for domain in ['vidmoly.net', 'vidmoly.to']:
            embed_url = f"https://{domain}/embed-{video_id}.html"
            html = make_request(embed_url)
            hls_patterns = [
                r'sources:\s*\[\s*\{\s*file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
            ]
            for pattern in hls_patterns:
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    video_url = match.group(1)
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    print(video_url)
                    return
        print(f"https://vidmoly.net/embed-{video_id}.html")
        return

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scraper.py [search|episodes|extract] [arg]")
        sys.exit(1)
        
    action = sys.argv[1]
    arg = sys.argv[2]
    vf = False
    
    if len(sys.argv) > 3 and sys.argv[3] == "--vf":
        vf = True
        
    if action == "search":
        search(arg, vf)
    elif action == "episodes":
        episodes(arg)
    elif action == "extract":
        extract(arg)
