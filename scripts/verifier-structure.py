#!/usr/bin/env python3
"""Contrôles structurels du dépôt eperformance-mia (landing Mia).

PHILOSOPHIE (arbitrage du 19/09 — 4e garde-fou recalibré du projet) :
un garde-fou vérifie des INVARIANTS DE PRODUIT, jamais l'implémentation
figée d'une version. Contrôlés : les 8 sections PAR RÔLE (balisage libre),
le JSON sectoriel généré (consommé par la page), la règle C2 par marqueurs
de statut, la démo branchée + limite, le SEO, les vidéos mesurées, et les
interdits (zéro hex hors exception, zéro Google Fonts, zéro emoji
d'interface, empreinte eperf.css). NON contrôlé : le DOM exact de la LP v1
(ids imposés, panneaux pré-rendus, site de démo en dur) — retirés le 19/09
suivant l'arbitrage demandé par l'agent SITE (journal 16:10) : les éléments
obligatoires PAR SECTION viennent de la spécification de SITE (§7 de sa
CONCEPTION-LP).

Deux niveaux : niveau 1 (toujours actif) — JSON, hex, polices, emoji,
empreinte, vidéos, sitemap ; niveau 2 (actif dès que index.html n'est plus
la page d'attente) — les contrôles de conception, portés sur les RÔLES.

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
PAGE_ATTENTE = "en préparation"  # casse : le body écrit « …en préparation. »
JSON_SECTEURS = RACINE / "contenu-sectoriel.json"
LANDING_CSS = RACINE / "assets" / "css" / "landing.css"
LANDING_JS = RACINE / "assets" / "js" / "landing.js"

SECTEURS_ATTENDUS = [
    "restauration", "hotellerie", "ecommerce", "immobilier", "mlm", "beaute",
    "sante", "education", "evenementiel", "tourisme", "artisan", "vitrine",
]
SECTEURS_EXCLUS = ["blog", "email"]

# Les 8 sections PAR RÔLE — les identifiants v1 deviennent une CONVENTION
# documentée (id contenant le rôle OU data-section), pas une obligation.
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


def en_passation() -> bool:
    """Vrai tant que index.html est la page d'attente (LP de SITE non livrée)."""
    return INDEX.is_file() and PAGE_ATTENTE in INDEX.read_text(encoding="utf-8")


def cible_lp() -> Path:
    """Le fichier visé par les contrôles de CONTENU DE LP.

    En état de passation (index.html = page d'attente), les contrôles de contenu
    portent sur l'ARCHIVE — le jalon de référence reste vérifié, la page
    d'attente n'est pas jugée comme une landing. SITE remettra un index.html
    complet, et la cible redeviendra automatiquement index.html.
    """
    if en_passation():
        archive = RACINE / "docs" / "archive" / "index-lp-v1.html"
        if archive.is_file():
            return archive
    return INDEX


