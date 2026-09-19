# eperformance-mia — la landing de vente de Mia

**mia.eperformance.pro** — la page qui vend Mia, l'assistante conversationnelle
d'ePerformance, métier par métier.

Mia est un produit SaaS **sectoriel** : chaque site client a sa Mia contextuelle
(12 métiers clients), et les propriétaires gèrent leur chatbot depuis
l'application Mia (PWA). Cette landing vend ce que Mia sait faire **aujourd'hui**
et ne promet que ce qui est branché — règle du projet :

> **« Mia répond » ≠ « Mia exécute »** — toute capacité d'exécution (réservation
> réelle, commande, paiement) est affichée avec le badge « Bientôt », jamais
> vendue comme active.

Dépôt public : `github.com/Kstephane683/eperformance-mia` (public : exigence de
GitHub Pages gratuit). Page statique **sans framework** : le contenu vit dans le
balisage, la page reste indexable sans JavaScript.

---

## Pourquoi un dépôt dédié par app (décision à conserver)

1. **Séparation code source / site public** : le code source du widget vit dans
   `toolkit_eperformance/eperformance-widget/`, le site vitrine dans
   `site-eperformance/`. Un site public n'a rien à faire dans un dépôt de code
   applicatif — et inversement.
2. **Un sous-domaine par app, zéro conflit de chemin** : `mia.eperformance.pro`
   aujourd'hui ; quand d'autres apps viendront (portail, diagnostic…), chacune
   aura son dépôt et son sous-domaine — personne ne se marche dessus.
3. **Cycle de déploiement indépendant** : cette landing se déploie quand ELLE
   est prête, sans coupler à la publication du site vitrine ou du widget.
4. **Périmètre de coordination clair** : `mon-site` = l'agent SITE ; le widget =
   le code source ; ce dépôt = la présence publique de l'app Mia.

## Les ressources copiées, et leur canonique (ne jamais éditer ici)

| Ressource | Canonique | Note |
|---|---|---|
| `assets/css/eperf.css` | `site-eperformance/assets/css/eperf.css` (généré par `agent-ia-web/eperf_core`) | copie compilée avec en-tête NOTE ; contrôle `scripts/verifier-empreinte.py` ; empreinte posée dans `assets/css/eperf.css.sha256` |
| `assets/fonts/*.woff2` | `site-eperformance/assets/fonts/` | sous-ensemble latin, auto-hébergé, zéro Google Fonts |
| `assets/img/*` (favicon, logos, og-image) | `site-eperformance/assets/img/` | identité visuelle de la marque |
| `assets/captures/*` | `toolkit_eperformance/eperformance-widget/docs/phase3-tache-6-6/maquettes/` | captures RÉELLES de l'application et de la console, produites par le harnais de l'équipe (phase 3, tâche 6.6) |
| Contenu sectoriel | `agent-ia-web/eperf_core/sectors.py` | **la source** — régénéré, jamais réécrit à la main |

## Le contenu sectoriel — une seule source

`_build/generer-contenu.py` **importe réellement `SECTEURS`** du noyau (les
12 secteurs clients : les 14 du noyau moins `blog` et `email`), et produit :

- `contenu-sectoriel.json` — intention, thèmes FAQ, titres de hero, questions
  de démonstration, roadmap « Mia exécute » par métier (horodaté, committé) ;
- le pré-rendu de `index.html` entre les marqueurs `<!-- GEN:…:DEBUT/FIN -->`
  (hero, options du sélecteur, 12 panneaux de capacités, banc des 12 métiers,
  questions de démo) — pour que la page reste lisible SANS JavaScript.

```bash
# depuis l'arborescence de travail habituelle (../agent-ia-web à côté du dépôt)
python3 _build/generer-contenu.py

# ou, si le noyau vit ailleurs :
EPERF_CORE=/chemin/vers/agent-ia-web python3 _build/generer-contenu.py
```

Après régénération : vérifier le diff de `index.html` et de
`contenu-sectoriel.json`, committer les deux (convention : un sujet par
commit, messages en français).

## Les vidéos — méthode et mesures

`scripts/produire-videos.py` produit les quatre vidéos (décision du
propriétaire : **sans voix générée** — muettes) :

