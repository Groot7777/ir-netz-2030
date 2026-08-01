#!/usr/bin/env python3
"""Scan a KML (or any text) file for likely missed ue/oe/ae -> ü/ö/ä transliterations.
Flags every 'ue', 'oe', 'ae' substring occurrence (case-insensitive, word-boundary
aware) except for words on the exception list (real German/other words that
legitimately contain these letter sequences without needing an umlaut)."""
import re
import sys

EXCEPTIONS = {
    "sauerland", "engpass", "anschluss", "auerbach", "bauer", "mauer", "sauer",
    "trauer", "abenteuer", "steuer", "feuer", "ungeheuer", "gebaeude".replace("ae", "ae"),
    "museum", "aerodynamisch", "aerodynamische", "aerodynamischen", "aero-shuttle",
    "aeroshuttle", "haemorrhage", "boegen", "coesfeld",
}

WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")
TARGET_RE = re.compile(r"(ue|oe|ae)", re.IGNORECASE)


def scan_text(text):
    findings = []
    for m in WORD_RE.finditer(text):
        word = m.group(0)
        if word.lower() in EXCEPTIONS:
            continue
        if TARGET_RE.search(word):
            findings.append((m.start(), word))
    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: scan_umlauts.py <file.kml>", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    findings = scan_text(text)
    seen_words = {}
    for pos, word in findings:
        seen_words.setdefault(word, []).append(pos)
    if not seen_words:
        print("Keine verdaechtigen ue/oe/ae-Vorkommen gefunden.")
        return
    print(f"{len(seen_words)} verdaechtige Woerter ({len(findings)} Vorkommen gesamt):")
    for word in sorted(seen_words, key=lambda w: w.lower()):
        print(f"  {word!r}  x{len(seen_words[word])}")


if __name__ == "__main__":
    main()