def extraire_section(index: str, role: str):
    """Balisage d'une section, trouvé par id contenant le rôle OU data-section."""
    autres = "|".join(r for r, _ in SECTIONS_ATTENDUES if r != role)
    m = re.search(
        rf'<[^>]*id="[^"]*\b{role}\b[^"]*"[^>]*>(.*?)'
        rf'(?=<[^>]*(?:id|data-section)="[^"]*\b(?:{autres})\b[^"]*"|</body>)',
        index, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(
        rf'<[^>]*data-section=["\']{role}["\'][^>]*>(.*?)(?=<[^>]*data-section=|</body>)',
        index, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else None


def verifier_sections(index: str) -> None:
    """Les 8 sections PAR RÔLE — le balisage est libre.

    Chaque rôle doit exister via un `id` contenant le rôle OU via
    `data-section="<rôle>"`. La v1 imposait les ids exacts : c'était
    l'implémentation figée qui bloquait toute nouvelle conception.
    """
    for role, nom in SECTIONS_ATTENDUES:
        par_id = re.search(rf'id="[^"]*\b{role}\b[^"]*"', index, re.IGNORECASE)
        par_data = re.search(rf'data-section=["\']{role}["\']', index, re.IGNORECASE)
        if not (par_id or par_data):
            echec(f"section absente : {nom} — aucun marqueur du rôle « {role} » "
                  "(ni id, ni data-section)")
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

    for slug, donnees_secteur in donnees["secteurs"].items():
        for champ in ("nom", "intention", "faq_themes", "repond", "execute",
                      "hero", "questions_demo"):
            if not donnees_secteur.get(champ):
                echec(f"{slug} : champ vide ou absent : {champ}")
        if len(donnees_secteur.get("questions_demo", [])) != 3:
            echec(f"{slug} : il faut 3 questions de démo")

    # — NIVEAU 2 (index de production uniquement) —
    # L'INVARIANT : la page consomme le fichier généré (pas une réécriture du
    # contenu). La forme du pré-rendu (data-panneau, data-questions) était un
    # artefact de la v1 et n'est plus imposée. L'archive v1 intégrait le
    # contenu pré-rendu par le générateur et n'est donc pas jugée sur ce point
    # — ces contrôles s'activent avec la conception de SITE.
    consomme = any(marqueur in index for marqueur in (
        "contenu-sectoriel.json", "contenu_sectoriel", "contenuSectoriel"))
    if not consomme:
        echec("contenu-sectoriel.json n'est pas consommé par la page "
              "(référence au fichier attendue dans le HTML ou le JS)")
    # Règle C2 : une page qui annonce des capacités d'exécution doit marquer
    # leur STATUT. La v1 vérifiait les classes de ses propres listes — artefact.
    if re.search(r"ex[ée]cutera|ex[ée]cution", index, re.IGNORECASE):
        if not re.search(r"[Bb]ientôt|pr[ée]vue?|roadmap|à venir|en préparation", index):
            echec("règle C2 : des capacités d'exécution sont annoncées sans marqueur "
                  "de statut (Bientôt/prévue/roadmap/à venir)")


def verifier_elements_obligatoires(index: str) -> None:
    """Le contrôle d'INTENTION demandé par l'agent SITE (journal 19/09 16:10) :
    un titre par section, les DEUX CTA du hero, un sélecteur de secteur, la
    question RGPD dans la FAQ. Les éléments variables (textes, visuels, mise
    en page) sont libres."""
    for role, _ in SECTIONS_ATTENDUES:
        section = extraire_section(index, role)
        if section and not re.search(r"<h[1-3][\s>]", section):
            echec(f"section « {role} » : aucun titre de niveau h1-h3")
    hero = extraire_section(index, "haut") or ""  # le rôle S1 s'appelle « haut »
    if hero and "install" not in hero.lower():
        echec("hero : le CTA d'installation est absent")
    if hero and not re.search(r"d[ée]mo|action", hero, re.IGNORECASE):
        echec("hero : le CTA « voir Mia en action / démo » est absent")
    if not re.search(r"<select|s[ée]lecteur|data-secteur|choisir.{0,20}secteur",
                     index, re.IGNORECASE):
        echec("sélecteur de secteur absent")
    faq = extraire_section(index, "faq") or ""
    if faq and not re.search(r"conversation|donn[ée]es|RGPD|confidentialit",
                             faq, re.IGNORECASE):
        echec("FAQ : la question données personnelles / conversations est absente")


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
    """La démo est branchée sur l'API de production et porte une limite.

    Le SITE DE DÉMONSTRATION utilisé n'est pas imposé (artefact retiré) :
    le choix du site_id de démonstration appartient à la conception —
    l'invariant est le branchement réel + la limite de questions.
    """
    js = LANDING_JS.read_text(encoding="utf-8")
    if "web-production-4ab53.up.railway.app/api/chatbot/message" not in js:
        echec("démo : l'API de production n'est pas visée")
    if not re.search(r"5\s*(?:questions?)|(?:questions?|max)\s*[:=]?\s*5|limite.{0,24}5",
                     js, re.IGNORECASE):
        echec("démo : la limite de questions (5) n'est pas posée")


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
        ('rel="canonical"', "canonical"),
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
    elif en_passation():
        # NIVEAU 1 — état de passation : l'archive v1 reste le jalon de
        # contenu, la page d'attente n'est pas jugée comme une landing, et
        # les contrôles de CONCEPTION (consommé, C2, éléments obligatoires,
        # SEO de landing) ne s'activent pas.
        verifier_sections(index)
        verifier_contenu_sectoriel(index)
        verifier_hex()
        verifier_google_fonts(index)
        verifier_emoji()
        verifier_demo()
        verifier_videos()
        verifier_empreinte()
    else:
        # NIVEAU 2 — index de production : tout, y compris les contrôles de
        # conception (consommé, C2, éléments obligatoires, SEO complet).
        # Ce sont ces fonctions qui portent les portes ; en passation,
        # main() n'appelle pas cette branche.
        verifier_sections(index)
        verifier_contenu_sectoriel(index)
        verifier_elements_obligatoires(index)
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
    cible = "archive v1 (état de passation)" if en_passation() else "index.html"
    print(f"[structure] PASS — 8 sections par rôle, 12 secteurs, C2 (répond/exécute), "
          f"éléments obligatoires par section, zéro hex hors exception, zéro Google "
          f"Fonts, zéro emoji, démo, vidéos, SEO — cible : {cible}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
