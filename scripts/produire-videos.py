#!/usr/bin/env python3
"""Production des quatre vidéos de la landing Mia.

Méthode (décision du propriétaire : SANS voix générée — vidéos muettes) :

  hero-loop        15-20 s   Playwright enregistre le widget RÉEL en action sur
                             le site de production (eperformance.pro) : le
                             visiteur ouvre la bulle, pose une question, Mia
                             répond (vraie API). Même scène en boucle.
  demo-produit     60-90 s   Playwright enregistre la LANDING elle-même :
                             parcours S1 → S2 (changement de secteur) → S3 →
                             S4 (deux vraies questions de démo) → S5 → S6 → S8.
  tuto-install     30-45 s   Playwright enregistre le site de production :
                             la bulle Mia, son ouverture, une conversation —
                             avec surtitres expliquant l'installation (le
                             résultat installé, pas une maquette).
  tuto-app         30 s      Séquence de captures animées : les six captures
                             RÉELLES de l'application (harnais phase3,
                             docs/phase3-tache-6-6), composées sur fond flouté
                             avec léger Ken Burns et surtitres.

  puis ffmpeg assemble/convertit en MP4 H.264 + WebM (VP9), sans piste audio
  (silencieux assumé — documenté), avec surtitres si la vidéo en prévoit.

Chaque vidéo est mesurée à la fin (durée réelle, poids réel) et les mesures
sont écrites dans docs/videos-mesures.json.

Usage :
    python3 scripts/produire-videos.py            # les quatre
    python3 scripts/produire-videos.py hero       # une seule : hero|demo|install|app
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
VIDEOS = RACINE / "videos"
CAPTURES = RACINE / "assets" / "captures"
MESURES = RACINE / "docs" / "videos-mesures.json"

SITE_PRODUCTION = "https://eperformance.pro/"
LANDING_LOCALE = "http://localhost:8080/"

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# Surtitre : via textfile (l'option drawtext textfile= évite tout problème
# d'échappement des apostrophes françaises dans la ligne de commande).
_compteur_etiquettes = 0


def surtitre(texte: str, taille: int, marge: int, debut: float, fin: float) -> str:
    global _compteur_etiquettes
    _compteur_etiquettes += 1
    fichier = VIDEOS / f"_etiquette-{_compteur_etiquettes}.txt"
    fichier.write_text(texte, encoding="utf-8")
    return (
        f"drawtext=fontfile={FONT_BOLD}:textfile={fichier}:fontsize={taille}:"
        f"fontcolor=white:borderw=0:shadowx=2:shadowy=2:shadowcolor=black@0.85:"
        f"x=(w-text_w)/2:y=h-{marge}:enable='between(t,{debut},{fin})'"
    )


def nettoyer_etiquettes() -> None:
    for f in VIDEOS.glob("_etiquette-*.txt"):
        f.unlink()


def ffmpeg(args: list[str]) -> None:
    """Exécute ffmpeg et échoue bruyamment (une vidéo silencieusement fausse
    serait pire qu'une production arrêtée)."""
    resultat = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args,
        capture_output=True, text=True,
    )
    if resultat.returncode != 0:
        raise SystemExit(f"[videos] ECHEC ffmpeg : {resultat.stderr[-1500:]}")


def convertir(mp4: Path, crf_x264: str, crf_vp9: str, titre_sur_dialogue: bool = False) -> None:
    """MP4 H.264 + WebM VP9, sans audio, faststart."""
    webm = mp4.with_suffix(".webm")
    ffmpeg(["-i", str(mp4), "-an", "-c:v", "libx264", "-preset", "slow",
            "-crf", crf_x264, "-pix_fmt", "yuv420p", "-r", "30",
            "-movflags", "+faststart", str(mp4.with_suffix(".tmp.mp4"))])
    mp4.with_suffix(".tmp.mp4").replace(mp4)
    ffmpeg(["-i", str(mp4), "-an", "-c:v", "libvpx-vp9", "-crf", crf_vp9,
            "-b:v", "0", "-row-mt", "1", "-pix_fmt", "yuv420p",
            str(webm) + ".tmp.webm"])
    Path(str(webm) + ".tmp.webm").replace(webm)


