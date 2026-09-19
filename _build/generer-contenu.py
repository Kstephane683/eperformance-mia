#!/usr/bin/env python3
"""Générateur du contenu sectoriel de la landing Mia.

RÈGLE FONDATRICE — « une seule source, des références » :
le contenu sectoriel affiché par la landing (intention, thèmes FAQ, nom de
métier) n'est écrit nulle part à la main. Il est importé du noyau
`agent-ia-web/eperf_core/sectors.py` — la même donnée que consomment le
générateur de sites et l'application Mia. Ce script :

  1. importe réellement `SECTEURS` (les 14 secteurs du noyau) ;
  2. en garde les 12 secteurs clients (exclut `blog` et `email` — une Mia
     pour « le secteur e-mail » n'a pas de sens produit, décision de l'audit
     C1 du 19/09) ;
  3. produit `contenu-sectoriel.json` (avec sa date de génération) ;
  4. pré-rend le contenu entre les marqueurs de `index.html` (entre
     `<!-- GEN:...:DEBUT -->` et `<!-- GEN:...:FIN -->`) pour que la page
     reste indexable SANS JavaScript — le pattern établi du projet.

Ce que ce script ajoute à la donnée du noyau (et uniquement ça) :
  - les TITRES DE HERO et leurs accroches — du texte commercial formulé
    selon la règle C2 (« Mia répond », jamais « Mia exécute ») ;
  - la reformulation de l'intention pour la section 2 ;
  - les questions de démonstration, dérivées des `faq_themes` réels par la
    table `QUESTIONS_PAR_THEME` (repli générique pour tout thème non mappé) ;
  - la liste « Mia exécute » (roadmap intégrations, du PLAN-COMPLET §2) —
    toujours affichée avec le badge « Bientôt », jamais comme une capacité
    active (règle C2, bloquante).

Usage :
    python3 _build/generer-contenu.py
    EPERF_CORE=/autre/chemin/agent-ia-web python3 _build/generer-contenu.py

Le chemin du noyau est résolu, dans l'ordre : variable d'environnement
`EPERF_CORE`, puis `../agent-ia-web` relatif à ce dépôt (arborescence de
travail habituelle sous `/home/ballo/OX6A/`).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Chemins — le dépôt, et le noyau `agent-ia-web`
# ---------------------------------------------------------------------------

RACINE_DEPOT = Path(__file__).resolve().parent.parent
RACINE_NOYAU = Path(
    __import__("os").environ.get("EPERF_CORE", RACINE_DEPOT.parent / "agent-ia-web")
)

sys.path.insert(0, str(RACINE_NOYAU))
from eperf_core.sectors import SECTEURS  # noqa: E402 — import réel du noyau

# Les 14 secteurs du noyau moins les deux hors périmètre (audit C1) :
# `blog` est un site éditorial, `email` une bibliothèque de gabarits — aucun
# des deux n'est un métier de site client.
EXCLUS = {"blog", "email"}
ORDRE = [
    "restauration", "hotellerie", "ecommerce", "immobilier", "mlm", "beaute",
    "sante", "education", "evenementiel", "tourisme", "artisan", "vitrine",
]

# ---------------------------------------------------------------------------
# Textes formulés pour la landing — la SEULE extension de la donnée du noyau
# ---------------------------------------------------------------------------

# Titre de hero par métier. Formulation C2 : « répond », jamais « exécute ».
# (Le premier jet pour la restauration — « qui prend les demandes de
# réservation » — a été corrigé : Mia ne PREND pas une réservation, elle
# RÉPOND et transmet la demande.)
HERO_TITRES = {
    "vitrine": "Votre site mérite une assistante qui répond à vos visiteurs, jour et nuit",
    "beaute": "Votre salon mérite une assistante qui répond à vos clientes, même après la fermeture",
    "restauration": "Votre site mérite une assistante qui répond à vos clients jour et nuit",
    "hotellerie": "Votre hôtel mérite une assistante qui répond à vos voyageurs à toute heure",
    "sante": "Votre cabinet mérite une assistante qui répond aux inquiétudes de vos patients",
    "education": "Votre établissement mérite une assistante qui répond aux futurs étudiants",
    "immobilier": "Votre agence mérite une assistante qui répond à chaque prospect dès sa première question",
    "evenementiel": "Votre événement mérite une assistante qui répond à vos visiteurs en continu",
    "ecommerce": "Votre boutique mérite une assistante qui répond à vos clients pendant qu'ils achètent",
    "mlm": "Votre réseau mérite une assistante qui répond aux candidats jour et nuit",
    "tourisme": "Votre agence mérite une assistante qui répond aux voyageurs avant le départ",
    "artisan": "Votre entreprise mérite une assistante qui répond aux demandes de devis pendant vos chantiers",
}

HERO_ACCROCHES = {
    "vitrine": "Mia répond aux questions sur vos prestations, vos délais et votre zone d'intervention, avec les informations de VOTRE site — puis vous transmet chaque demande.",
    "beaute": "Mia présente vos soins, vos produits utilisés et vos conditions d'annulation, puis vous transmet chaque demande de rendez-vous.",
    "restauration": "Mia présente votre carte, vos horaires et vos options pour allergies et régimes, puis vous transmet chaque demande de réservation.",
    "hotellerie": "Mia présente vos chambres, vos conditions d'arrivée et d'annulation, puis vous transmet chaque demande de réservation.",
    "sante": "Mia répond aux questions pratiques — remboursement, mutuelle, urgences — et vous transmet chaque demande de rendez-vous.",
    "education": "Mia présente vos programmes, vos frais et votre calendrier, puis vous transmet chaque dossier de candidature.",
    "immobilier": "Mia présente vos biens, la visite et le financement, puis qualifie le prospect : budget, localisation, type de bien.",
    "evenementiel": "Mia présente le programme, la billetterie et l'accès, puis vous transmet chaque demande de devis.",
    "ecommerce": "Mia répond sur les produits, la livraison, les retours et le paiement — et capture le contact d'un panier abandonné.",
    "mlm": "Mia explique comment démarrer, l'investissement et le plan de rémunération en langage simple, puis qualifie chaque candidat.",
    "tourisme": "Mia présente vos séjours, les formalités et les devis, puis vous transmet chaque demande de réservation.",
    "artisan": "Mia présente vos prestations, vos matériaux et vos délais, puis vous transmet chaque demande de devis.",
}

# Reformulation de l'intention du noyau, en tête de section 2. L'intention
# décrit le MÉTIER (pourquoi un visiteur arrive) ; la reformulation en tire ce
# que Mia apporte. La donnée brute reste disponible dans le JSON.
INTENTIONS_REFORMULEES = {
    "vitrine": "Sur un site de services, le visiteur veut une preuve avant un contact : le travail est-il réel, sous quels délais, dans quelle zone. Mia tient ce rôle — elle répond avec les informations de votre site, à toute heure, et amène chaque visiteur au contact.",
    "beaute": "Une cliente choisit un geste et une praticienne : quels soins, quels produits, quel délai pour un rendez-vous. Mia répond à tout cela depuis votre site — et laisse le rendez-vous à prendre avec vous.",
    "restauration": "Un client affamé veut une réponse immédiate : la carte, les horaires, une table. Mia tient ce rôle jour et nuit — elle répond, et vous transmet la demande de réservation.",
    "hotellerie": "Un voyageur réserve quand son doute est levé : la chambre, le tarif, l'arrivée, l'annulation. Mia répond à chacune de ces questions avec les informations de votre établissement.",
    "sante": "Une inquiétude doit se transformer en rendez-vous, pas rester sans réponse. Mia répond aux questions pratiques et vous transmet chaque demande de rendez-vous.",
    "education": "Un futur étudiant compare des programmes avant de candidater. Mia présente les vôtres — niveau, durée, frais — et vous transmet chaque dossier.",
    "immobilier": "Un prospect veut voir avant de visiter : le bien, le prix, le financement. Mia présente vos biens et qualifie le prospect pendant que vos agents travaillent.",
    "evenementiel": "Un visiteur décide vite : le programme, la billetterie, l'accès. Mia répond en continu et vous transmet chaque demande de devis.",
    "ecommerce": "Un client qui hésite sur la livraison, la taille ou le retour repart sans acheter. Mia répond au moment précis de l'hésitation — et capture le contact d'un panier abandonné.",
    "mlm": "Un candidat se décide quand le démarrage, l'investissement et la rémunération sont clairs. Mia explique les trois en langage simple, 24 h sur 24.",
    "tourisme": "Un voyageur part quand les formalités et le devis sont clairs. Mia présente vos séjours et vous transmet chaque demande de réservation.",
    "artisan": "Un client compare des devis pendant que vous êtes sur le chantier. Mia répond sur vos prestations, vos matériaux et vos délais — et vous transmet la demande.",
}

# « Mia exécute » — la roadmap d'intégrations du PLAN-COMPLET §2. TOUJOURS
# affichée avec le badge « Bientôt » : aucune de ces capacités n'est branchée
# aujourd'hui (règle C2, bloquante). Ne jamais déplacer une ligne de cette
# table vers « Mia répond » sans le support correspondant côté backend.
EXECUTE_ROADMAP = {
    "vitrine": ["Prise de consultation avec agenda", "Devis et facturation automatisés"],
    "beaute": ["Rendez-vous réels avec agenda", "Rappels automatiques"],
    "restauration": ["Réservation réelle avec agenda", "Commande en ligne", "Liste d'attente"],
    "hotellerie": ["Réservation réelle", "Check-in digital", "Room service", "Upselling"],
    "sante": ["Rendez-vous réels", "Préparation avant consultation"],
    "education": ["Admission réelle en ligne", "Support étudiant automatisé"],
    "immobilier": ["Agenda d'agent pour les visites", "Fiches envoyées automatiquement", "CRM"],
    "evenementiel": ["Billetterie réelle", "Gestion des prestataires"],
    "ecommerce": ["Lecture des commandes du site", "Récupération des paniers abandonnés", "Recommandations produits"],
    "mlm": ["Suivi d'activité du réseau", "Formations recommandées"],
    "tourisme": ["Réservation réelle", "Documents de voyage"],
    "artisan": ["Devis réels", "Planning de chantier"],
}

# La capacité de transmission déjà branchée, propre à chaque métier (colonne
# « Mia répond » du PLAN-COMPLET §2, complément aux thèmes FAQ du noyau).
TRANSMISSION_BRANCHÉE = {
    "vitrine": "Demande de devis transmise (prise de contact)",
    "beaute": "Prise de rendez-vous transmise (contact)",
    "restauration": "Demande de réservation transmise (prise de contact)",
    "hotellerie": "Demande de réservation transmise (prise de contact)",
    "sante": "Tri et orientation des demandes, rappels",
    "education": "Dossier de candidature transmis",
    "immobilier": "Qualification du prospect (budget, localisation, type)",
    "evenementiel": "Demande de devis transmise (contact)",
    "ecommerce": "Capture de contact sur panier abandonné",
    "mlm": "Qualification et recrutement 24 h sur 24",
    "tourisme": "Devis et demande de réservation transmis (contact)",
    "artisan": "Demande de devis transmise",
}

# Les deux capacités transverses, branchées, affichées pour tous les secteurs.
REPOND_COMMUN = [
    "Réponse avec les informations de VOTRE site, 24 h sur 24",
    "Escalade vers un humain quand la question dépasse sa connaissance du site",
]

# Questions de démonstration, dérivées des thèmes FAQ réels. Tout thème absent
# de cette table retombe sur le gabarit générique « J'ai une question sur … ».
QUESTIONS_PAR_THEME = {
    "accès et stationnement": "Où êtes-vous situé et où se garer ?",
    "allergies et régimes": "Avez-vous des options pour les allergies et les régimes particuliers ?",
    "annulation": "Quelle est votre politique d'annulation ?",
    "annulation et report": "Puis-je annuler ou reporter mon rendez-vous ?",
    "arrivée et départ": "À quelles heures se font l'arrivée et le départ ?",
    "assurance": "Travaillez-vous avec les assurances ?",
    "billetterie et places": "Comment obtenir des billets et où en trouver ?",
    "calendrier et rythme": "Quel est le calendrier et le rythme des cours ?",
    "compte client": "Comment créer et gérer mon compte client ?",
    "devis": "Comment obtenir un devis ?",
    "devis et réservation": "Comment obtenir un devis et réserver ?",
    "diplômes et accréditations": "Vos diplômes sont-ils reconnus et accrédités ?",
    "délais": "Quels sont vos délais d'intervention ?",
    "délais et planning": "Quels sont les délais et le planning de chantier ?",
    "démarrage et investissement": "Comment démarrer et quel est l'investissement de départ ?",
    "déroulement d'une prestation": "Comment se déroule une prestation, concrètement ?",
    "estimation": "Comment faire estimer mon bien ?",
    "financement": "Comment se passe le financement d'un achat ?",
    "formalités et visa": "Quelles sont les formalités et les visas nécessaires ?",
    "frais de scolarité": "Quels sont les frais de scolarité ?",
    "frais et notaire": "Quels sont les frais de notaire et les frais annexes ?",
    "groupes et événements privés": "Acceptez-vous les groupes et les événements privés ?",
    "horaires": "Quels sont vos horaires ?",
    "inscription et dossier": "Comment s'inscrire et constituer son dossier ?",
    "lieu et accès": "Où se déroule l'événement et comment y accéder ?",
    "livraison": "Quels sont vos délais et zones de livraison ?",
    "matériaux et finitions": "Quels matériaux et finitions proposez-vous ?",
    "paiement": "Quels moyens de paiement acceptez-vous ?",
    "parrainage et parrain": "Comment fonctionne le parrainage ?",
    "plan de rémunération": "Comment fonctionne le plan de rémunération ?",
    "prestataires et traiteurs": "Comment devenir prestataire ou traiteur de l'événement ?",
    "prise de rendez-vous": "Comment prendre rendez-vous ?",
    "produits": "Quels produits proposez-vous ?",
    "produits utilisés": "Quels produits utilisez-vous ?",
    "remboursement et mutuelle": "Vos prestations sont-elles prises en charge par la mutuelle ?",
    "retours et remboursements": "Comment fonctionnent les retours et les remboursements ?",
    "réservation": "Comment réserver une table ?",
    "réservation et annulation": "Comment réserver et jusqu'à quand annuler ?",
    "soins": "Quels soins proposez-vous ?",
    "taille des groupes": "Gérez-vous les groupes et à partir de combien de personnes ?",
    "urgences": "Comment gérer une urgence ?",
    "visite": "Comment organiser une visite ?",
    "zone d'intervention": "Quelle est votre zone d'intervention ?",
    "équipements": "Quels équipements sont disponibles ?",
}


def question_pour_theme(theme: str) -> str:
    """Question de démo dérivée d'un thème FAQ ; gabarit générique en repli."""
    if theme in QUESTIONS_PAR_THEME:
        return QUESTIONS_PAR_THEME[theme]
    return f"J'ai une question sur : {theme}."


