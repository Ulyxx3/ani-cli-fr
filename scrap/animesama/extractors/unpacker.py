"""
unpacker.py - Décompacteur JavaScript Dean Edwards (eval(function(p,a,c,k,e,d)...)).
"""
import re

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_PACKER_RE = re.compile(
    r"eval\(function\(p,a,c,k,e,[dr]\)\{.*?\}\("
    r"'((?:\\.|[^'\\])*)'\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'((?:\\.|[^'\\])*)'\.split\('\|'\)",
    re.DOTALL,
)


def _unescape_js_literal(text: str) -> str:
    return re.sub(r"\\([\\'\"])", r"\1", text)


def _decode_base(token: str, radix: int) -> int:
    valid = _ALPHABET[:radix]
    val = 0
    for ch in token:
        idx = valid.find(ch)
        if idx == -1:
            return -1
        val = val * radix + idx
    return val


def unpack_all(html: str) -> list[str]:
    """
    Extrait et décompacte tous les blocs Dean Edwards présents dans une page HTML.
    """
    results: list[str] = []
    if not html:
        return results

    for match in _PACKER_RE.finditer(html):
        payload = _unescape_js_literal(match.group(1))
        radix = int(match.group(2))
        symtab_raw = _unescape_js_literal(match.group(4))
        symtab = symtab_raw.split("|")

        if radix < 2 or radix > len(_ALPHABET):
            continue

        def _replace(tok_match: re.Match) -> str:
            token = tok_match.group(0)
            idx = _decode_base(token, radix)
            if 0 <= idx < len(symtab) and symtab[idx]:
                return symtab[idx]
            return token

        results.append(re.sub(r"\b\w+\b", _replace, payload))

    return results
