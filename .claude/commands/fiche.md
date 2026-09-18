---
description: Génère la fiche de révision (fiche.tex/fiche.pdf) d'un cours enregistré
---

Génère la fiche de révision pour le cours d'id `$ARGUMENTS`.

1. Lis `~/Cours/$ARGUMENTS/meta.json` pour le titre, la date et le code `matiere` du cours
   (regarde `app/subjects.py` dans ce projet pour retrouver le nom complet du module à
   partir du code). Si le dossier n'existe pas, dis-le clairement et arrête-toi.
2. Repère les sources disponibles dans `~/Cours/$ARGUMENTS/` :
   - `slides/texte.txt` + `slides/page-XX.png` (si le dossier `slides/` existe — texte
     extrait page par page + image de chaque page, à lire avec l'outil Read pour les
     schémas/formules) ;
   - `resume.md` (s'il a déjà été généré via `/resume <id>` — sinon ignore, la fiche peut se
     construire directement sur `transcription.txt`) ;
   - `transcription.txt` (transcription brute whisper, toujours présente).
   Si aucune de ces sources n'a de contenu exploitable (transcription vide/juste du bruit et
   pas de slides), dis-le clairement et arrête-toi plutôt que d'inventer une fiche à partir
   de rien.
3. Lance l'agent **`fiche-cours`** (outil Agent) pour écrire `fiche.tex`. Dans le prompt,
   donne-lui explicitement :
   - le dossier support et les fichiers disponibles identifiés à l'étape 2 ;
   - la priorité des sources : **slides d'abord** si présentes (structure et contenu suivent
     leur plan), résumé/transcript en secondaire (contexte oral, exemples, digressions) ;
     sans slides, se baser directement sur le résumé/transcript ;
   - le titre du cours, la matière et la date (lus à l'étape 1) ;
   - la destination exacte : sauvegarder dans `~/Cours/$ARGUMENTS/fiche.tex` (pas
     `livrables/mit/...`, sa destination par défaut), compiler depuis ce dossier pour
     produire `fiche.pdf` au même endroit.
   L'agent lit lui-même les supports, écrit, compile et vérifie le rendu (Overfull hbox, PNG) :
   pas besoin de relire son travail en détail, juste confirmer que `fiche.pdf` existe au
   retour.
4. Termine par un résumé court : titre du cours, confirmation que `fiche.pdf` est bien
   présent dans le dossier.