# ---------------------------------------------------------------------------
# Construction des données
# ---------------------------------------------------------------------------


def construire_donnees() -> dict:
    """Assemble le JSON final — la donnée du noyau, étiquetée et horodatée."""
    secteurs: dict[str, dict] = {}
    themes_non_mappees: list[str] = []

    for slug in ORDRE:
        secteur = SECTEURS[slug]

        questions = []
        for theme in list(secteur.faq_themes)[:3]:
            questions.append(question_pour_theme(theme))
            if theme not in QUESTIONS_PAR_THEME:
                themes_non_mappees.append(f"{slug}: {theme}")

        secteurs[slug] = {
            "nom": secteur.nom,
            "intention": secteur.intention.strip(),
            "intention_reformulee": INTENTIONS_REFORMULEES[slug],
            "faq_themes": list(secteur.faq_themes),
            "repond": (
                [TRANSMISSION_BRANCHÉE[slug]] + REPOND_COMMUN
            ),
            "execute": EXECUTE_ROADMAP[slug],
            "hero": {
                "titre": HERO_TITRES[slug],
                "accroche": HERO_ACCROCHES[slug],
            },
            "questions_demo": questions,
        }

    if themes_non_mappees:
        print("[contenu] thèmes sans question mappée (gabarit générique employé) :")
        for t in themes_non_mappees:
            print(f"    - {t}")

    return {
        "_genere_le": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "_source": "agent-ia-web/eperf_core/sectors.py — SECTEURS (12 secteurs clients, hors blog/email)",
        "_regle": "Mia répond (vérifiable) / Mia exécute (roadmap, badge Bientôt) — règle C2",
        "secteurs": secteurs,
        "ordre": ORDRE,
    }


