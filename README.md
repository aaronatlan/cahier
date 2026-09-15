# Cahier — enregistrement, transcription, fiche + exercices

App macOS pour enregistrer et transcrire les cours (anglais, local, gratuit,
faster-whisper) sans ouvrir de terminal, avec une bibliothèque de tous les
cours passés groupée par matière MIT. Les fiches de révision et exercices en
LaTeX sont générés à la demande par Claude Code (pas de clé API embarquée
dans l'app).

Le code vit ici, dans `~/cours-transcription` (volontairement hors de
`~/Desktop` — voir `livrables/applications/cahier/README.md` dans
jarvis-starter-kit pour pourquoi). L'app installée tourne depuis
`~/Applications/Cahier.app` et les données des cours dans `~/Cours/`.

## Utilisation au quotidien

Ouvre **Cahier** depuis le Dock ou Spotlight. Aucun terminal à ouvrir.

1. Clique le bouton rond pour démarrer/arrêter l'enregistrement (choisis le
   module concerné avant de lancer).
2. La transcription se lance automatiquement (anglais, pas de traduction).
3. Ajoute les slides du cours (PDF) dans l'onglet **Slides** si tu en as.
4. Onglets **Fiche** / **Exercices** : bouton "Copier la demande pour Claude
   Code" → colle-la dans une session Claude Code ouverte dans ce dossier
   (`~/cours-transcription`) → la fiche et les exercices sont générés en
   LaTeX et compilés en PDF, consultables directement dans l'app.

Tous les cours sont stockés dans `~/Cours/<id>/` (audio, transcription,
slides, fiche/exercices).

## Installation (une seule fois, déjà faite)

```bash
brew install portaudio
cd cours-transcription
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Réglages utiles

- `app/transcriber.py` : `MODEL_SIZE` (`"medium"` par défaut) et `LANGUAGE`
  (fixé à `"en"`, les cours étant toujours en anglais).
- `app/subjects.py` : liste des modules MIT pour le regroupement de la
  bibliothèque.
- `.claude/commands/fiche.md` : la commande `/fiche <id>` qui génère la fiche
  et les exercices. Voir `CLAUDE.md` pour les conventions LaTeX.
- Si ce dossier est un jour déplacé à nouveau, penser à mettre à jour
  `PROJECT_DIR` dans `~/Applications/Cahier.app/Contents/MacOS/launch`.

## Ancien script (`cours.py`)

Le script terminal d'origine (`python3 cours.py`) fonctionne toujours si
besoin, mais l'app graphique (**Cahier**) est l'usage recommandé au
quotidien.
