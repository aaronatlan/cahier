# cahier

Ce dossier contient l'app **Cahier** d'Aaron : enregistrement micro, transcription locale
(faster-whisper, anglais), et bibliothèque de cours groupée par matière MIT. Les fiches de
révision et exercices ne sont **pas** générées par une clé API embarquée dans l'app — le
bouton "Générer avec Claude Code" lance le CLI `claude` déjà authentifié sur la machine
d'Aaron (voir section "Génération à la demande" ci-dessous), à la demande, jamais en fond
sans action explicite de l'utilisateur.

## Où sont les données

Chaque cours est un dossier `~/Cours/<id>/` (hors de ce repo) contenant :
- `audio.wav` — enregistrement brut
- `transcription.txt` — transcription horodatée, en anglais, brute (whisper, peu ponctuée)
- `slides/texte.txt` + `slides/page-XX.png` — si des slides ont été ajoutées (texte extrait
  page par page + image de chaque page, à lire avec l'outil Read pour les schémas/formules)
- `meta.json` — titre, date, durée, `matiere` (code du module, voir `app/subjects.py`)
- `resume.md` — résumé lisible de la transcription (voir section "Résumé" ci-dessous)
- `fiche.tex` / `fiche.pdf` (commande `/fiche`), `exercices.tex` / `exercices.pdf` (commande
  `/exercices`)
- `audio.partial.pcm` — sauvegarde continue de l'audio *pendant* l'enregistrement (PCM 16 bits
  brut, supprimée dès que `audio.wav` est écrit à l'arrêt) ; `.transcribed_until` — jusqu'où
  l'audio est déjà transcrit. Ces deux fichiers n'existent que si l'app a été tuée avant la
  fin de l'arrêt : `app/recovery.py` les exploite au démarrage suivant pour reconstruire
  `audio.wav`, transcrire la fin et clore le cours (statut `done`).

## Génération à la demande (résumé, fiche, exercices)

Trois commandes indépendantes, une par livrable (`.claude/commands/`) :
`/resume <id>` → `resume.md`, `/fiche <id>` → `fiche.tex`/`fiche.pdf`,
`/exercices <id>` → `exercices.tex`/`exercices.pdf`. Chacune lit elle-même ce dont elle a
besoin (méta, transcription, slides) ; `/fiche` et `/exercices` exploitent `resume.md` /
`fiche.tex` s'ils existent déjà mais n'en dépendent pas. Deux façons de les lancer :

- **Depuis l'app** : le bouton "Générer avec Claude Code" de chaque onglet (Résumé/Fiche/
  Exercices, quand vide) déclenche **uniquement** son livrable via
  `POST /api/courses/{id}/generate/{resume|fiche|exercices}`, qui lance `claude -p
  "/<kind> <id>"` en sous-processus (chemin absolu vers le binaire, `--permission-mode
  acceptEdits` + `--allowedTools` scopé à Read/Write/Edit/Bash/Grep/Glob/WebSearch/WebFetch/
  Agent — pas `--dangerously-skip-permissions`, qui bypasserait tout le système de
  permissions). Un verrou `.generating-<kind>` dans le dossier du cours empêche un double
  lancement du même livrable (y compris après un redémarrage de l'app ; expire après 30 min
  s'il reste orphelin) mais autorise deux livrables différents en parallèle ; la sortie est
  journalisée dans `generation-<kind>.log`. L'app poll `GET
  /api/courses/{id}/generate/{kind}/status` pour savoir quand rafraîchir l'affichage.
- **Depuis une session Claude Code ouverte dans ce dossier** (les commandes projet ne sont
  reconnues que si la session est rootée ici, pas à la racine du workspace parent) : taper
  directement `/resume <id>`, `/fiche <id>` ou `/exercices <id>`.

## Résumé (`resume.md`)

La transcription brute (whisper) n'est pas lisible : peu de ponctuation, hésitations,
passages qui changent de langue. `resume.md` la transforme en résumé structuré et
scannable, façon page Notion. C'est un livrable en soi (affiché dans l'app, onglet
"Résumé"), et sert aussi de source secondaire pour la fiche et les exercices.

Si des slides existent pour le cours, s'en servir pour clarifier ce que la transcription
rend mal : termes techniques, formules, noms propres — le prof les affiche au tableau en
parlant, elles font donc autorité sur le vocabulaire exact. Le résumé garde toutefois la
structure chronologique de l'oral (voir format ci-dessous), il ne suit pas le plan des
slides comme le fait la fiche.

Format à suivre (markdown simple, rendu par un mini-parseur maison dans l'app — s'en tenir à
ces éléments) :
- Une section `## Overview` en premier : 2-4 puces qui donnent le contexte général (sujet de
  la séance, ce qui est couvert).
- Puis une section `## <Titre thématique>` par grand thème abordé, dans l'ordre où ils
  apparaissent dans le cours. Le titre résume le thème en quelques mots.
- Sous chaque titre, des puces (`- `) concises, pas des paragraphes. Sous-puces indentées de
  2 espaces si besoin de détailler un point.
- `**gras**` sur les termes clés, notions importantes, noms propres.
- Si une question/réponse notable a eu lieu à l'oral, l'intégrer comme une puce (ex.
  `- **Q:** ... — **A:** ...`) plutôt que de la noter mot à mot.
- Toujours en anglais (comme la transcription source), sauf demande contraire.
- Ne pas essayer de tout dire : c'est un résumé pour réviser vite, pas une retranscription
  reformulée phrase par phrase.

## Génération de `fiche.tex` et `exercices.tex` : délégation aux agents

`fiche.tex` et `exercices.tex` ne sont **pas** écrits directement par la session `/fiche`/`/exercices` :
elles délèguent à deux agents définis au niveau du workspace parent (`~/jarvis-starter-kit/.claude/agents/`),
déjà réglés sur les standards de qualité et de mise en forme voulus par Aaron pour ses fiches MIT :

- **`fiche-cours`** pour `fiche.tex` — encadrés `tcolorbox` colorés par type de contenu
  (définition/théorème/méthode/formule/exemple/piège), un exemple concret par notion,
  vérification stricte du sourcing, compilation + relecture visuelle (PNG, `Overfull \hbox`).
- **`fiche-exo`** pour `exercices.tex` — mêmes standards, exercices à difficulté progressive
  avec corrigés détaillés, sourcing vérifié, aucun exercice trivial.

Ces agents utilisent leur **propre préambule LaTeX autonome** (embarqué dans chaque `.tex`,
pas de fichier partagé à copier) et leur propre destination par défaut
(`livrables/mit/fiche-<nom>/...`) : `/fiche` et `/exercices` leur redirigent explicitement la sortie vers
`~/Cours/<id>/fiche.tex` et `~/Cours/<id>/exercices.tex` dans le prompt de délégation (voir
`.claude/commands/fiche.md` et `exercices.md`). Ne pas dupliquer leurs instructions de style ici — elles vivent
dans les fichiers d'agent, source de vérité unique pour éviter toute dérive entre les deux.

### Priorité des sources : slides d'abord

Fiche et exercices doivent principalement s'appuyer sur **les slides** quand elles existent
(structure, définitions, formules telles que présentées par l'enseignant) — c'est la source
la plus fiable et la mieux organisée. Le résumé/transcript sert de source **secondaire** :
contexte donné à l'oral, exemples, digressions utiles, questions/réponses. Sans slides,
structurer directement sur le résumé/transcript. `/fiche` et `/exercices` transmettent cette priorité aux agents
dans son prompt de délégation (les agents n'ont pas cette notion de "slides Cahier" par défaut).
