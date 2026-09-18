---
description: Génère la fiche d'exercices (exercices.tex/exercices.pdf) d'un cours enregistré
---

Génère les exercices pour le cours d'id `$ARGUMENTS`.

1. Lis `~/Cours/$ARGUMENTS/meta.json` pour le titre, la date et le code `matiere` du cours
   (regarde `app/subjects.py` dans ce projet pour retrouver le nom complet du module à
   partir du code). Si le dossier n'existe pas, dis-le clairement et arrête-toi.
2. Repère les sources disponibles dans `~/Cours/$ARGUMENTS/` :
   - `slides/texte.txt` + `slides/page-XX.png` (si le dossier `slides/` existe) ;
   - `resume.md` (s'il a déjà été généré via `/resume <id>` — sinon ignore) ;
   - `transcription.txt` (transcription brute whisper, toujours présente) ;
   - `fiche.tex` (s'il a déjà été généré via `/fiche <id>` — sert alors de checklist pour
     vérifier que chaque notion importante est couverte par au moins un exercice ; sinon
     ignore, les exercices se construisent directement sur les slides/résumé/transcript).
   Si aucune source n'a de contenu exploitable (transcription vide/juste du bruit et pas de
   slides), dis-le clairement et arrête-toi plutôt que d'inventer des exercices à partir de
   rien.
3. Lance l'agent **`fiche-exo`** (outil Agent) pour écrire `exercices.tex`. Dans le prompt,
   donne-lui explicitement :
   - le dossier support et les fichiers disponibles identifiés à l'étape 2 (en mentionnant
     `fiche.tex` s'il existe, pour la checklist de couverture) ;
   - la priorité des sources : **slides d'abord** si présentes, résumé/transcript en
     secondaire ; sans slides, se baser directement sur le résumé/transcript ;
   - le titre du cours, la matière et la date (lus à l'étape 1) ;
   - la destination exacte : sauvegarder dans `~/Cours/$ARGUMENTS/exercices.tex` (pas
     `livrables/mit/...`, sa destination par défaut), compiler depuis ce dossier pour
     produire `exercices.pdf` au même endroit.
   L'agent lit lui-même les supports, écrit, compile et vérifie le rendu (Overfull hbox, PNG) :
   pas besoin de relire son travail en détail, juste confirmer que `exercices.pdf` existe au
   retour.
4. Termine par un résumé court : titre du cours, nombre d'exercices générés, confirmation
   que `exercices.pdf` est bien présent dans le dossier.
