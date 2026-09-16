"""Point d'entrée pour le bundle py2app (Contents/MacOS/launcher).

py2app a besoin d'un script au niveau racine comme point d'entrée ; on
délègue immédiatement à app.main pour ne rien dupliquer.
"""

from app.main import main

if __name__ == "__main__":
    main()
