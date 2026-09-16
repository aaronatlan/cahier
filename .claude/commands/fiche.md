---
description: Génère le résumé, la fiche de révision et les exercices (LaTeX) d'un cours enregistré
---

Génère le résumé, la fiche de révision et les exercices pour le cours d'id `$ARGUMENTS`.

1. Lis `~/Cours/$ARGUMENTS/meta.json` pour le titre, la date et le code `matiere` du cours
   (regarde `app/subjects.py` dans ce projet pour retrouver le nom complet du module à
   partir du code). Si le dossier n'existe pas, dis-le clairement et arrête-toi.
2. Lis `~/Cours/$ARGUMENTS/transcription.txt`. C'est une transcription brute (whisper) : peu
   ponctuée, parfois hachée, mélange de langues sur les hésitations — pas lisible telle
   quelle.
3. Si `~/Cours/$ARGUMENTS/slides/` existe : lis `slides/texte.txt`, et regarde chaque
   `slides/page-XX.png` avec l'outil Read (ce sont des images) pour capter les schémas,
   graphes et formules que le texte extrait ne rend pas bien.
4. Écris `~/Cours/$ARGUMENTS/resume.md` : un résumé propre et lisible de la transcription,
   façon page Notion (voir `CLAUDE.md` section "Résumé" pour le format exact). C'est un
   livrable à part entière (consultable dans l'app), et il sert aussi de base pour la fiche
   et les exercices ci-dessous.
5. Copie `latex/preambule.tex` (dans ce projet) vers `~/Cours/$ARGUMENTS/preambule.tex`.
6. Écris `~/Cours/$ARGUMENTS/fiche.tex` : fiche de révision concise en anglais. **Source
   principale : les slides** (si présentes) — structure et contenu de la fiche suivent leur
   plan. Le résumé/transcript sert de source secondaire pour le contexte donné à l'oral, les
   exemples, les nuances ou digressions utiles qui ne sont pas sur les slides. S'il n'y a pas
   de slides, structure-toi directement sur le résumé/transcript. Définitions en boîte
   `definition`, formules importantes mises en avant. Voir `CLAUDE.md` (section "Conventions
   LaTeX") pour le détail du style attendu.
7. Écris `~/Cours/$ARGUMENTS/exercices.tex` : 4 à 6 exercices progressifs testant la
   compréhension (pas du par-cœur) du contenu des slides, éclairés par ce qui a été dit à
   l'oral (exemples donnés en cours, questions d'élèves et réponses, etc.). Tous les énoncés
   d'abord, puis après `\newpage` une section "Corrections" avec les corrigés détaillés en
   boîte `correction`.
8. Compile les deux fichiers avec `pdflatex` depuis `~/Cours/$ARGUMENTS/` (deux passes) pour
   produire `fiche.pdf` et `exercices.pdf`. Si la compilation échoue, corrige le `.tex` et
   recompile plutôt que d'abandonner.
9. Termine par un résumé court : titre du cours, nombre d'exercices générés, et confirmation
   que `resume.md`, `fiche.pdf` et `exercices.pdf` sont bien présents dans le dossier.
