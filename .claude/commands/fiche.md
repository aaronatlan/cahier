---
description: Génère la fiche de révision et les exercices (LaTeX) d'un cours enregistré
---

Génère la fiche de révision et les exercices pour le cours d'id `$ARGUMENTS`.

1. Lis `~/Cours/$ARGUMENTS/meta.json` pour le titre, la date et le code `matiere` du cours
   (regarde `app/subjects.py` dans ce projet pour retrouver le nom complet du module à
   partir du code). Si le dossier n'existe pas, dis-le clairement et arrête-toi.
2. Lis `~/Cours/$ARGUMENTS/transcription.txt`.
3. Si `~/Cours/$ARGUMENTS/slides/` existe : lis `slides/texte.txt`, et regarde chaque
   `slides/page-XX.png` avec l'outil Read (ce sont des images) pour capter les schémas,
   graphes et formules que le texte extrait ne rend pas bien.
4. Copie `latex/preambule.tex` (dans ce projet) vers `~/Cours/$ARGUMENTS/preambule.tex`.
5. Écris `~/Cours/$ARGUMENTS/fiche.tex` : fiche de révision concise en anglais, structurée
   par concept clé, définitions en boîte `definition`, formules importantes mises en avant.
   Voir `CLAUDE.md` (section "Conventions LaTeX") pour le détail du style attendu.
6. Écris `~/Cours/$ARGUMENTS/exercices.tex` : 4 à 6 exercices progressifs testant la
   compréhension (pas du par-cœur), tous les énoncés d'abord, puis après `\newpage` une
   section "Corrections" avec les corrigés détaillés en boîte `correction`.
7. Compile les deux fichiers avec `pdflatex` depuis `~/Cours/$ARGUMENTS/` (deux passes) pour
   produire `fiche.pdf` et `exercices.pdf`. Si la compilation échoue, corrige le `.tex` et
   recompile plutôt que d'abandonner.
8. Termine par un résumé court : titre du cours, nombre d'exercices générés, et confirmation
   que `fiche.pdf`/`exercices.pdf` sont bien présents dans le dossier.
