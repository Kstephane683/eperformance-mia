#!/usr/bin/env python3
"""Vérifie que la copie d'eperf.css n'a pas divergé du canonique.

La landing embarque une COPIE de `site-eperformance/assets/css/eperf.css`
(le canonique de déploiement, généré par `agent-ia-web/eperf_core`). Une copie
qui dérive silencieusement est le défaut exact que ce contrôle empêche —
pattern établi pour le blog (guide-deploiement-github.md) : comparer les
empreintes après TOUTE modification du canonique.

Mécanique : la copie sert le canonique PRÉCÉDÉ d'un bloc NOTE (de copie,
« ne jamais éditer »). Le bloc NOTE se termine par un marqueur unique —
`— FIN DE LA NOTE eperformance-mia` — et tout ce qui suit est censé être
LES OCTETS EXACTS du canonique. Le fichier `assets/css/eperf.css.sha256`
pose l'empreinte sha256 du canonique au moment de la copie. Le contrôle
recalcule l'empreinte de la copie APRÈS le marqueur et la compare :
  - identique : la copie servie est exactement le canonique posé ;
  - différent : la copie a été éditée ou le canonique a évolué — recopier
    le canonique, mettre à jour l'empreinte, committer (ne JAMAIS éditer
    la copie directement).

Usage :
    python3 scripts/verifier-empreinte.py
        vérifie copie-vs-empreinte posée (fonctionne partout, CI incluse)
    python3 scripts/verifier-empreinte.py --source /chemin/site-eperformance
        vérifie EN PLUS contre la source canonique si elle est accessible
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
COPIE = RACINE / "assets" / "css" / "eperf.css"
EMPREINTE = RACINE / "assets" / "css" / "eperf.css.sha256"
MARQUEUR = "— FIN DE LA NOTE eperformance-mia : tout ce qui suit EST le canonique —"


def sha256_octets(donnees: bytes) -> str:
    return hashlib.sha256(donnees).hexdigest()


def canonique_sous_la_note(copie: Path) -> bytes:
    """Les octets de la copie situés APRÈS le marqueur de fin de NOTE."""
    brut = copie.read_bytes()
    texte = brut.decode("utf-8")
    position = texte.find(MARQUEUR)
    if position < 0:
        raise ValueError("marqueur de fin de NOTE introuvable dans la copie")
    fin_note = texte.index("*/", position) + 2
    # Après le marqueur : une ligne vide sépare la NOTE du canonique.
    return texte[fin_note:].lstrip("\n").encode("utf-8")


def main() -> int:
    if not COPIE.is_file() or not EMPREINTE.is_file():
        print("[empreinte] ECHEC — copie ou empreinte manquante", file=sys.stderr)
        return 1

    attendue = EMPREINTE.read_text(encoding="utf-8").strip()
    echec = False
    try:
        constatee = sha256_octets(canonique_sous_la_note(COPIE))
    except ValueError as erreur:
        print(f"[empreinte] ECHEC — {erreur}", file=sys.stderr)
        return 1

    if constatee != attendue:
        print(
            f"[empreinte] ECHEC — le contenu sous la NOTE a divergé du canonique posé\n"
            f"[empreinte]   attendue (posée à la copie) : {attendue}\n"
            f"[empreinte]   constatée                   : {constatee}\n"
            f"[empreinte] Soit la copie a été éditée (interdit), soit le canonique a "
            f"évolué : recopier site-eperformance/assets/css/eperf.css puis "
            f"mettre à jour assets/css/eperf.css.sha256.",
            file=sys.stderr,
        )
        echec = True
    else:
        print(f"[empreinte] PASS — copie conforme au canonique posé ({attendue[:12]}…)")

    # Comparaison directe à la source canonique, si elle est accessible.
    if len(sys.argv) > 2 and sys.argv[1] == "--source":
        source = Path(sys.argv[2]) / "assets" / "css" / "eperf.css"
        if source.is_file():
            empreinte_source = sha256_octets(source.read_bytes())
            if empreinte_source != attendue:
                print(
                    f"[empreinte] AVIS — le canonique a évolué ({empreinte_source[:12]}…)\n"
                    f"[empreinte] Resynchroniser : recopier {source} puis régénérer .sha256.",
                    file=sys.stderr,
                )
                echec = True
            else:
                print("[empreinte] PASS — copie identique au canonique site-eperformance")
        else:
            print(f"[empreinte] AVIS — source canonique introuvable : {source}")

    return 1 if echec else 0


if __name__ == "__main__":
    sys.exit(main())
