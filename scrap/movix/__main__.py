#!/usr/bin/env python3
"""
scrap/movix/__main__.py
Point d'entrée CLI du package movix.

Peut être lancé de deux façons :
  python scrap/movix <action> <arg> [options]
  python -m scrap.movix <action> <arg> [options]

Actions :
  search   <query>   [--type anime|tv|movie|multi] [--mode vf|sub]
  episodes <id>      [--type ...] [--season N] [--mode vf|sub]
  extract  <server_data>

Le mode par défaut est VOSTFR (--mode sub).
"""
import sys
import io
import os

# Force UTF-8 output (nécessaire sur Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ajoute la racine du projet (2 niveaux au-dessus de ce fichier) au sys.path
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from scrap.movix import search, episodes, extract


def main():
    if len(sys.argv) < 3:
        print("Usage: python scrap/movix [search|episodes|extract] [arg] [options]")
        sys.exit(1)

    action = sys.argv[1]
    arg = sys.argv[2]

    # Valeurs par défaut
    content_type = "multi"
    season_num = 1
    lang_mode = "sub"  # VOSTFR par défaut

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
            lang_mode = args_rest[i + 1]
            i += 2
        elif a in ("movie", "tv", "anime", "multi"):
            content_type = a
            i += 1
        else:
            i += 1

    if action == "search":
        search(arg, content_type=content_type, lang_mode=lang_mode)
    elif action == "episodes":
        episodes(arg, season_num=season_num, lang_mode=lang_mode)
    elif action == "extract":
        extract(arg)
    else:
        print(f"[movix] Action inconnue: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
