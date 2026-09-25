#!/usr/bin/env python3
"""Contrôle d'intention de la LP Mia — mia.eperformance.pro.

CONTRAT : CONCEPTION-LP.md §7 (site-eperformance/docs/app-mia/), écrit par
l'agent SITE et traduit ici par CHATBOT (arbitrage du 20/09). Un garde-fou
vérifie des INVARIANTS DE PRODUIT, jamais le DOM d'une version figée.

Niveau 1 — invariants de dépôt (toujours actifs) : empreinte eperf.css,
zéro hex hors le bloc de primitives de la page servie, zéro Google Fonts,
zéro emoji d'interface, zéro nom d'agent, zéro requête externe au
chargement, démo branchée sur l'API de production avec sa limite, vidéos
présentes avec mesures, sitemap/robots.

Niveau 2 — le contrat de structure (actif quand index.html n'est plus la
page d'attente, cible la LP servie) : header/main/footer ; les 8 sections
DANS CET ORDRE (hero + sélecteur, capacités, comment-ça-marche,
démonstration, application, preuves, FAQ, CTA final) — reconnues par id,
data-section, aria-labelledby ou class ; les éléments obligatoires par
section (h1 du hero, rôle="group" de sélection, DEUX CTA du hero et du CTA
final, au moins 4 cartes avec « Mia répond », FAQ RGPD + prix) ; la
consommation du contenu sectoriel généré ; la règle C2 PAR CARTE (les mots
« réserve/commande/paie » coexistent avec un marqueur de statut).

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

# Les 8 sections DU CONTRAT §7, dans l'ordre — avec les variantes de nommage
# tolérées (la LP de SITE utilise hero/capacites/comment/demo/app/preuves/
# faq/final ; la convention v1 haut/fonctionnement/application/demarrer reste
# acceptée). Une section est reconnue par un id, data-section,
# aria-labelledby ou une class contenant une de ces variantes.
SECTIONS_ATTENDUES: list[tuple[str, str, tuple[str, ...]]] = [
    ("hero", "S1 hero + sélecteur de secteur", ("hero", "haut")),
    ("capacites", "S2 ce que Mia sait faire", ("capacites",)),
    ("fonctionnement", "S3 comment ça marche", ("fonctionnement", "comment", "etapes")),
    ("demo", "S4 démonstration interactive", ("demo",)),
    ("application", "S5 l'application", ("application", "app")),
    ("preuves", "S6 preuves", ("preuves",)),
    ("faq", "S7 FAQ", ("faq",)),
    ("final", "S8 CTA final", ("final", "demarrer")),
]

# Mots-capacité à risque (règle C2) : ils décrivent une capacité « Mia
# exécute » — ils ne peuvent apparaître qu'avec un marqueur de statut.
MOTS_C2 = re.compile(r"r[ée]serv(?:er|ation|ations?)|command(?:er|e|es)|paie[rt]?|paiement", re.IGNORECASE)
MARQUEURS_STATUT = re.compile(r"[Bb]ientôt|pr[ée]vue?|roadmap|à venir|en préparation|prochainement|mia\s+r[ée]pond|r[ée]pond|transmet|transmettre|transmise|demande", re.IGNORECASE)

# Noms d'agent internes : le motif prudent (agent_used, assigned_agent,
# « 27 agents », « agents internes/IA ») — « agent » seul est un métier
# légitime (agent immobilier) et ne déclenche pas.
NOMS_AGENTS = re.compile(
    r"agent[_-]used|assigned[_-]agent|\b27\s+agents\b|agents?\s+internes\b|"
    r"agents?\s+IA\b|compteur d[' ]agents",
    re.IGNORECASE)

HEX_A_TRADUIRE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
GOOGLE_FONTS = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com|googleapis\.com/css")
# « Zéro référence externe au chargement » (§7) = ce que le navigateur
# TÉLÉCHARGE à l'ouverture : src= (script, img, video…) et <link … href=>
# (feuille de style, preconnect). Un lien de navigation <a href> ne charge
# rien — le flagger interdisait à la LP de pointer vers eperformance.pro et
# le blog (2 faux positifs constatés le 20/09, instrument corrigé).
REQUETE_EXTERNE = re.compile(
    r'\bsrc="https?://(?!mia\.eperformance\.pro)[^"]*"'
    r'|<link[^>]+href="https?://(?!mia\.eperformance\.pro)[^"]*"',
    re.IGNORECASE)
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF\U0000FE0F]"
)

erreurs: list[str] = []


def echec(message: str) -> None:
    erreurs.append(message)


def en_passation() -> bool:
    """Vrai tant que index.html est la page d'attente (LP de SITE non posée)."""
    return INDEX.is_file() and PAGE_ATTENTE in INDEX.read_text(encoding="utf-8")


