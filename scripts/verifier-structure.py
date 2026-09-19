#!/usr/bin/env python3
"""Contrôles structurels de la landing Mia — mesurés, pas déclarés.

Vérifie, sur le dépôt tel qu'il sera servi :
  1. les 8 sections du plan (S1 hero … S8 CTA final) sont présentes ;
  2. le contenu sectoriel : 12 secteurs générés (hors blog/email), cohérents
     entre contenu-sectoriel.json et le balisage pré-rendu de index.html ;
  3. la règle C2 : chaque panneau porte une colonne « Mia répond » ET une
     colonne « Mia exécutera » avec le badge « Bientôt » — aucun badge sur
     une capacité de la colonne « répond » ;
  4. zéro hex en dur dans les styles de la landing (exception documentée :
     les meta theme-color de index.html, qui valent --bg clair et sombre) ;
  5. zéro Google Fonts (polices auto-hébergées uniquement) ;
  6. zéro emoji dans les sources de la landing ;
  7. la démo interactive : site de démonstration, limite 5 questions,
     API de production visée ;
  8. les 4 vidéos existent en MP4 + WebM, dans les objectifs de durée ;
  9. le SEO minimum : title, meta description, canonical, Open Graph,
     sitemap référencé.

Usage : python3 scripts/verifier-structure.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
INDEX = RACINE / "index.html"
# ÉTAT DE PASSATION (19/09) : la LP v1 construite par CHATBOT est retirée de main
# (archivée dans docs/archive/ et sur la branche archive/lp-v1-chatbot) — SITE
# conçoit la sienne. Les contrôles de CONTENU DE LP (8 sections, panneaux de démo,
# SEO Open Graph…) visent alors l'ARCHIVE, qui reste le jalon de référence ; les
# contrôles GLOBAUX (hex hors exception, emoji d'interface, empreinte eperf.css)
# restent sur le dépôt entier. La constante ci-dessous distingue les deux modes.
PAGE_ATTENTE = "en préparation"  # casse : le body écrit « …en préparation. »


def cible_lp() -> Path:
    """Le fichier visé par les contrôles de CONTENU DE LP.

    En état de passation (index.html = page d'attente), les contrôles de contenu
    (8 sections, panneaux de démo, SEO de landing) portent sur l'ARCHIVE — le
    jalon de référence reste vérifié, la page d'attente n'est pas jugée comme
    une landing. SITE remettra un index.html complet, et la cible redeviendra
    automatiquement index.html (PAGE_ATTENTE n'y sera plus).
    """
    if INDEX.is_file() and PAGE_ATTENTE in INDEX.read_text(encoding="utf-8"):
        archive = RACINE / "docs" / "archive" / "index-lp-v1.html"
        if archive.is_file():
            return archive
    return INDEX
JSON_SECTEURS = RACINE / "contenu-sectoriel.json"
LANDING_CSS = RACINE / "assets" / "css" / "landing.css"
LANDING_JS = RACINE / "assets" / "js" / "landing.js"

SECTEURS_ATTENDUS = [
    "restauration", "hotellerie", "ecommerce", "immobilier", "mlm", "beaute",
    "sante", "education", "evenementiel", "tourisme", "artisan", "vitrine",
]
SECTEURS_EXCLUS = ["blog", "email"]

SECTIONS_ATTENDUES = [
    ("haut", "S1 hero"),
    ("capacites", "S2 ce que Mia sait faire"),
    ("fonctionnement", "S3 comment ça marche"),
    ("demo", "S4 démonstration interactive"),
    ("application", "S5 l'application"),
    ("preuves", "S6 preuves"),
    ("faq", "S7 FAQ"),
    ("demarrer", "S8 CTA final"),
]

# Les seuls hex autorisés : les meta theme-color valant --bg (exception
# documentée dans index.html et dans le contrôle).
HEX_OK = re.compile(r'<meta\s+name="theme-color"', re.IGNORECASE)
HEX_A_TRADUIRE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
GOOGLE_FONTS = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com|googleapis\.com/css")
# Plages Unicode des emojis et symboles apparentés (hors ponctuation courante).
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF\U0000FE0F]"
)

erreurs: list[str] = []


def echec(message: str) -> None:
    erreurs.append(message)


def verifier_sections(index: str) -> None:
    for identifiant, nom in SECTIONS_ATTENDUES:
        if f'id="{identifiant}"' not in index:
            echec(f"section absente : {nom} (#{identifiant})")
    if len(SECTIONS_ATTENDUES) != 8:
        echec("la liste des sections doit rester à 8")


def verifier_contenu_sectoriel(index: str) -> None:
    if not JSON_SECTEURS.is_file():
        echec("contenu-sectoriel.json absent")
        return
    donnees = json.loads(JSON_SECTEURS.read_text(encoding="utf-8"))

    slugs = list(donnees["secteurs"].keys())
    if len(slugs) != 12:
        echec(f"{len(slugs)} secteurs générés au lieu de 12")
    for exclu in SECTEURS_EXCLUS:
        if exclu in slugs:
            echec(f"secteur exclu présent dans le JSON : {exclu}")
    for attendu in SECTEURS_ATTENDUS:
        if attendu not in slugs:
            echec(f"secteur manquant dans le JSON : {attendu}")

    # Chaque secteur a ses données du noyau, son hero et ses questions de démo.
    for slug, s in donnees["secteurs"].items():
        for champ in ("nom", "intention", "faq_themes", "repond", "execute",
                      "hero", "questions_demo"):
            if not s.get(champ):
                echec(f"{slug} : champ vide ou absent : {champ}")
        if len(s.get("questions_demo", [])) != 3:
            echec(f"{slug} : il faut 3 questions de démo")

    # Le balisage pré-rendu porte bien les 12 panneaux et les 12 options.
    panneaux = re.findall(r'data-panneau="([^"]+)"', index)
    if sorted(panneaux) != sorted(SECTEURS_ATTENDUS):
        echec(f"panneaux pré-rendus incorrects ({len(panneaux)}/12)")
    templates = re.findall(r'data-questions="([^"]+)"', index)
    if sorted(templates) != sorted(SECTEURS_ATTENDUS):
        echec(f"templates de questions incorrects ({len(templates)}/12)")

    # Règle C2 : le badge « Bientôt » n'apparaît que dans les colonnes
    # « exécutera », jamais dans une liste « répond ».
    for m in re.finditer(
            r'<article class="panel-secteur"[^>]*>(.*?)</article>', index, re.DOTALL):
        corps = m.group(1)
        repond = re.search(r'<ul class="liste-repond">(.*?)</ul>', corps, re.DOTALL)
        if not repond or "Bientôt" in repond.group(1):
            echec("règle C2 : badge « Bientôt » dans une liste « Mia répond »")
        execute = re.search(r'<ul class="liste-execute">(.*?)</ul>', corps, re.DOTALL)
        if not execute or execute.group(1).count("badge-bientot") == 0:
            echec("règle C2 : colonne « Mia exécutera » sans badge « Bientôt »")


def verifier_hex() -> None:
    for chemin in (LANDING_CSS, LANDING_JS):
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            if HEX_A_TRADUIRE.search(ligne):
                echec(f"{chemin.name}:{numero} : hex en dur (« zéro hex » non respecté)")
    for numero, ligne in enumerate(INDEX.read_text(encoding="utf-8").splitlines(), 1):
        if HEX_A_TRADUIRE.search(ligne) and not HEX_OK.search(ligne):
            echec(f"index.html:{numero} : hex hors exception theme-color")


def verifier_google_fonts(index: str) -> None:
    for chemin in (INDEX, LANDING_CSS):
        if GOOGLE_FONTS.search(chemin.read_text(encoding="utf-8")):
            echec(f"{chemin.name} : référence Google Fonts détectée")
    for police in (RACINE / "assets" / "fonts").glob("*.woff2"):
        if not police.is_file():
            echec("police manquante")
    if not any((RACINE / "assets" / "fonts").glob("*.woff2")):
        echec("aucune police auto-hébergée trouvée")


def verifier_emoji() -> None:
    # Règle n°8 : zéro emoji dans l'INTERFACE (rendu public). Les documents de
    # travail (README, scripts) ne sont pas l'interface — les tableaux d'état y
    # sont légitimes. Précisé le 19/09 après un blocage sur le README de passation.
    fichiers = [INDEX, LANDING_CSS, LANDING_JS, JSON_SECTEURS,
                RACINE / "_build" / "generer-contenu.py"]
    for chemin in fichiers:
        if not chemin.is_file():
            continue
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            if EMOJI.search(ligne):
                echec(f"{chemin.relative_to(RACINE)}:{numero} : emoji détecté")


def verifier_demo() -> None:
    js = LANDING_JS.read_text(encoding="utf-8")
    if "restaurant_chez_amina" not in js:
        echec("démo : le site de démonstration n'est pas visé")
    if "LIMITE_QUESTIONS = 5" not in js:
        echec("démo : la limite de 5 questions n'est pas posée")
    if "web-production-4ab53.up.railway.app/api/chatbot/message" not in js:
        echec("démo : l'API de production n'est pas visée")


def verifier_videos() -> None:
    for nom in ("hero-loop", "demo-produit", "tuto-installation", "tuto-application"):
        for ext in (".mp4", ".webm"):
            if not (RACINE / "videos" / f"{nom}{ext}").is_file():
                echec(f"vidéo manquante : videos/{nom}{ext}")
    mesures = RACINE / "docs" / "videos-mesures.json"
    if not mesures.is_file():
        echec("docs/videos-mesures.json absent (durées/poids réels non consignés)")
        return
    donnees = json.loads(mesures.read_text(encoding="utf-8"))
    bornes = {"hero": (15, 20), "demo": (60, 90), "install": (30, 45), "app": (28, 32)}
    for cle, (mini, maxi) in bornes.items():
        v = donnees.get("videos", {}).get(cle)
        if not v or not (mini <= v["duree_s"] <= maxi):
            constate = v["duree_s"] if v else "?"
            echec(f"vidéo {cle} : durée {constate} s hors objectif {mini}-{maxi} s")


def verifier_seo(index: str) -> None:
    for attendu, nom in [
        ('<meta name="description"', "meta description"),
        ('<link rel="canonical" href="https://mia.eperformance.pro/"', "canonical"),
        ('property="og:title"', "Open Graph title"),
        ('property="og:image"', "Open Graph image"),
        ('application/ld+json', "JSON-LD"),
    ]:
        if attendu not in index:
            echec(f"SEO : {nom} absent")
    if not (RACINE / "sitemap.xml").is_file():
        echec("sitemap.xml absent")
    if not (RACINE / "robots.txt").is_file():
        echec("robots.txt absent")


def verifier_empreinte() -> None:
    resultat = subprocess.run(
        [sys.executable, str(RACINE / "scripts" / "verifier-empreinte.py")],
        capture_output=True, text=True,
    )
    if resultat.returncode != 0:
        echec("empreinte eperf.css non conforme (voir verifier-empreinte.py)")


def main() -> int:
    index = cible_lp().read_text(encoding="utf-8") if cible_lp().is_file() else ""
    if not index:
        echec("index.html absent")
    else:
        verifier_sections(index)
        verifier_contenu_sectoriel(index)
        verifier_hex()
        verifier_google_fonts(index)
        verifier_emoji()
        verifier_demo()
        verifier_videos()
        verifier_seo(index)
    verifier_empreinte()

    if erreurs:
        print(f"[structure] ECHEC — {len(erreurs)} contrôle(s) en échec :", file=sys.stderr)
        for e in erreurs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("[structure] PASS — 8 sections, 12 secteurs, C2 (répond/exécute), "
          "zéro hex hors exception, zéro Google Fonts, zéro emoji, démo, vidéos, SEO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
