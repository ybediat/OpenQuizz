"""Petits outils partagés par les écrans."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QWidget)

DOSSIER_INTERFACE = Path(__file__).resolve().parent


# Police par défaut de l'application (lisibilité, utile notamment en cas de dyslexie)
POLICE_PAR_DEFAUT = "Lexend"


def charger_polices(dossier: Path) -> set[str]:
    """Enregistre auprès de Qt toutes les polices .ttf / .otf du dossier
    (static/), sans les installer sur Windows. Retourne les familles chargées."""
    familles = set()
    if not dossier.is_dir():
        return familles
    for fichier in sorted(dossier.iterdir()):
        if fichier.suffix.casefold() in (".ttf", ".otf"):
            ident = QFontDatabase.addApplicationFont(str(fichier))
            if ident != -1:
                familles.update(QFontDatabase.applicationFontFamilies(ident))
    return familles


def appliquer_police(app: QApplication, familles: set[str]):
    """Lexend devient la police de base si elle a été chargée.
    Le thème QSS peut la préciser ou la remplacer."""
    if POLICE_PAR_DEFAUT in familles:
        police = QFont(POLICE_PAR_DEFAUT, 11)
        police.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        app.setFont(police)


def appliquer_theme(app: QApplication):
    """Charge interface/theme.qss. Tout le style visuel vit dans ce fichier,
    pour pouvoir changer le design sans toucher au code des écrans."""
    chemin = DOSSIER_INTERFACE / "theme.qss"
    if chemin.is_file():
        qss = chemin.read_text(encoding="utf-8")
        # @INTERFACE@ dans le thème = ce dossier (pour les images comme coche.svg)
        qss = qss.replace("@INTERFACE@", DOSSIER_INTERFACE.as_posix())
        app.setStyleSheet(qss)


def definir_etat(widget: QWidget, etat: str | None):
    """Pose la propriété dynamique « etat » (juste / faux / accent / vide)
    utilisée par le thème, puis force Qt à recalculer le style."""
    widget.setProperty("etat", etat or "")
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def etiquette(texte: str = "", nom_objet: str = "", retour_ligne: bool = True) -> QLabel:
    """QLabel avec un objectName (pour le thème) et retour à la ligne."""
    label = QLabel(texte)
    if nom_objet:
        label.setObjectName(nom_objet)
    label.setWordWrap(retour_ligne)
    return label


def bouton(texte: str, nom_objet: str = "", rappel=None) -> QPushButton:
    b = QPushButton(texte)
    if nom_objet:
        b.setObjectName(nom_objet)
    if rappel:
        b.clicked.connect(rappel)
    return b


def vider_layout(layout):
    """Supprime récursivement tous les widgets d'un layout."""
    while layout.count():
        element = layout.takeAt(0)
        if element.widget():
            # hide() immédiat : deleteLater() n'agit qu'au retour dans la boucle Qt
            element.widget().hide()
            element.widget().deleteLater()
        elif element.layout():
            vider_layout(element.layout())


class ClavierSpecial(QWidget):
    """Rangée de boutons pour taper les caractères spéciaux du cursus
    (ò, è, à...) dans le dernier champ de saisie utilisé."""

    def __init__(self, caracteres: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("clavierSpecial")
        self.cible: QLineEdit | None = None
        self._champs: list[QLineEdit] = []
        QApplication.instance().focusChanged.connect(self._focus_change)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for c in caracteres:
            b = bouton(c, "toucheSpeciale", lambda _=False, c=c: self._inserer(c))
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # ne pas voler le focus au champ
            layout.addWidget(b)
        layout.addStretch()

    def suivre(self, champ: QLineEdit):
        """Déclare un champ : il devient la cible quand il prend le focus."""
        self._champs.append(champ)
        if self.cible is None:
            self.cible = champ

    def _focus_change(self, _ancien, nouveau):
        if nouveau in self._champs:
            self.cible = nouveau

    def _inserer(self, caractere: str):
        if self.cible is not None and self.cible.isEnabled():
            self.cible.insert(caractere)
            self.cible.setFocus()