| Vidéo | Méthode | Objectif |
|---|---|---|
| `videos/hero-loop.mp4/.webm` | Playwright enregistre le **widget réel** en action sur `eperformance.pro` (question réelle, réponse réelle de l'API), ffmpeg découpe 18 s | 15-20 s, < 2 Mo |
| `videos/demo-produit.mp4/.webm` | Playwright enregistre **la landing elle-même** (parcours complet, deux vraies questions de démo), ffmpeg + surtitres | 60-90 s |
| `videos/tuto-installation.mp4/.webm` | Playwright enregistre le **widget installé** sur le site de production, ffmpeg + surtitres | 30-45 s |
| `videos/tuto-application.mp4/.webm` | ffmpeg : séquence animée des **captures réelles** de l'application (harnais phase3), Ken Burns léger | 30 s |

Formats : MP4 (H.264) + WebM (VP9), sans piste audio (silencieux assumé).
Durées et poids RÉELS mesurés par ffprobe : `docs/videos-mesures.json`.

```bash
python3 scripts/produire-videos.py          # les quatre
python3 scripts/produire-videos.py hero     # une seule : hero|demo|install|app
```

La vidéo `demo` enregistre `http://localhost:8080/` : servir le dépôt avant
(`python3 -m http.server 8080` — ce port est dans la liste CORS de l'API).

## La démonstration interactive (section 4)

Branchée sur l'API de production
(`web-production-4ab53.up.railway.app/api/chatbot/message`) avec le site de
démonstration `restaurant_chez_amina`. Limite côté client : **5 questions par
visiteur** (session), puis « Démo limitée — installez Mia sur votre site ».
Chaque réponse affiche le **temps réellement mesuré**.

**CORS** : l'API autorise une liste d'origines exacte. Sont autorisées
(vérifiées par preflight au 19/09/2026) : `https://kstephane683.github.io`
(l'URL Pages), `https://eperformance.pro`, `https://www.eperformance.pro`,
`http://localhost:8080`. **`https://mia.eperformance.pro` ne l'est pas encore**
→ la démo affichera un message honnête sur le domaine final tant que l'origine
n'aura pas été ajoutée côté backend (voir docs/RAPPORT-LANDING.md, demande
enregistrée).

## Garde-fous (dépôt public — leçon du 19/09)

- `scripts/verifier-secrets.py` — refuse tout push contenant un secret en clair.
  **Éprouvé** : fait échouer une fois exprès sur un fichier test (jeton factice)
  avant installation ; hook `pre-push` local + workflow GitHub Actions au push.
- `scripts/verifier-empreinte.py` — la copie d'eperf.css est exactement le
  canonique posé (hachage du contenu sous le marqueur de NOTE).
- `scripts/verifier-structure.py` — 8 sections, 12 secteurs, règle C2
  (badge « Bientôt » uniquement sur « Mia exécutera »), zéro hex hors exception
  documentée, zéro Google Fonts, zéro emoji, démo, vidéos, SEO.

```bash
sh .git/hooks/pre-push        # éprouver les trois garde-fous localement
python3 scripts/verifier-structure.py
```

## Redéployer

Le déploiement est **GitHub Pages depuis `main`** (fichier `.nojekyll` présent,
`CNAME` = `mia.eperformance.pro`). Pousser sur `main` suffit :

```bash
git push origin main   # le hook pre-push exécute les garde-fous
```

Vérifier ensuite : `https://kstephane683.github.io/eperformance-mia/`
(toujours disponible) et `https://mia.eperformance.pro/` (si le DNS est posé).

## Actions restantes au propriétaire (K. Stéphane Ballo)

1. **DNS Hostinger** — poser le CNAME qui pointe `mia` vers
   `kstephane683.github.io.` (le fichier CNAME du dépôt ne suffit pas, c'est le
   DNS qui fait foi). GitHub Pages exige aussi que l'enregistrement soit
   validé dans les paramètres Pages du dépôt (déjà configuré côté GitHub).
2. **Enforce HTTPS** — une fois le DNS vérifié et le certificat émis
   (Settings → Pages → Enforce HTTPS). À NE PAS activer avant que le DNS
   réponde, sinon le domaine bascule en boucle d'erreur.
3. **URL de l'application Mia** — l'accès « Vous avez déjà Mia ? Gérez-la »
   (hero) et le bouton « Installer l'application » (section 5) attendent l'URL
   réelle de la PWA. Chercher `TODO propriétaire` dans `index.html` et
   `assets/js/landing.js` : deux remplacements.
4. **CORS backend** — ajouter `https://mia.eperformance.pro` à la variable
   `CORS_ORIGINS` du backend Railway (périmètre backend).

## Identité du produit

- **Mia** — produit d'assistante conversationnelle d'**ePerformance**
  (propriétaire : K. Stéphane Ballo).
- Landing : 8 sections (hero métier, capacités, fonctionnement, démo en direct,
  application mobile, preuves mesurées, FAQ, CTA final), sélecteur de secteur
  structurant, thème clair/sombre, WCAG 2.1 AA, polices auto-hébergées,
  zéro emoji, contenu sectoriel généré — une seule source, des références.