# ---------------------------------------------------------------------------
# Pré-rendu HTML — pour que la page reste indexable sans JavaScript
# ---------------------------------------------------------------------------

ACCENTS_A_ECHAPPER = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}


def echapper(texte: str) -> str:
    for vieux, neuf in ACCENTS_A_ECHAPPER.items():
        texte = texte.replace(vieux, neuf)
    return texte


def rendre_hero(donnees: dict) -> str:
    """Titre et accroche du hero — le secteur par défaut (restauration)."""
    s = donnees["secteurs"]["restauration"]
    return (
        f'\n        <h1 id="titre-hero">{echapper(s["hero"]["titre"])}</h1>\n'
        f'        <p class="accroche-hero">{echapper(s["hero"]["accroche"])}</p>\n        '
    )


def rendre_select(donnees: dict) -> str:
    options = "\n".join(
        f'            <option value="{slug}"{" selected" if slug == "restauration" else ""}>'
        f'{echapper(donnees["secteurs"][slug]["nom"])}</option>'
        for slug in donnees["ordre"]
    )
    return f'\n{options}\n        '


def rendre_panels(donnees: dict) -> str:
    blocs = []
    for slug in donnees["ordre"]:
        s = donnees["secteurs"][slug]
        cache = " hidden" if slug != "restauration" else ""
        themes = "\n".join(
            f'          <li>{echapper(t)}</li>' for t in s["faq_themes"]
        )
        repond = "\n".join(
            f'          <li>{echapper(item)}</li>' for item in s["repond"]
        )
        execute = "\n".join(
            f'          <li><span class="capacite">{echapper(item)}</span>'
            f'<span class="badge-bientot">Bientôt</span></li>'
            for item in s["execute"]
        )
        blocs.append(
            f'      <article class="panel-secteur" data-panneau="{slug}"{cache}>\n'
            f'        <p class="intention-metier">{echapper(s["intention_reformulee"])}</p>\n'
            f'        <div class="colonnes-capacites">\n'
            f'          <div class="colonne-repond">\n'
            f'            <h3>Mia répond <span class="sous-titre-colonne">aujourd\u2019hui, vérifiable en démo</span></h3>\n'
            f'            <ul class="liste-repond">\n'
            f'{repond}\n'
            f'{themes}\n'
            f'            </ul>\n'
            f'          </div>\n'
            f'          <div class="colonne-execute">\n'
            f'            <h3>Mia exécutera <span class="sous-titre-colonne">après intégration — roadmap</span></h3>\n'
            f'            <ul class="liste-execute">\n'
            f'{execute}\n'
            f'            </ul>\n'
            f'          </div>\n'
            f'        </div>\n'
            f'      </article>'
        )
    return "\n" + "\n".join(blocs) + "\n    "


