"""Affichage de la leçon avant le quiz."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QScrollArea,
                               QVBoxLayout, QWidget)

from moteur.modeles import Quiz

from .commun import bouton, etiquette


class EcranLecon(QWidget):
    commencer = Signal()
    retour = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.quiz_titre = etiquette("", "texteDiscret")
        layout.addWidget(self.quiz_titre)

        carte = QFrame()
        carte.setObjectName("carte")
        cl = QVBoxLayout(carte)
        self.titre = etiquette("", "titreCarte")
        self.texte = etiquette("", "texteLecon")
        self.texte.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.texte.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        cl.addWidget(self.titre)
        cl.addWidget(self.texte, 1)

        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QFrame.Shape.NoFrame)
        defilement.setWidget(carte)
        layout.addWidget(defilement, 1)

        bas = QHBoxLayout()
        bas.addWidget(bouton("Retour", "boutonDiscret", self.retour.emit))
        bas.addStretch()
        self.bouton_go = bouton("Commencer le quiz", "boutonPrincipal", self.commencer.emit)
        bas.addWidget(self.bouton_go)
        layout.addLayout(bas)

    def afficher(self, quiz: Quiz):
        self.quiz_titre.setText(quiz.titre)
        self.titre.setText(quiz.lecon.titre)
        self.texte.setText(quiz.lecon.texte)
        self.bouton_go.setFocus()


class FenetreLecon(QDialog):
    """Leçon affichée dans une fenêtre à part pendant les questions (joker).
    Non modale : on peut répondre tout en la lisant."""

    def __init__(self, quiz: Quiz, parent=None):
        super().__init__(parent)
        self.setObjectName("fenetreLecon")
        self.setWindowTitle(f"Joker · {quiz.lecon.titre}")
        self.setModal(False)
        self.resize(420, 480)
        layout = QVBoxLayout(self)
        titre = etiquette(quiz.lecon.titre, "titreCarte")
        texte = etiquette(quiz.lecon.texte, "texteLecon")
        texte.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        texte.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        contenu = QFrame()
        contenu.setObjectName("carte")
        cl = QVBoxLayout(contenu)
        cl.addWidget(titre)
        cl.addWidget(texte, 1)
        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QFrame.Shape.NoFrame)
        defilement.setWidget(contenu)
        layout.addWidget(defilement, 1)
        layout.addWidget(bouton("Fermer", "boutonPrincipal", self.close),
                         alignment=Qt.AlignmentFlag.AlignRight)

    def afficher_a_cote(self, fenetre: QWidget):
        """Place la leçon à droite de la fenêtre principale si l'écran le permet."""
        cadre = fenetre.frameGeometry()
        ecran = fenetre.screen().availableGeometry()
        x = cadre.right() + 8
        if x + self.width() > ecran.right():
            x = max(ecran.left(), ecran.right() - self.width())
        self.move(x, cadre.top())
        self.show()
        self.raise_()
