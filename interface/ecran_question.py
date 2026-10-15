"""Écran de question : un rendu par type, validation puis correction."""

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLineEdit,
                               QMessageBox, QProgressBar, QRadioButton,
                               QVBoxLayout, QWidget)

from moteur.modeles import QCM, SAISIE, TROUS, VRAI_FAUX, Correction, Question
from moteur.session import SessionQuiz

from .commun import ClavierSpecial, bouton, definir_etat, etiquette, vider_layout
from .ecran_lecon import FenetreLecon

_MOTIF_TROU = re.compile(r"\{([^{}]+)\}")

_TITRES_FEEDBACK = {
    "juste": "Bonne réponse !",
    "accent": "Bonne réponse, mais attention à l'orthographe",
    "faux": "Ce n'est pas ça",
    "joker": "Joker utilisé : question comptée fausse",
}


class EcranQuestion(QWidget):
    termine = Signal()     # toutes les questions ont été vues
    abandon = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session: SessionQuiz | None = None
        self.caracteres: list[str] = []
        self.corrige = False
        # Widgets de réponse de la question courante
        self.groupe: QButtonGroup | None = None
        self.champs: dict[str, QLineEdit] = {}
        # Joker : leçon consultée pendant la question courante
        self.joker_utilise = False
        self.fenetre_lecon: FenetreLecon | None = None

        layout = QVBoxLayout(self)

        haut = QHBoxLayout()
        self.titre_quiz = etiquette("", "texteDiscret")
        self.compteur = etiquette("", "texteDiscret", retour_ligne=False)
        haut.addWidget(self.titre_quiz, 1)
        haut.addWidget(self.compteur)
        layout.addLayout(haut)
        self.progression = QProgressBar()
        self.progression.setObjectName("progression")
        self.progression.setTextVisible(False)
        layout.addWidget(self.progression)

        carte = QFrame()
        carte.setObjectName("carte")
        self.carte_layout = QVBoxLayout(carte)
        self.enonce = etiquette("", "enonce")
        self.carte_layout.addWidget(self.enonce)
        self.zone_reponse = QVBoxLayout()
        self.carte_layout.addLayout(self.zone_reponse)
        self.carte_layout.addStretch()
        layout.addWidget(carte, 1)

        # Bandeau de correction (coloré selon la propriété « etat »)
        self.feedback = QFrame()
        self.feedback.setObjectName("feedback")
        fl = QVBoxLayout(self.feedback)
        self.feedback_titre = etiquette("", "feedbackTitre")
        self.feedback_texte = etiquette("", "feedbackTexte")
        fl.addWidget(self.feedback_titre)
        fl.addWidget(self.feedback_texte)
        layout.addWidget(self.feedback)

        bas = QHBoxLayout()
        bas.addWidget(bouton("Abandonner", "boutonDiscret", self._abandonner))
        self.bouton_joker = bouton("Joker : voir la leçon", "boutonJoker", self._joker)
        self.bouton_joker.setToolTip("Affiche la leçon, mais la question sera comptée fausse.")
        bas.addWidget(self.bouton_joker)
        self.indice = etiquette("", "texteDiscret")
        bas.addWidget(self.indice, 1)
        self.bouton_action = bouton("Valider", "boutonPrincipal", self._action)
        bas.addWidget(self.bouton_action)
        layout.addLayout(bas)

        # Entrée = Valider puis Suivant
        for touche in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            QShortcut(QKeySequence(touche), self, self._action)

    # --- Cycle de vie -----------------------------------------------------

    def demarrer(self, session: SessionQuiz, caracteres_speciaux: list[str]):
        self.session = session
        self.caracteres = caracteres_speciaux
        self.titre_quiz.setText(session.quiz.titre)
        self._fermer_lecon()
        self.fenetre_lecon = FenetreLecon(session.quiz, self.window()) if session.quiz.lecon else None
        self.progression.setMaximum(session.total)
        self._afficher_question()

    def _afficher_question(self):
        q = self.session.question_courante()
        self.corrige = False
        self.compteur.setText(f"Question {self.session.index + 1} / {self.session.total}")
        self.progression.setValue(self.session.index)
        self.feedback.hide()
        self.indice.setText("")
        self.bouton_action.setText("Valider")
        # Nouvelle question : la leçon se referme et le joker redevient disponible
        self.joker_utilise = False
        if self.fenetre_lecon:
            self.fenetre_lecon.close()
        self.bouton_joker.setText("Joker : voir la leçon")
        self.bouton_joker.setVisible(self.fenetre_lecon is not None)
        self.bouton_joker.setEnabled(True)

        vider_layout(self.zone_reponse)
        self.groupe, self.champs = None, {}
        if q.type == QCM:
            self.enonce.setText(q.enonce)
            self._construire_choix(q.choix)
        elif q.type == VRAI_FAUX:
            self.enonce.setText(f"Vrai ou faux ?\n\n{q.enonce}")
            self._construire_choix(["Vrai", "Faux"])
        elif q.type == TROUS:
            self.enonce.setText("Complète :")
            self._construire_trous(q)
        elif q.type == SAISIE:
            self.enonce.setText(q.enonce)
            champ = QLineEdit()
            champ.setObjectName("champReponse")
            champ.setPlaceholderText("Ta réponse")
            self.champs["reponse"] = champ
            self.zone_reponse.addWidget(champ)
            champ.setFocus()
        if self.champs and self.caracteres:
            clavier = ClavierSpecial(self.caracteres)
            for champ in self.champs.values():
                clavier.suivre(champ)
            self.zone_reponse.addWidget(clavier)
        if self.champs:
            next(iter(self.champs.values())).setFocus()

    def _construire_choix(self, choix: list[str]):
        self.groupe = QButtonGroup(self)
        for i, texte in enumerate(choix):
            radio = QRadioButton(texte)
            radio.setObjectName("choix")
            self.groupe.addButton(radio, i)
            self.zone_reponse.addWidget(radio)

    def _construire_trous(self, q: Question):
        """Une ligne de widgets par ligne d'énoncé : textes et champs alternés."""
        for ligne in q.enonce.split("\n"):
            rangee = QHBoxLayout()
            position = 0
            for m in _MOTIF_TROU.finditer(ligne):
                if m.start() > position:
                    rangee.addWidget(etiquette(ligne[position:m.start()], "texteTrou", False))
                cle = m.group(1).strip()
                champ = QLineEdit()
                champ.setObjectName("champTrou")
                champ.setFixedWidth(140)
                self.champs[cle] = champ
                rangee.addWidget(champ)
                position = m.end()
            if position < len(ligne):
                rangee.addWidget(etiquette(ligne[position:], "texteTrou", False))
            rangee.addStretch()
            self.zone_reponse.addLayout(rangee)

    # --- Actions ----------------------------------------------------------

    def _action(self):
        if self.session is None or self.session.terminee:
            return
        if self.corrige:
            self.session.suivante()
            if self.session.terminee:
                self._fermer_lecon()
                self.termine.emit()
            else:
                self._afficher_question()
        else:
            self._valider()

    def _lire_reponse(self, q: Question):
        """Retourne la réponse au format attendu par le moteur, ou None si vide."""
        if q.type in (QCM, VRAI_FAUX):
            i = self.groupe.checkedId()
            if i < 0:
                return None
            return i if q.type == QCM else (i == 0)
        if q.type == SAISIE:
            texte = self.champs["reponse"].text()
            return texte if texte.strip() else None
        if q.type == TROUS:
            reponse = {cle: champ.text() for cle, champ in self.champs.items()}
            return reponse if any(v.strip() for v in reponse.values()) else None

    def _valider(self):
        q = self.session.question_courante()
        reponse = self._lire_reponse(q)
        if reponse is None:
            self.indice.setText("Réponds avant de valider.")
            return
        self.indice.setText("")
        correction = self.session.repondre(reponse, joker=self.joker_utilise)
        self.corrige = True
        if not self.joker_utilise:
            self.bouton_joker.setEnabled(False)
        self._montrer_correction(q, correction)
        dernier = self.session.index + 1 >= self.session.total
        self.bouton_action.setText("Voir le bilan" if dernier else "Suivant")
        self.bouton_action.setFocus()

    def _montrer_correction(self, q: Question, c: Correction):
        # Fige les réponses et colore les éléments justes / faux
        if self.groupe:
            for b in self.groupe.buttons():
                b.setEnabled(False)
            bonne = q.bonne_reponse if q.type == QCM else (0 if q.bonne_reponse else 1)
            definir_etat(self.groupe.button(bonne), "juste")
            choisi = self.groupe.checkedId()
            if choisi != bonne:
                definir_etat(self.groupe.button(choisi), "faux")
        for cle, champ in self.champs.items():
            champ.setReadOnly(True)
            etat = c.detail.get(cle, c.statut_reel or c.statut)
            definir_etat(champ, etat)

        lignes = []
        if c.joker:
            juste = "juste" if c.statut_reel != "faux" else "fausse"
            lignes.append(f"Ta réponse était {juste}.")
        if c.statut == "faux" or q.type == TROUS:
            lignes.append(f"Réponse attendue : {c.reponse_attendue}")
        if c.remarque:
            lignes.append(c.remarque)
        if c.explication:
            lignes.append(c.explication)
        etat = "joker" if c.joker else c.statut
        self.feedback_titre.setText(_TITRES_FEEDBACK[etat])
        self.feedback_texte.setText("\n".join(lignes))
        self.feedback_texte.setVisible(bool(lignes))
        definir_etat(self.feedback, etat)
        definir_etat(self.feedback_titre, etat)
        self.feedback.show()
        self.progression.setValue(self.session.index + 1)

    def _joker(self):
        """Premier clic : confirmation, puis la question est marquée « joker ».
        Clics suivants (même question) : réaffiche simplement la leçon."""
        if self.fenetre_lecon is None:
            return
        if not self.joker_utilise:
            reponse = QMessageBox.question(
                self, "Utiliser un joker",
                "Afficher la leçon ? Cette question sera comptée fausse.")
            if reponse != QMessageBox.StandardButton.Yes:
                return
            self.joker_utilise = True
            self.bouton_joker.setText("Revoir la leçon")
        self.fenetre_lecon.afficher_a_cote(self.window())

    def _fermer_lecon(self):
        if self.fenetre_lecon:
            self.fenetre_lecon.close()
            self.fenetre_lecon.deleteLater()
            self.fenetre_lecon = None

    def _abandonner(self):
        reponse = QMessageBox.question(self, "Abandonner",
                                       "Abandonner ce quiz ? Cette partie ne sera pas enregistrée.")
        if reponse == QMessageBox.StandardButton.Yes:
            self.session = None
            self._fermer_lecon()
            self.abandon.emit()
