"""Point d'entrée d'OpenQuizz : python main.py"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from interface.app import FenetrePrincipale
from interface.commun import appliquer_police, appliquer_theme, charger_polices

RACINE = Path(__file__).resolve().parent
DOSSIER_QUIZ = RACINE / "quiz"
DOSSIER_POLICES = RACINE / "static"
# Base des profils et résultats, à côté du programme (ignorée par git)
FICHIER_DONNEES = RACINE / "donnees" / "openquizz.db"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("OpenQuizz")
    # Polices d'abord : le thème peut ensuite y faire référence par leur nom
    appliquer_police(app, charger_polices(DOSSIER_POLICES))
    appliquer_theme(app)
    fenetre = FenetrePrincipale(DOSSIER_QUIZ, FICHIER_DONNEES)
    fenetre.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
