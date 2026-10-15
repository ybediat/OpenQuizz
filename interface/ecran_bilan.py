"""Bilan de fin de quiz : score, erreurs et remarques d'orthographe."""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from moteur.modeles import TROUS, VRAI_FAUX, Bilan, ResultatQuestion
from moteur.stockage import format_date

from .commun import bouton, definir_etat, etiquette, vider_layout


def _message(ratio: float) -> str:
    if ratio == 1:
        return "Parfait, rien à redire !"
    if ratio >= 0.8:
        return "Très bien, encore un petit effort."
    if ratio >= 0.5:
        return "C'est en bonne voie. Relis les corrections ci-dessous."
    return "Pas de panique : relis la leçon et retente ta chance."


class EcranBilan(QWidget):
    recommencer = Signal()
    retour = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.titre = etiquette("", "texteDiscret")
        layout.addWidget(self.titre)
        self.score = etiquette("", "scoreGeant")
        self.score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.score)
        self.message = etiquette("", "sousTitre")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message)

        contenu = QWidget()
        self.liste = QVBoxLayout(contenu)
        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QFrame.Shape.NoFrame)
        defilement.setWidget(contenu)
        layout.addWidget(defilement, 1)

        bas = QHBoxLayout()
        bas.addWidget(bouton("Retour à la liste", "boutonDiscret", self.retour.emit))
        bas.addStretch()
        bas.addWidget(bouton("Recommencer", "boutonPrincipal", self.recommencer.emit))
        layout.addLayout(bas)

    def afficher(self, bilan: Bilan, date: datetime):
        jokers = f" · {bilan.jokers} joker{'s' if bilan.jokers > 1 else ''}" if bilan.jokers else ""
        self.titre.setText(f"{bilan.quiz.titre} · {format_date(date)}{jokers}")
        self.score.setText(f"{bilan.score} / {bilan.total}")
        self.message.setText(_message(bilan.score / bilan.total if bilan.total else 0))

        vider_layout(self.liste)
        if bilan.erreurs:
            self.liste.addWidget(etiquette(f"Erreurs ({len(bilan.erreurs)})", "titreSection"))
            for r in bilan.erreurs:
                self.liste.addWidget(self._carte(r, "joker" if r.correction.joker else "faux"))
        if bilan.avertissements:
            self.liste.addWidget(etiquette("Attention à l'orthographe", "titreSection"))
            for r in bilan.avertissements:
                self.liste.addWidget(self._carte(r, "accent"))
        self.liste.addStretch()

    def _carte(self, r: ResultatQuestion, etat: str) -> QFrame:
        carte = QFrame()
        carte.setObjectName("carteErreur")
        definir_etat(carte, etat)
        cl = QVBoxLayout(carte)
        q = r.question
        enonce = "Complète la phrase" if q.type == TROUS else q.enonce
        if q.type == VRAI_FAUX:
            enonce = f"Vrai ou faux : {q.enonce}"
        cl.addWidget(etiquette(enonce, "enonceBilan"))
        cl.addWidget(etiquette(f"Ta réponse : {r.reponse_lisible or '(vide)'}", "texteCarte"))
        cl.addWidget(etiquette(f"Bonne réponse : {r.correction.reponse_attendue}", "texteCarte"))
        if r.correction.joker:
            juste = "juste" if r.correction.statut_reel != "faux" else "fausse"
            cl.addWidget(etiquette(f"Joker utilisé (ta réponse était {juste})", "texteDiscret"))
        for complement in (r.correction.remarque, r.correction.explication):
            if complement:
                cl.addWidget(etiquette(complement, "texteDiscret"))
        return carte
