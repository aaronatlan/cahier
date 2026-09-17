# Cahier — enregistrement, transcription, fiche + exercices

App macOS pour enregistrer et transcrire les cours (anglais, local, gratuit,
faster-whisper) sans ouvrir de terminal, avec une bibliothèque de tous les
cours passés groupée par matière MIT. Les fiches de révision et exercices en
LaTeX sont générés à la demande par Claude Code (pas de clé API embarquée
dans l'app).

Ce dossier est son propre repo git (poussé sur
[github.com/aaronatlan/cahier](https://github.com/aaronatlan/cahier), public),
imbriqué dans `jarvis-starter-kit` (privé) mais ignoré par son `.gitignore` —
donc un seul `git push` d'ici suffit, jamais besoin de toucher au repo jarvis
pour un changement sur Cahier. L'app installée tourne depuis
`~/Applications/Cahier.app` et les données des cours dans `~/Cours/`.

## Utilisation au quotidien

Ouvre **Cahier** depuis le Dock ou Spotlight. Aucun terminal à ouvrir.

1. Clique le bouton rond pour démarrer/arrêter l'enregistrement (choisis le
   module concerné avant de lancer).
2. La transcription se lance automatiquement (anglais, pas de traduction).
3. Ajoute les slides du cours (PDF) dans l'onglet **Slides** si tu en as.
4. Onglets **Résumé** / **Fiche** / **Exercices** : bouton "Générer avec
   Claude Code" → lance directement le CLI `claude` en fond (pas de
   copier-coller, pas de terminal) ; résumé, fiche et exercices sont générés
   et la fiche/les exercices compilés en PDF, consultables directement dans
   l'app une fois prêts.

Tous les cours sont stockés dans `~/Cours/<id>/` (audio, transcription,
slides, fiche/exercices).

## Installation (une seule fois, déjà faite)

```bash
brew install portaudio
cd livrables/applications/cahier
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Reconstruire l'app après un changement de code

`Cahier.app` est empaqueté avec `py2app` en **mode alias** (`-A`) : le bundle
contient un vrai exécutable compilé (nécessaire pour que macOS l'identifie
correctement et propose l'autorisation micro — voir plus bas), mais son code
Python reste un lien symbolique vers ce dossier. Donc la plupart des
changements (Python, JS, CSS) sont pris en compte au prochain lancement,
**sans rebuild**. Un rebuild n'est nécessaire que si tu changes `setup.py`,
l'icône, ou l'`Info.plist` :

```bash
source venv/bin/activate
python3 setup.py py2app -A
rm -rf ~/Applications/Cahier.app
cp -R dist/Cahier.app ~/Applications/Cahier.app
codesign --force --deep --sign - ~/Applications/Cahier.app
```

### Pourquoi py2app (et pas un simple script shell)

La première version de l'app était un bundle fait main dont l'exécutable
était juste un script shell lançant `python3` (le vrai binaire de
`Python.framework`). macOS attribue les autorisations TCC (micro, dossiers
protégés) au binaire qui fait réellement l'appel système, pas au bundle qui
l'a lancé — donc le script shell n'obtenait jamais la popup d'autorisation
micro (silence total en enregistrement, sans erreur). `py2app` produit un
vrai binaire compilé comme exécutable principal, que macOS peut identifier
et signer (`com.aaronatlan.cahier`), ce qui résout le problème.

## Réglages utiles

- `app/transcriber.py` : `MODEL_SIZE` (`"medium"` par défaut) et `LANGUAGE`
  (fixé à `"en"`, les cours étant toujours en anglais).
- `app/subjects.py` : liste des modules MIT pour le regroupement de la
  bibliothèque.
- `.claude/commands/fiche.md` : la commande `/fiche <id>` qui génère la fiche
  et les exercices. Voir `CLAUDE.md` pour les conventions LaTeX.

## Ancien script (`cours.py`)

Le script terminal d'origine (`python3 cours.py`) fonctionne toujours si
besoin, mais l'app graphique (**Cahier**) est l'usage recommandé au
quotidien.