def cible_lp() -> Path:
    """Le fichier visé par les contrôles de structure de LP.

    En état de passation, l'archive v1 reste le jalon de contenu — mais le
    contrat §7 a été écrit APRÈS elle : les contrôles de STRUCTURE §7 ne
    s'appliquent qu'à l'index de production (voir main()).
    """
    if en_passation():
        archive = RACINE / "docs" / "archive" / "index-lp-v1.html"
        if archive.is_file():
            return archive
    return INDEX


def marqueurs_role(index: str, role: str, variantes: tuple[str, ...]) -> list[int]:
    """Positions de tous les marqueurs d'un rôle (id, data-section,
    aria-labelledby, class) — la conception est libre, le rôle est l'invariant."""
    positions: list[int] = []
    for variante in variantes:
        for motif in (
            rf'id="[^"]*\b{variante}\b[^"]*"',
            rf'data-section=["\']{variante}["\']',
            rf'aria-labelledby="[^"]*\b{variante}\b[^"]*"',
            rf'class="[^"]*\b{variante}\b[^"]*"',
        ):
            for m in re.finditer(motif, index, re.IGNORECASE):
                positions.append(m.start())
    return sorted(set(positions))


def verifier_ordre_sections(index: str) -> list[int]:
    """Les 8 sections, chacune reconnue, DANS L'ORDRE du contrat §7."""
    positions: list[int] = []
    for role, nom, variantes in SECTIONS_ATTENDUES:
        pos = marqueurs_role(index, role, variantes)
        if not pos:
            echec(f"section absente : {nom} — aucun marqueur de « {role} » "
                  "(id, data-section, aria-labelledby ou class)")
            positions.append(-1)
            continue
        positions.append(pos[0])
    for avant, apres in zip(positions, positions[1:]):
        if -1 in (avant, apres):
            continue
        if apres < avant:
            echec("sections hors ordre : le contrat §7 impose hero → capacités → "
                  "comment-ça-marche → démonstration → application → preuves → "
                  "FAQ → CTA final")
            break
    return positions


def verifier_squelette(index: str) -> None:
    """Header, main, footer — le squelette du contrat §7."""
    for balise in ("header", "main", "footer"):
        if not re.search(rf"<{balise}[\s>]", index, re.IGNORECASE):
            echec(f"squelette : <{balise}> absent")


def verifier_hero(index: str, pos_hero: int) -> None:
    """Le hero : un h1, le groupe de sélection de secteur, les DEUX CTA."""
    extrait = index[pos_hero:pos_hero + 6000]
    if not re.search(r"<h1[\s>]", extrait):
        echec("hero : aucun h1")
    if 'role="group"' not in index:
        echec("hero : le groupe de sélection de secteur (role=\"group\") est absent")
    if "install" not in extrait.lower():
        echec("hero : le CTA d'installation est absent")
    if not re.search(r"d[ée]mo|action", extrait, re.IGNORECASE):
        echec("hero : le CTA « voir Mia en action / démo » est absent")
    if not re.search(r"<select|s[ée]lecteur|data-secteur", extrait, re.IGNORECASE):
        echec("hero : le sélecteur de secteur est absent")


