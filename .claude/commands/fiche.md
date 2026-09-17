---
description: Génère le résumé, la fiche de révision et les exercices (LaTeX) d'un cours enregistré
---

Génère le résumé, la fiche de révision et les exercices pour le cours d'id `$ARGUMENTS`.

1. Lis `~/Cours/$ARGUMENTS/meta.json` pour le titre, la date et le code `matiere` du cours
   (regarde `app/subjects.py` dans ce projet pour retrouver le nom complet du module à
   partir du code). Si le dossier n'existe pas, dis-le clairement et arrête-toi.
2. Lis `~/Cours/$ARGUMENTS/transcription.txt`. C'est une transcription brute (whisper) : peu
   ponctuée, parfois hachée, mélange de langues sur les hésitations — pas lisible telle
   quelle. Si elle est vide ou ne contient que du bruit (quelques mots sans rapport, ex. un
   enregistrement qui a échoué), dis-le clairement et arrête-toi plutôt que d'inventer un
   résumé, une fiche ou des exercices à partir de rien.
3. Si `~/Cours/$ARGUMENTS/slides/` existe : lis `slides/texte.txt`, et regarde chaque
   `slides/page-XX.png` avec l'outil Read (ce sont des images) pour capter les schémas,
   graphes et formules que le texte extrait ne rend pas bien.
4. Écris `~/Cours/$ARGUMENTS/resume.md` : un résumé propre et lisible de la transcription,
   façon page Notion (voir `CLAUDE.md` section "Résumé" pour le format exact). Si des slides
   existent, appuie-toi dessus pour clarifier ce que la transcription rend mal (termes
   techniques, formules, noms propres mal transcrits par whisper) — le prof les affiche en
   parlant, donc elles font autorité sur le vocabulaire exact même si le résumé suit le fil
   chronologique de l'oral, pas le plan des slides. C'est un livrable à part entière
   (consultable dans l'app), et il sert aussi de base pour la fiche et les exercices
   ci-dessous.
5. Lance l'agent **`fiche-cours`** (outil Agent) pour écrire `fiche.tex`. Dans le prompt,
   donne-lui explicitement :
   - le dossier support : `~/Cours/$ARGUMENTS/` avec `slides/texte.txt` + `slides/page-XX.png`
     (s'ils existent), `resume.md`, `transcription.txt` ;
   - la priorité des sources : **slides d'abord** si présentes (structure et contenu suivent
     leur plan), résumé/transcript en secondaire (contexte oral, exemples, digressions) ;
     sans slides, se baser directement sur le résumé/transcript ;
   - le titre du cours, la matière et la date (lus à l'étape 1) ;
   - la destination exacte : sauvegarder dans `~/Cours/$ARGUMENTS/fiche.tex` (pas
     `livrables/mit/...`, sa destination par défaut), compiler depuis ce dossier pour produire
     `fiche.pdf` au même endroit.
   L'agent lit lui-même les supports, écrit, compile et vérifie le rendu (Overfull hbox, PNG) :
   pas besoin de relire son travail en détail, juste confirmer que `fiche.pdf` existe au retour.
6. Lance l'agent **`fiche-exo`** (outil Agent) pour écrire `exercices.tex`, avec le même
   contexte support/priorité/destination qu'à l'étape précédente (adapter le chemin en
   `~/Cours/$ARGUMENTS/exercices.tex` / `exercices.pdf`). Si `fiche.tex` vient d'être généré à
   l'étape précédente, mentionne son chemin pour que l'agent l'utilise comme checklist de
   couverture des notions (comme il le ferait avec une fiche dans `livrables/mit/`).
7. Termine par un résumé court : titre du cours, nombre d'exercices générés, et confirmation
   que `resume.md`, `fiche.pdf` et `exercices.pdf` sont bien présents dans le dossier.
