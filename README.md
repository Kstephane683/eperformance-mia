# eperformance-mia — dépôt de la landing Mia (mia.eperformance.pro)

**Statut : PASSATION À L'AGENT SITE** (décision du propriétaire, 19/09).
L'agent SITE conçoit la landing **et** l'app Mia. Ce dépôt lui est remis avec
les dépendances prêtes — **la LP v1 construite par CHATBOT a été retirée de
`main`** (archivée dans `docs/archive/index-lp-v1.html` et sur la branche
`archive/lp-v1-chatbot`) : c'est une **référence de contenu**, pas un modèle
de conception.

## Ce qui est déjà en place (dépendances livrées)

| Élément | État |
|---|---|
| Dépôt GitHub + GitHub Pages | ✅ actif, sert `https://mia.eperformance.pro/` |
| Custom domain `mia.eperformance.pro` | ✅ configuré côté GitHub, HTTPS **enforced** |
| DNS Hostinger (CNAME) | ✅ posé par le propriétaire |
| Garde-fou secrets | ✅ `scripts/_verifier-secrets.py` — hook pre-push **ET** workflow Actions (le dépôt est public : la leçon du 19/09) |
| Empreinte eperf.css | ✅ `scripts/verifier-empreinte.py` — la copie de déploiement `assets/css/eperf.css` doit rester identique à la canonique (`agent-ia-web/eperf_core`, canonique de déploiement `site-eperformance`) — **ne jamais l'éditer, la resynchroniser** |
| Contenu sectoriel | ✅ `contenu-sectoriel.json` — **généré** par `_build/generer-contenu.py` **depuis `agent-ia-web/eperf_core/sectors.py`** (import réel) : 12 secteurs clients, intention + `faq_themes` réels. **Ne jamais réécrire à la main** : relancer le script |
| 4 vidéos muettes | ✅ `videos/` — hero-loop, démo produit, tuto installation, tuto app (Playwright + ffmpeg, MP4 H.264 + WebM, durées et poids mesurés dans `docs/`) |
| Règle C2 (bloquante) | **« Mia répond » ≠ « Mia exécute »** — ne jamais vendre ce qui n'est pas branché. La LP v1 archivée montre l'application de la règle, pas son design |

## Ce que l'agent SITE conçoit

La landing (8 sections : hero + sélecteur de secteur structurant, capacités
par métier, comment ça marche, démo interactive, gestion mobile, preuves
**sans invention**, FAQ dont le RGPD, CTA final) et l'app Mia (14 écrans) —
consigne complète chez CHATBOT : `unified-ia-backend/docs/refonte-app-mia/CONSIGNE-SITE.md`
(+ AUDIT-PREALABLE.md et PLAN-COMPLET.md pour le produit).

**Référence structurale (optionnelle)** : les captures de l'app Jèko dans
`toolkit_eperformance/eperformance-widget/docs/refonte-app-mia/references-visuelles/`
— structure et navigation reprises possibles, design system et couleurs **non**
(`eperf.css` canonique).

## Régénérer / redéployer

```bash
python3 _build/generer-contenu.py     # contenu sectoriel depuis le noyau
git push                              # Pages redéploie depuis main
bash scripts/verifier-empreinte.py    # contrôle eperf.css
bash scripts/verifier-structure.py    # contrôles structurels (8 sections, 12 secteurs, C2…)
```