def mesurer(nom: str, mp4: Path, webm: Path, duree_connue: float, methode: str) -> dict:
    """Durée et poids RÉELS via ffprobe — jamais déclarés."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
         "-of", "json", str(mp4)],
        capture_output=True, text=True, check=True,
    )
    infos = json.loads(probe.stdout)["format"]
    return {
        "nom": nom,
        "methode": methode,
        "duree_s": round(float(infos["duration"]), 1),
        "poids_mp4_mo": round(int(infos["size"]) / 1_000_000, 2),
        "poids_webm_mo": round(webm.stat().st_size / 1_000_000, 2),
        "objectif_duree": duree_connue,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. HERO LOOP — le widget réel sur le site de production
# ─────────────────────────────────────────────────────────────────────────────


def produire_hero() -> dict:
    from playwright.sync_api import sync_playwright

    brut = VIDEOS / "_brut-hero.webm"
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        contexte = navigateur.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(VIDEOS),
            record_video_size={"width": 1280, "height": 720},
        )
        t0 = time.time()                    # l'enregistrement démarre avec la page
        page = contexte.new_page()
        page.goto(SITE_PRODUCTION, wait_until="domcontentloaded")
        time.sleep(4)                                   # la bulle apparaît
        # Le bandeau de consentement du site masque la bulle (décision D9 du
        # widget) : on l'accepte s'il est là, puis on ouvre via l'API publique
        # du SDK — plus robuste qu'un clic sur la bulle.
        try:
            page.click("#consent-banner button:visible", timeout=4000)
            time.sleep(1)
        except Exception:
            pass                                        # pas de bandeau : rien à faire
        page.evaluate("window.ePerformance && window.ePerformance.open()")
        time.sleep(2)
        # Le widget est un iframe même origine. L'accueil « Poser une question »
        # est un BOUTON qui ouvre la conversation avec le champ focalisé.
        cadre = page.frame_locator("#eperformance-widget-frame")
        page.wait_for_timeout(1500)
        try:
            cadre.locator("button.ep-saisie").first.click(timeout=10000)
            time.sleep(1.5)
            champ = cadre.locator("input.ep-input").first
            champ.fill("Quels sont vos horaires d'ouverture ?", timeout=10000)
            champ.press("Enter")
        except Exception:
            # Repli : certains montages exposent le champ dans le document hôte.
            page.keyboard.type("Quels sont vos horaires d'ouverture ?")
            page.keyboard.press("Enter")

        # On attend la RÉPONSE RÉELLE (l'indicateur d'écriture disparaît),
        # puis quelques secondes de lecture — la vidéo ne s'arrête pas sur
        # un minuteur aveugle mais sur l'événement qu'elle doit montrer.
        indicateur = cadre.locator(".ep-typing").first
        try:
            indicateur.wait_for(state="visible", timeout=20000)
        except Exception:
            pass                                        # réponse déjà arrivée
        indicateur.wait_for(state="hidden", timeout=90000)
        t_reponse = time.time() - t0                    # instant de la réponse, depuis le début du film
        time.sleep(6)                                   # la réponse reste lisible

        chemin_video = page.video.path()                # avant la fermeture
        contexte.close()                                # finalise le webm
        navigateur.close()
        Path(chemin_video).rename(brut)

    # Fenêtre de 18 s : 12 s avant la réponse (ouverture, question, écriture)
    # et 6 s de lecture. La fin du film coïncide avec la réponse affichée.
    debut = max(0.0, t_reponse - 12.0)
    ffmpeg(["-ss", f"{debut:.2f}", "-t", "18", "-i", str(brut),
            "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "28",
            "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart",
            str(VIDEOS / "hero-loop.mp4")])
    convertir(VIDEOS / "hero-loop.mp4", "28", "36")

    # Poster : la réponse vient de s'afficher (t≈12 s du clip final).
    ffmpeg(["-ss", "12.5", "-i", str(VIDEOS / "hero-loop.mp4"), "-frames:v", "1",
            "-q:v", "4", str(RACINE / "assets/img/poster-hero.jpg")])

    brut.unlink(missing_ok=True)
    return mesurer("hero-loop", VIDEOS / "hero-loop.mp4", VIDEOS / "hero-loop.webm",
                   "15-20 s", "Playwright — widget réel sur eperformance.pro, question réelle à l'API ; ffmpeg H.264+VP9, muet")


# ─────────────────────────────────────────────────────────────────────────────
# 2. DÉMO PRODUIT — la landing elle-même, avec vraies questions de démo
# ─────────────────────────────────────────────────────────────────────────────

# Plan de la narration : [(instant_s, texte, taille)] — appliqué en une passe
# drawtext. Les instants correspondent au scénario d'enregistrement ci-dessous.
PLAN_SURTITRES_DEMO = [
    (2.0,  "Le sélecteur de secteur adapte toute la page", 34),
    (11.0, "Ce que Mia répond aujourd'hui — et ce qu'elle exécutera plus tard", 30),
    (20.0, "Trois étapes : question, réponse, prise en main", 34),
    (28.0, "Démo en direct — branchée sur l'API de production", 34),
    (52.0, "Chaque réponse est mesurée en direct", 30),
    (62.0, "Gérez Mia depuis votre téléphone", 34),
    (74.0, "Des preuves, pas des promesses", 34),
]


def produire_demo() -> dict:
    from playwright.sync_api import sync_playwright

    brut = VIDEOS / "_brut-demo.webm"
    if not brut.exists():                       # reprise : brut déjà enregistré
        with sync_playwright() as p:
          navigateur = p.chromium.launch()
          contexte = navigateur.new_context(
              viewport={"width": 1280, "height": 720},
              record_video_dir=str(VIDEOS),
              record_video_size={"width": 1280, "height": 720},
          )
          page = contexte.new_page()
          page.goto(LANDING_LOCALE, wait_until="networkidle")
          time.sleep(3)

          def glisser_vers(selecteur: str, duree_s: float) -> None:
              page.eval_on_selector(
                  selecteur,
                  "el => el.scrollIntoView({behavior:'smooth', block:'start'})")
              time.sleep(duree_s)

          glisser_vers("#capacites", 4)
          page.select_option("#select-secteur", "hotellerie")   # la page s'adapte
          time.sleep(3)
          page.select_option("#select-secteur", "restauration")
          time.sleep(2)
          glisser_vers("#fonctionnement", 4)
          time.sleep(3)
          glisser_vers("#demo", 3)
          page.click(".suggestion >> nth=0")                    # vraie question 1
          page.wait_for_selector(".message.mia .metrique-reponse", timeout=90000)
          time.sleep(4)
          page.click(".suggestion >> nth=1")                    # vraie question 2
          page.wait_for_selector(
              ".message.mia .metrique-reponse >> nth=1", timeout=90000)
          time.sleep(4)
          glisser_vers("#application", 4)
          time.sleep(4)
          glisser_vers("#preuves", 4)
          time.sleep(4)
          glisser_vers("#demarrer", 3)
          time.sleep(3)

          chemin_video = page.video.path()
          contexte.close()
          navigateur.close()
          Path(chemin_video).rename(brut)
    # Surtitres : un drawtext par instant.
    filtres = ",".join(
        surtitre(e, t, 36, a, a + 8) for a, e, t in PLAN_SURTITRES_DEMO
    )
    ffmpeg(["-i", str(brut), "-an", "-vf", filtres,
            "-c:v", "libx264", "-preset", "slow", "-crf", "25",
            "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart",
            str(VIDEOS / "demo-produit.mp4")])
    convertir(VIDEOS / "demo-produit.mp4", "25", "34")
    brut.unlink(missing_ok=True)
    return mesurer("demo-produit", VIDEOS / "demo-produit.mp4", VIDEOS / "demo-produit.webm",
                   "60-90 s", "Playwright — enregistrement de la landing (démo réelle, 2 questions à l'API) ; ffmpeg + surtitres Liberation Sans, muet")


# ─────────────────────────────────────────────────────────────────────────────
# 3. TUTORIEL INSTALLATION — le résultat installé, sur le site de production
# ─────────────────────────────────────────────────────────────────────────────

PLAN_SURTITRES_INSTALL = [
    (2.0,  "Mia est installée par ePerformance sur votre site", 30),
    (8.0,  "La bulle Mia apparaît — configurée pour votre métier", 30),
    (14.0, "Elle répond à vos visiteurs, jour et nuit", 30),
    (28.0, "Chaque demande vous est transmise — vous prenez la main", 30),
    (36.0, "Installer Mia : eperformance.pro", 34),
]


def produire_install() -> dict:
    from playwright.sync_api import sync_playwright

    brut = VIDEOS / "_brut-install.webm"
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        contexte = navigateur.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(VIDEOS),
            record_video_size={"width": 1280, "height": 720},
        )
        page = contexte.new_page()
        page.goto(SITE_PRODUCTION, wait_until="domcontentloaded")
        time.sleep(5)                                   # 1 : le site chargé, la bulle apparaît
        try:
            page.click("#consent-banner button:visible", timeout=4000)
            time.sleep(1)
        except Exception:
            pass
        page.evaluate("window.ePerformance && window.ePerformance.open()")
        time.sleep(4)                                   # 2 : le panneau s'ouvre
        cadre = page.frame_locator("#eperformance-widget-frame")
        try:
            cadre.locator("button.ep-saisie").first.click(timeout=10000)
            time.sleep(1.5)
            champ = cadre.locator("input.ep-input").first
            champ.fill("Comment fonctionne le chatbot ?", timeout=10000)
            champ.press("Enter")
        except Exception:
            page.keyboard.type("Comment fonctionne le chatbot ?")
            page.keyboard.press("Enter")

        # La vidéo s'arrête sur la réponse réelle, pas sur un minuteur.
        indicateur = cadre.locator(".ep-typing").first
        try:
            indicateur.wait_for(state="visible", timeout=20000)
        except Exception:
            pass
        indicateur.wait_for(state="hidden", timeout=90000)
        time.sleep(8)                                   # lecture de la réponse

        chemin_video = page.video.path()
        contexte.close()
        navigateur.close()
        Path(chemin_video).rename(brut)

    filtres = ",".join(
        surtitre(e, t, 36, a, a + 8) for a, e, t in PLAN_SURTITRES_INSTALL
    )
    ffmpeg(["-i", str(brut), "-an", "-vf", filtres,
            "-c:v", "libx264", "-preset", "slow", "-crf", "25",
            "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart",
            str(VIDEOS / "tuto-installation.mp4")])
    convertir(VIDEOS / "tuto-installation.mp4", "25", "34")
    brut.unlink(missing_ok=True)
    return mesurer("tuto-installation", VIDEOS / "tuto-installation.mp4", VIDEOS / "tuto-installation.webm",
                   "30-45 s", "Playwright — widget réel installé sur eperformance.pro ; ffmpeg + surtitres, muet")


# ─────────────────────────────────────────────────────────────────────────────
# 4. TUTORIEL APPLICATION — captures réelles animées (repli assumé du plan)
# ─────────────────────────────────────────────────────────────────────────────

SEQUENCE_APP = [
    ("application-accueil-mobile-390x844-clair.png",        "L'accueil : l'état vivant", 5),
    ("application-conversation-mobile-390x844-clair.png",   "Les conversations : tout ce que Mia dit", 5),
    ("console-competences-de-mia-mobile-390x844-clair.png", "Les compétences de votre métier", 5),
    ("application-accueil-mobile-390x844-sombre.png",       "Le thème sombre, comme la landing", 5),
    ("application-conversation-mobile-390x844-sombre.png",  "La prise en main, au bon moment", 5),
    ("console-competences-de-mia-mobile-390x844-sombre.png","Tout se règle depuis votre téléphone", 5),
]


def produire_app() -> dict:
    """Compositing ffmpeg : capture centrée sur fond flouté, léger Ken Burns,
    surtitre. Les captures sont RÉELLES (harnais phase3 de l'équipe)."""
    segments = []
    for i, (fichier, legende, duree) in enumerate(SEQUENCE_APP):
        source = CAPTURES / fichier
        sortie = VIDEOS / f"_seg-app-{i}.mp4"
        filtres = (
            "[0:v]scale=1280:720:force_original_aspect_ratio=increase,"
            "crop=1280:720,boxblur=28:2,eq=brightness=-0.06[bg];"
            "[0:v]scale=-2:640[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
            + surtitre(legende, 30, 30, 0.2, duree)
            + ",zoompan=z='min(zoom+0.0005,1.05)':d="
              f"{duree * 30}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720[v]"
        )
        ffmpeg(["-loop", "1", "-i", str(source), "-filter_complex", filtres,
                "-map", "[v]", "-an", "-t", str(duree),
                "-c:v", "libx264", "-preset", "medium", "-crf", "24",
                "-pix_fmt", "yuv420p", str(sortie)])
        segments.append(sortie)

    liste = VIDEOS / "_liste-app.txt"
    liste.write_text(
        "".join(f"file '{s.name}'\n" for s in segments), encoding="utf-8")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(liste),
            "-c", "copy", str(VIDEOS / "tuto-application.mp4")])
    convertir(VIDEOS / "tuto-application.mp4", "26", "35")
    for s in segments:
        s.unlink()
    liste.unlink()
    return mesurer("tuto-application", VIDEOS / "tuto-application.mp4", VIDEOS / "tuto-application.webm",
                   "30 s", "ffmpeg — séquence animée des captures réelles de l'application (harnais phase3), Ken Burns léger, muet")


# ─────────────────────────────────────────────────────────────────────────────

PRODUCTIONS = {
    "hero": produire_hero,
    "demo": produire_demo,
    "install": produire_install,
    "app": produire_app,
}


def main() -> int:
    cibles = sys.argv[1:] or list(PRODUCTIONS)
    VIDEOS.mkdir(exist_ok=True)

    mesures: dict = {"_note": "Durées et poids RÉELS mesurés par ffprobe au moment de la production.",
                     "videos": {}}
    if MESURES.exists():
        mesures = json.loads(MESURES.read_text(encoding="utf-8"))

    for cible in cibles:
        if cible not in PRODUCTIONS:
            raise SystemExit(f"[videos] cible inconnue : {cible} (hero|demo|install|app)")
        print(f"[videos] production de {cible}…")
        mesures["videos"][cible] = PRODUCTIONS[cible]()
        print(f"[videos] {cible} : {mesures['videos'][cible]['duree_s']} s, "
              f"{mesures['videos'][cible]['poids_mp4_mo']} Mo (MP4)")

    MESURES.write_text(json.dumps(mesures, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(f"[videos] mesures écrites : {MESURES.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
