#!/usr/bin/env python3
"""
scrap/animesama/__main__.py
Point d'entrée CLI du package animesama.

Peut être lancé de deux façons :
  python scrap/animesama <action> <arg> [--vf] [--source <source_name>]
  python -m scrap.animesama <action> <arg> [--vf] [--source <source_name>]

Actions :
  search   <query> [--vf]                       Recherche un anime (VOSTFR par défaut, --vf pour VF)
  episodes <url_path> [--vf] [--source <src>]   Liste les épisodes d'un anime (avec source choisie si spécifiée)
  extract  <server_data>                        Extrait l'URL vidéo directe
"""
import sys
import os

# Ajoute la racine du projet au sys.path
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from scrap.animesama import search, episodes, extract, chapters, pages


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python scrap/animesama [search|episodes|chapters|pages|extract] [arg] [--vf] [--scans] [--source <src>]"
        )
        sys.exit(1)

    action = sys.argv[1]
    arg = sys.argv[2]
    vf = "--vf" in sys.argv
    scans = "--scans" in sys.argv

    target_source = None
    if "--source" in sys.argv:
        try:
            source_idx = sys.argv.index("--source")
            if source_idx + 1 < len(sys.argv):
                target_source = sys.argv[source_idx + 1]
        except ValueError:
            pass

    if action == "search":
        search(arg, vf=vf, scans=scans)
    elif action == "episodes":
        episodes(arg, vf=vf, target_source=target_source)
    elif action == "chapters":
        chapters(arg, vf=vf)
    elif action == "pages":
        pages(arg)
    elif action == "extract":
        extract(arg)
    else:
        print(f"[anime-sama] Action inconnue: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

