# cahier

Ce dossier contient l'app **Cahier** d'Aaron : enregistrement micro, transcription locale
(faster-whisper, anglais), et bibliothèque de cours groupée par matière MIT. Les fiches de
révision et exercices ne sont **pas** générés automatiquement par l'app (pas de clé API
embarquée) — c'est fait ici, à la demande, par Claude Code.

## Où sont les données

Chaque cours est un dossier `~/Cours/<id>/` (hors de ce repo) contenant :
- `audio.wav` — enregistrement brut
- `transcription.txt` — transcription horodatée, en anglais
- `slides/texte.txt` + `slides/page-XX.png` — si des slides ont été ajoutées (texte extrait
  page par page + image de chaque page, à lire avec l'outil Read pour les schémas/formules)
- `meta.json` — titre, date, durée, `matiere` (code du module, voir `app/subjects.py`)
- `fiche.tex` / `fiche.pdf`, `exercices.tex` / `exercices.pdf` — générés par la commande `/fiche`

## Générer une fiche + des exercices

Utiliser la commande `/fiche <id-du-cours>` (voir `.claude/commands/fiche.md`). L'app affiche
l'id et propose un bouton "Copier la demande pour Claude Code" qui copie directement
`/fiche <id>` dans le presse-papiers.

## Conventions LaTeX

- Préambule partagé : `latex/preambule.tex` (macros mathématiques usuelles, `definition` et
  `correction` en tcolorbox, geometry/hyperref/fancyhdr déjà configurés).
- Chaque dossier de cours doit rester autonome : copier `latex/preambule.tex` vers
  `~/Cours/<id>/preambule.tex` avant de générer `fiche.tex`/`exercices.tex`, qui l'importent
  avec `\input{preambule.tex}` (chemin relatif, pas de dépendance externe).
- Compiler avec `pdflatex` (`/Library/TeX/texbin/pdflatex`), deux passes si des `\ref`/`\cite`
  sont utilisés.
- Le contenu est toujours en anglais (les cours source sont en anglais) sauf demande contraire.

### `fiche.tex` — fiche de révision

Structure attendue : titre + date du cours, puis sections par concept clé, avec définitions
en boîte `definition`, formules importantes, et schéma de synthèse si les slides en fournissent
un. Concis, pensé pour réviser vite avant un examen — pas une retranscription du cours.

### `exercices.tex` — exercices avec corrigés

4 à 6 exercices de difficulté progressive testant la compréhension du cours (pas du
par-cœur). Tous les énoncés d'abord, puis, après un `\newpage` et une section clairement
titrée "Corrections", les corrigés détaillés (boîte `correction`) — pour permettre de
chercher avant de regarder la réponse (rappel actif).