def rendre_banc(donnees: dict) -> str:
    """La grille des 12 métiers (section Preuves) — chips de données réelles."""
    items = "\n".join(
        f'        <li data-secteur="{slug}">{echapper(donnees["secteurs"][slug]["nom"])}</li>'
        for slug in donnees["ordre"]
    )
    return f"\n{items}\n      "


def rendre_questions_demo(donnees: dict) -> str:
    """Suggestions de la démo, par secteur (attributs data — lisibles sans JS)."""
    blocs = []
    for slug in donnees["ordre"]:
        questions = " ".join(
            echapper(q.replace('"', "&quot;"))
            for q in donnees["secteurs"][slug]["questions_demo"]
        )
        blocs.append(
            f'      <template data-questions="{slug}">{questions}</template>'
        )
    return "\n" + "\n".join(blocs) + "\n    "


def injecter(index: Path, donnees: dict) -> int:
    """Remplace le contenu entre les marqueurs GEN de index.html.

    Retourne le nombre de blocs injectés ; refuse un index sans marqueurs
    (une génération silencieusement sans effet serait pire qu'une erreur).
    """
    texte = index.read_text(encoding="utf-8")
    remplacements = {
        "HERO": rendre_hero(donnees),
        "SELECT": rendre_select(donnees),
        "PANELS": rendre_panels(donnees),
        "BANC": rendre_banc(donnees),
        "QUESTIONS": rendre_questions_demo(donnees),
    }
    total = 0
    for nom, contenu in remplacements.items():
        motif = re.compile(
            r"(<!-- GEN:" + nom + r":DEBUT -->).*?(<!-- GEN:" + nom + r":FIN -->)",
            re.DOTALL,
        )
        if not motif.search(texte):
            raise SystemExit(
                f"[contenu] ECHEC — marqueur GEN:{nom} absent de index.html"
            )
        texte = motif.sub(lambda m: m.group(1) + contenu + m.group(2), texte)
        total += 1
    index.write_text(texte, encoding="utf-8")
    return total


def main() -> int:
    if not (RACINE_NOYAU / "eperf_core" / "sectors.py").is_file():
        raise SystemExit(
            f"[contenu] ECHEC — sectors.py introuvable sous {RACINE_NOYAU}\n"
            "[contenu] Définir EPERF_CORE=/chemin/vers/agent-ia-web"
        )

    donnees = construire_donnees()

    sortie = RACINE_DEPOT / "contenu-sectoriel.json"
    sortie.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    n = len(donnees["secteurs"])
    themes = sum(len(s["faq_themes"]) for s in donnees["secteurs"].values())
    print(f"[contenu] {sortie.relative_to(RACINE_DEPOT)} — {n} secteurs, {themes} thèmes FAQ")

    index = RACINE_DEPOT / "index.html"
    if index.is_file():
        total = injecter(index, donnees)
        print(f"[contenu] index.html — {total} bloc(s) pré-rendu(s) (HERO, SELECT, PANELS, BANC, QUESTIONS)")
    else:
        print("[contenu] index.html absent — JSON seul généré (la page sera pré-rendue à sa création)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
