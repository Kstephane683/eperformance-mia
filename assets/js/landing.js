/* ==========================================================================
   Landing Mia — interactions
   assets/js/landing.js

   Trois responsabilités, et rien d'autre :
     1. le thème clair/sombre (pattern canonique eperf — data-theme + localStorage) ;
     2. le sélecteur de secteur, qui adapte le hero, les capacités affichées
        et les questions de la démo — contenu lu depuis contenu-sectoriel.json
        (une seule source : eperf_core/sectors.py via _build/generer-contenu.py) ;
     3. la démonstration interactive, branchée sur l'API de production d'ePerformance
        avec un site de démonstration — limitée à 5 questions par visiteur, et
        honnête sur les erreurs (CORS, réseau, quota) comme sur les temps de réponse.

   Règle C2 appliquée en incluant ici : la démo ne promet rien — elle envoie
   une question, affiche la réponse et le temps mesuré.
   ========================================================================== */

(function () {
  'use strict';

  document.documentElement.classList.remove('no-js');

  /* ── 1. Thème clair / sombre ─────────────────────────────────────────── */

  var boutonTheme = document.querySelector('[data-theme-toggle]');
  if (boutonTheme) {
    var appliquerEtatTheme = function () {
      var sombre = document.documentElement.getAttribute('data-theme') === 'dark';
      boutonTheme.setAttribute('aria-pressed', String(sombre));
      boutonTheme.setAttribute('aria-label', sombre ? 'Activer le thème clair' : 'Activer le thème sombre');
    };
    appliquerEtatTheme();
    boutonTheme.addEventListener('click', function () {
      var suivant = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', suivant);
      try { localStorage.setItem('eperf-theme', suivant); } catch (e) { /* stockage indisponible : le thème reste pour la session */ }
      appliquerEtatTheme();
    });
  }

  /* ── 2. Contenu sectoriel — une seule source, le JSON généré ─────────── */

  var donnees = null;            // contenu de contenu-sectoriel.json (si chargé)
  var secteurCourant = 'restauration';

  var select = document.getElementById('select-secteur');
  var titreHero = document.getElementById('titre-hero');
  var accrocheHero = document.querySelector('.accroche-hero');
  var annonce = document.getElementById('annonce-secteur');
  var rappelMetier = document.getElementById('rappel-metier');

  function nomDuSecteur(slug) {
    if (donnees && donnees.secteurs[slug]) return donnees.secteurs[slug].nom;
    var option = select ? select.querySelector('option[value="' + slug + '"]') : null;
    return option ? option.textContent : slug;
  }

  function appliquerSecteur(slug) {
    secteurCourant = slug;
    var s = donnees && donnees.secteurs[slug];

    // Hero
    if (s && titreHero) titreHero.textContent = s.hero.titre;
    if (s && accrocheHero) accrocheHero.textContent = s.hero.accroche;

    // Panneaux de capacités (S2) — pré-rendus dans le balisage, on bascule hidden
    document.querySelectorAll('[data-panneau]').forEach(function (panneau) {
      var actif = panneau.getAttribute('data-panneau') === slug;
      if (actif && panneau.hidden) {
        panneau.hidden = false;
        // Relance l'animation d'apparition sans recréer le nœud.
        panneau.style.animation = 'none';
        void panneau.offsetHeight;
        panneau.style.animation = '';
      } else if (!actif) {
        panneau.hidden = true;
      }
    });

    // Questions suggérées de la démo (S4)
    majSuggestions(slug, s ? s.questions_demo : null);

    // Rappel du secteur (S8)
    if (rappelMetier) rappelMetier.textContent = nomDuSecteur(slug);

    // Annonce pour les lecteurs d'écran
    if (annonce) annonce.textContent = 'Page adaptée au métier : ' + nomDuSecteur(slug);
  }

  if (select) {
    select.addEventListener('change', function () {
      appliquerSecteur(select.value);
    });
  }

  fetch('contenu-sectoriel.json', { cache: 'no-cache' })
    .then(function (reponse) {
      if (!reponse.ok) throw new Error('HTTP ' + reponse.status);
      return reponse.json();
    })
    .then(function (json) {
      donnees = json;
      appliquerSecteur(secteurCourant);
    })
    .catch(function () {
      // Sans le JSON, la page reste utilisable : le balisage pré-rendu porte
      // le secteur par défaut et les questions par template data-questions.
      majSuggestions(secteurCourant, null);
    });

  /* ── 3. Démonstration interactive — branchée sur l'API de production ─── */

  var LIMITE_QUESTIONS = 5;
  var URL_API = 'https://web-production-4ab53.up.railway.app/api/chatbot/message';
  var SITE_DEMO = 'restaurant_chez_amina';

  var fil = document.getElementById('fil-messages');
  var formulaire = document.getElementById('form-chat');
  var saisie = document.getElementById('saisie-message');
  var conteneurSuggestions = document.getElementById('suggestions');
  var compteur = document.getElementById('compteur-questions');
  var noteErreur = null;

  var questionsEnvoyees = 0;
  try {
    questionsEnvoyees = parseInt(sessionStorage.getItem('mia-demo-questions') || '0', 10) || 0;
  } catch (e) { /* sessionStorage indisponible : limite par page */ }
  var enCours = false;

  function majCompteur() {
    if (!compteur) return;
    var restantes = Math.max(0, LIMITE_QUESTIONS - questionsEnvoyees);
    compteur.textContent = restantes === 0
      ? 'Limite atteinte'
      : restantes + (restantes > 1 ? ' questions disponibles' : ' question disponible');
  }

  function afficherErreur(texte) {
    if (!fil) return;
    if (noteErreur) noteErreur.remove();
    noteErreur = document.createElement('p');
    noteErreur.className = 'note-erreur';
    noteErreur.setAttribute('role', 'alert');
    noteErreur.textContent = texte;
    var fenetre = document.querySelector('[data-demo]');
    if (fenetre) fenetre.insertBefore(noteErreur, fenetre.querySelector('.saisie-chat'));
  }

  function ajouterMessage(role, texte, metrique) {
    if (!fil) return;
    var bulle = document.createElement('div');
    bulle.className = 'message ' + (role === 'visiteur' ? 'visiteur' : 'mia');
    var paragraphe = document.createElement('p');
    paragraphe.textContent = texte;
    bulle.appendChild(paragraphe);
    if (metrique) {
      var span = document.createElement('span');
      span.className = 'metrique-reponse';
      span.textContent = metrique;
      bulle.appendChild(span);
    }
    fil.appendChild(bulle);
    fil.scrollTop = fil.scrollHeight;
    return bulle;
  }

  function bloquerDemo() {
    if (saisie) { saisie.disabled = true; saisie.placeholder = 'Démo terminée — installez Mia sur votre site'; }
    if (formulaire) formulaire.querySelector('button[type="submit"]').disabled = true;
    if (conteneurSuggestions) conteneurSuggestions.querySelectorAll('.suggestion').forEach(function (b) { b.disabled = true; });
    ajouterMessage('mia', 'Démo limitée — installez Mia sur votre site. Contactez ePerformance pour l\u2019installation complète.');
  }

  function majSuggestions(slug, questions) {
    if (!conteneurSuggestions) return;
    if (!questions) {
      var gabarit = conteneurSuggestions.querySelector('template[data-questions="' + slug + '"]');
      // Le template porte les trois questions séparées par un espace — on
      // découpe après chaque point d'interrogation.
      questions = gabarit ? gabarit.textContent.trim().split(/(?<=\?)\s+/) : [];
    }
    conteneurSuggestions.querySelectorAll('.suggestion').forEach(function (b) { b.remove(); });
    questions.slice(0, 3).forEach(function (q) {
      var bouton = document.createElement('button');
      bouton.type = 'button';
      bouton.className = 'suggestion';
      bouton.textContent = q;
      bouton.disabled = questionsEnvoyees >= LIMITE_QUESTIONS;
      bouton.addEventListener('click', function () {
        if (saisie && !enCours) {
          saisie.value = q;
          formulaire.dispatchEvent(new Event('submit', { cancelable: true }));
        }
      });
      conteneurSuggestions.appendChild(bouton);
    });
  }

  function envoyerQuestion(texte) {
    if (enCours) return;
    if (questionsEnvoyees >= LIMITE_QUESTIONS) { bloquerDemo(); return; }

    questionsEnvoyees += 1;
    try { sessionStorage.setItem('mia-demo-questions', String(questionsEnvoyees)); } catch (e) { /* idem */ }
    majCompteur();
    ajouterMessage('visiteur', texte);

    var depart = performance.now();
    enCours = true;
    if (saisie) saisie.disabled = true;

    // Indicateur d'écriture
    var indicateur = document.createElement('div');
    indicateur.className = 'indicateur-ecriture';
    indicateur.setAttribute('aria-label', 'Mia écrit');
    for (var i = 0; i < 3; i++) indicateur.appendChild(document.createElement('span'));
    if (fil) { fil.appendChild(indicateur); fil.scrollTop = fil.scrollHeight; }

    fetch(URL_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', text: texte }],
        site_id: SITE_DEMO
      })
    })
      .then(function (reponse) {
        if (reponse.status === 429) {
          throw new Error('quota');
        }
        if (!reponse.ok) {
          throw new Error('http ' + reponse.status);
        }
        return reponse.json();
      })
      .then(function (corps) {
        var duree = (performance.now() - depart) / 1000;
        var dureeFormatee = duree.toFixed(1).replace('.', ',');
        if (indicateur.parentNode) indicateur.remove();
        ajouterMessage('mia',
          (corps && corps.text) ? corps.text : 'Je n\u2019ai pas pu formuler de réponse — réessayez.',
          'Réponse en ' + dureeFormatee + ' s — mesuré sur cette conversation'
        );
      })
      .catch(function (erreur) {
        if (indicateur.parentNode) indicateur.remove();
        if (erreur && erreur.message === 'quota') {
          ajouterMessage('mia', 'Trop de questions en peu de temps — réessayez dans un instant.');
        } else if (questionsEnvoyees >= LIMITE_QUESTIONS) {
          bloquerDemo();
        } else {
          ajouterMessage('mia', 'Je ne peux pas répondre depuis cette adresse pour le moment. La démo fonctionne sur https://kstephane683.github.io/eperformance-mia/ — ou contactez ePerformance pour une démonstration en direct.');
          afficherErreur('La démonstration ne peut pas joindre l\u2019API depuis ce domaine (origine non encore autorisée côté ePerformance).');
        }
      })
      .finally(function () {
        enCours = false;
        if (questionsEnvoyees >= LIMITE_QUESTIONS) {
          bloquerDemo();
        } else if (saisie) {
          saisie.disabled = false;
          saisie.focus();
        }
      });
  }

  if (formulaire) {
    formulaire.addEventListener('submit', function (evenement) {
      evenement.preventDefault();
      var texte = saisie ? saisie.value.trim() : '';
      if (!texte) return;
      saisie.value = '';
      envoyerQuestion(texte);
    });
  }

  /* ── 4. Bouton « Installer l'application » — URL en attente ───────────── */
  /* TODO propriétaire : remplacer ce bloc par <a href="URL-DE-L-APP"> dès
     que l'URL de l'application Mia est communiquée. */

  var btnInstallerApp = document.getElementById('btn-installer-app');
  var noteInstall = document.getElementById('note-install');
  if (btnInstallerApp) {
    btnInstallerApp.addEventListener('click', function () {
      if (noteInstall) {
        noteInstall.textContent = 'L\u2019accès à l\u2019application est livré avec l\u2019installation de Mia sur votre site — contactez ePerformance pour démarrer.';
      }
    });
  }

  /* ── Initialisation ───────────────────────────────────────────────────── */

  majCompteur();
  if (questionsEnvoyees >= LIMITE_QUESTIONS) bloquerDemo();
})();
