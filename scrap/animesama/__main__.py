#!/usr/bin/env python3
"""
scrap/animesama/__main__.py
Point d'entrée CLI du package animesama.

Peut être lancé de deux façons :
  python scrap/animesama <action> <arg> [--vf]
  python -m scrap.animesama <action> <arg> [--vf]

Actions :
  search   <query> [--vf]       Recherche un anime (VOSTFR par défaut, --vf pour VF)
  episodes <url_path> [--vf]    Liste les épisodes d'un anime
  extract  <server_data>        Extrait l'URL vidéo directe
"""
import sys
import os

# Ajoute la racine du projet (2 niveaux au-dessus de ce fichier) au sys.path
# pour que "from scrap.animesama import ..." fonctionne correctement
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from scrap.animesama import search, episodes, extract


def main():
    if len(sys.argv) < 3:
        print("Usage: python scrap/animesama [search|episodes|extract] [arg] [--vf]")
        sys.exit(1)

    action = sys.argv[1]
    arg = sys.argv[2]
    vf = "--vf" in sys.argv

    if action == "search":
        search(arg, vf=vf)
    elif action == "episodes":
        episodes(arg, vf=vf)
    elif action == "extract":
        extract(arg)
    else:
        print(f"[anime-sama] Action inconnue: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