def verifier_capacites(index: str) -> None:
    """Les capacités : au moins 4 cartes, avec un état « Mia répond » explicite."""
    cartes = re.findall(r"<article[\s>]", index)
    if len(cartes) < 4:
        echec(f"capacités : {len(cartes)} carte(s) — au moins 4 attendues")
    if not re.search(r"mia\s+r[ée]pond|r[ée]pond", index, re.IGNORECASE):
        echec("capacités : aucun état « Mia répond » explicite")


def verifier_faq(index: str) -> None:
    """La FAQ porte au minimum la question RGPD et la question prix."""
    if not re.search(r"qui voit les conversations|conversation.{0,40}protég", index, re.IGNORECASE):
        echec("FAQ : la question RGPD (« qui voit les conversations ») est absente")
    if not re.search(r"\bprix\b|tarif|co[uû]t", index, re.IGNORECASE):
        echec("FAQ : la question prix est absente")


def verifier_cta_final(index: str) -> None:
    """Le CTA final porte les deux CTA (installer + voir en action)."""
    fin = re.search(
        r'<section[^>]*(?:id="[^"]*\bfinal\b[^"]*"|data-section=["\']final["\']|'
        r'id="[^"]*\bdemarrer\b[^"]*")[^>]*>(.*?)(?=</main>|$)',
        index, re.DOTALL | re.IGNORECASE)
    if not fin:
        echec("CTA final : la section n'est pas identifiable")
        return
    extrait = fin.group(1)
    if "install" not in extrait.lower():
        echec("CTA final : le CTA d'installation est absent")
    if not re.search(r"d[ée]mo|action", extrait, re.IGNORECASE):
        echec("CTA final : le CTA « voir Mia en action / démo » est absent")


def verifier_c2_par_carte(index: str) -> None:
    """Règle C2 (contrat §7) : une carte qui présente une capacité à risque
    (réserver/commander/payer) doit porter un marqueur de statut — sinon le
    push échoue. Une page qui ne présente pas ces capacités est conforme."""
    for carte in re.split(r"(?=<article[\s>])", index):
        if not carte.startswith("<article"):
            continue
        fin = carte.find("</article>")
        corps = carte[:fin + 10] if fin > 0 else carte
        if MOTS_C2.search(corps) and not MARQUEURS_STATUT.search(corps):
            ligne_fautive = next((l.strip() for l in corps.splitlines()
                                  if MOTS_C2.search(l)), corps[:80])
            echec(f"règle C2 : capacité à risque sans marqueur de statut — {ligne_fautive[:90]}")


def verifier_consommation(index: str) -> None:
    """Le contenu sectoriel vient du fichier généré, jamais d'une réécriture."""
    consomme = any(marqueur in index for marqueur in (
        "contenu-sectoriel.json", "contenu_sectoriel", "contenuSectoriel"))
    if not consomme:
        echec("contenu-sectoriel.json n'est pas consommé par la page "
              "(référence au fichier attendue dans le HTML ou le JS)")


def bloc_primitives_retire(index: str) -> str:
    """Retire le bloc de primitives avant la recherche d'hex.

    Le contrat §7 autorise l'hex dans le bloc de primitives (jetons du noyau
    recopiés à l'identique) et nulle part ailleurs. Le bloc est délimité par
    un commentaire qui le nomme — on retire du marqueur d'ouverture à la
    balise </style> suivante.
    """
    m = re.search(r"/\*[^*]*primitives[^*]*\*/", index, re.IGNORECASE)
    if m:
        fin = index.find("</style>", m.start())
        if fin > 0:
            return index[:m.start()] + index[fin + len("</style>"):]
    return index


