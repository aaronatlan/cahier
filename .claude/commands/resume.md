---
description: Génère le résumé (resume.md) d'un cours enregistré
---

Génère le résumé du cours d'id `$ARGUMENTS`.

1. Lis `~/Cours/$ARGUMENTS/meta.json` pour le titre, la date et le code `matiere` du cours
   (regarde `app/subjects.py` dans ce projet pour retrouver le nom complet du module à
   partir du code). Si le dossier n'existe pas, dis-le clairement et arrête-toi.
2. Lis `~/Cours/$ARGUMENTS/transcription.txt`. C'est une transcription brute (whisper) : peu
   ponctuée, parfois hachée, mélange de langues sur les hésitations — pas lisible telle
   quelle. Si elle est vide ou ne contient que du bruit (quelques mots sans rapport, ex. un
   enregistrement qui a échoué), dis-le clairement et arrête-toi plutôt que d'inventer un
   résumé à partir de rien.
3. Si `~/Cours/$ARGUMENTS/slides/` existe : lis `slides/texte.txt`, et regarde chaque
   `slides/page-XX.png` avec l'outil Read (ce sont des images) pour capter les schémas,
   graphes et formules que le texte extrait ne rend pas bien.
4. Écris `~/Cours/$ARGUMENTS/resume.md` : un résumé propre et lisible de la transcription,
   façon page Notion (voir `CLAUDE.md` section "Résumé" pour le format exact). Si des slides
   existent, appuie-toi dessus pour clarifier ce que la transcription rend mal (termes
   techniques, formules, noms propres mal transcrits par whisper) — le prof les affiche en
   parlant, donc elles font autorité sur le vocabulaire exact même si le résumé suit le fil
   chronologique de l'oral, pas le plan des slides. C'est un livrable à part entière
   (consultable dans l'app), et il peut aussi servir de source secondaire pour la fiche et
   les exercices (`/fiche <id>`, `/exercices <id>`) s'ils sont générés séparément.
5. Termine par un résumé court : titre du cours, confirmation que `resume.md` est bien
   présent dans le dossier.
