# cahier

Ce dossier contient l'app **Cahier** d'Aaron : enregistrement micro, transcription locale
(faster-whisper, anglais), et bibliothèque de cours groupée par matière MIT. Les fiches de
révision et exercices ne sont **pas** générés automatiquement par l'app (pas de clé API
embarquée) — c'est fait ici, à la demande, par Claude Code.

## Où sont les données

Chaque cours est un dossier `~/Cours/<id>/` (hors de ce repo) contenant :
- `audio.wav` — enregistrement brut
- `transcription.txt` — transcription horodatée, en anglais, brute (whisper, peu ponctuée)
- `slides/texte.txt` + `slides/page-XX.png` — si des slides ont été ajoutées (texte extrait
  page par page + image de chaque page, à lire avec l'outil Read pour les schémas/formules)
- `meta.json` — titre, date, durée, `matiere` (code du module, voir `app/subjects.py`)
- `resume.md` — résumé lisible de la transcription (voir section "Résumé" ci-dessous)
- `fiche.tex` / `fiche.pdf`, `exercices.tex` / `exercices.pdf` — générés par la commande `/fiche`

## Générer le résumé, la fiche + les exercices

Utiliser la commande `/fiche <id-du-cours>` (voir `.claude/commands/fiche.md`) — malgré son
nom elle génère les trois : `resume.md`, `fiche.tex` et `exercices.tex`. L'app affiche l'id
et propose un bouton "Copier la demande pour Claude Code" qui copie directement `/fiche <id>`
dans le presse-papiers.

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

## Conventions LaTeX

- Préambule partagé : `latex/preambule.tex` (macros mathématiques usuelles, `definition` et
  `correction` en tcolorbox, geometry/hyperref/fancyhdr déjà configurés).
- Chaque dossier de cours doit rester autonome : copier `latex/preambule.tex` vers
  `~/Cours/<id>/preambule.tex` avant de générer `fiche.tex`/`exercices.tex`, qui l'importent
  avec `\input{preambule.tex}` (chemin relatif, pas de dépendance externe).
- Compiler avec `pdflatex` (`/Library/TeX/texbin/pdflatex`), deux passes si des `\ref`/`\cite`
  sont utilisés.
- Le contenu est toujours en anglais (les cours source sont en anglais) sauf demande contraire.

### Priorité des sources : slides d'abord

Fiche et exercices doivent principalement s'appuyer sur **les slides** quand elles existent
(structure, définitions, formules telles que présentées par l'enseignant) — c'est la source
la plus fiable et la mieux organisée. Le résumé/transcript sert de source **secondaire** :
contexte donné à l'oral, exemples, digressions utiles, questions/réponses. Sans slides,
structurer directement sur le résumé/transcript.

### `fiche.tex` — fiche de révision

Structure attendue : titre + date du cours, puis sections par concept clé (suivant le plan
des slides s'il y en a), avec définitions en boîte `definition`, formules importantes, et
schéma de synthèse si les slides en fournissent un. Concis, pensé pour réviser vite avant un
examen — pas une retranscription du cours.

### `exercices.tex` — exercices avec corrigés

4 à 6 exercices de difficulté progressive testant la compréhension (pas du par-cœur) du
contenu des slides s'il y en a (voir "Priorité des sources" ci-dessus), sinon du
résumé/transcript. Tous les énoncés d'abord, puis, après un `\newpage` et une section
clairement titrée "Corrections", les corrigés détaillés (boîte `correction`) — pour
permettre de chercher avant de regarder la réponse (rappel actif).