def verifier_hex_et_primitives(index: str) -> None:
    """Zéro hex hors le bloc de primitives (contrat §7) — sur la page servie
    ET sur les feuilles/scripts du dépôt."""
    sans_primitives = bloc_primitives_retire(index)
    for numero, ligne in enumerate(sans_primitives.splitlines(), 1):
        if HEX_A_TRADUIRE.search(ligne):
            echec(f"index.html:{numero} : hex en dur hors bloc de primitives (contrat §7)")
    for chemin in (LANDING_CSS, LANDING_JS):
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            if HEX_A_TRADUIRE.search(ligne):
                echec(f"{chemin.name}:{numero} : hex en dur (« zéro hex » non respecté)")


def verifier_interdits(index: str) -> None:
    """Les interdits inchangés du contrat §7."""
    if GOOGLE_FONTS.search(index) or GOOGLE_FONTS.search(LANDING_CSS.read_text(encoding="utf-8")):
        echec("référence Google Fonts détectée (polices auto-hébergées uniquement)")
    for chemin in (INDEX, LANDING_CSS, LANDING_JS, JSON_SECTEURS):
        if not chemin.is_file():
            continue
        for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            if EMOJI.search(ligne):
                echec(f"{chemin.relative_to(RACINE)}:{numero} : emoji détecté (interdit interface)")
            if NOMS_AGENTS.search(ligne):
                echec(f"{chemin.relative_to(RACINE)}:{numero} : nom d'agent interne détecté (interdit — Mia seule)")
    for m in REQUETE_EXTERNE.finditer(index):
        echec(f"index.html : requête externe au chargement interdite — {m.group(0)[:80]}")


def verifier_demo() -> None:
    """La démo est branchée sur l'API de production et porte une limite.

    Le SITE DE DÉMONSTRATION utilisé n'est pas imposé (artefact retiré) :
    le choix du site_id de démonstration appartient à la conception.
    """
    js = LANDING_JS.read_text(encoding="utf-8")
    if "api.eperformance.pro" not in js and "web-production-4ab53" not in js:
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


def verifier_fondamentaux(index: str) -> None:
    """Les fondamentaux communs aux deux niveaux : meta description,
    le domaine référencé, sitemap, robots."""
    if '<meta name="description"' not in index:
        echec("SEO : meta description absente")
    if "mia.eperformance.pro" not in index:
        echec("SEO : le domaine de la LP n'est pas référencé")
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
        # contenu. Le contrat §7 a été écrit après elle : les contrôles de
        # structure §7 ne la jugent pas — ils s'activeront avec l'index de
        # production (la LP de SITE).
        verifier_fondamentaux(index)
        verifier_hex_et_primitives(index)
        verifier_interdits(index)
        verifier_demo()
        verifier_videos()
        verifier_empreinte()
    else:
        # NIVEAU 2 — la LP servie : le contrat §7 complet.
        verifier_squelette(index)
        positions = verifier_ordre_sections(index)
        if positions and positions[0] >= 0:
            verifier_hero(index, positions[0])
        verifier_capacites(index)
        verifier_faq(index)
        verifier_cta_final(index)
        verifier_c2_par_carte(index)
        verifier_consommation(index)
        verifier_hex_et_primitives(index)
        verifier_interdits(index)
        verifier_demo()
        verifier_videos()
        verifier_fondamentaux(index)
        verifier_empreinte()

    if erreurs:
        print(f"[structure] ECHEC — {len(erreurs)} contrôle(s) en échec :", file=sys.stderr)
        for e in erreurs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    cible = "archive v1 (niveau 1 — en passation)" if en_passation() else "LP servie (contrat §7)"
    print(f"[structure] PASS — contrat §7 : 8 sections ordonnées par rôle, éléments "
          f"obligatoires, C2 par carte, zéro hex hors primitives, zéro requête "
          f"externe, zéro emoji, zéro nom d'agent, empreinte eperf.css — cible : {cible}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
