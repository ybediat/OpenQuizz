"""Fenêtre principale : enchaîne les écrans profils > liste > leçon > questions > bilan."""

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from moteur.chargeur import decouvrir
from moteur.modeles import Quiz
from moteur.session import SessionQuiz
from moteur.stockage import Profil, Stockage

from .ecran_bilan import EcranBilan
from .ecran_lecon import EcranLecon
from .ecran_liste import EcranListe
from .ecran_profils import DialogueProfil, EcranProfils
from .ecran_question import EcranQuestion


class FenetrePrincipale(QMainWindow):
    def __init__(self, dossier_quiz: Path, fichier_donnees: Path):
        super().__init__()
        self.setWindowTitle("OpenQuizz")
        self.resize(960, 640)
        self.dossier_quiz = dossier_quiz
        self.stockage = Stockage(fichier_donnees)
        self.profil: Profil | None = None
        self.quiz_courant: Quiz | None = None
        self.session: SessionQuiz | None = None

        self.pile = QStackedWidget()
        self.setCentralWidget(self.pile)
        self.ecran_profils = EcranProfils(self.stockage)
        self.ecran_liste = EcranListe()
        self.ecran_lecon = EcranLecon()
        self.ecran_question = EcranQuestion()
        self.ecran_bilan = EcranBilan()
        for ecran in (self.ecran_profils, self.ecran_liste, self.ecran_lecon,
                      self.ecran_question, self.ecran_bilan):
            ecran.setObjectName("ecran")
            self.pile.addWidget(ecran)

        # Navigation
        self.ecran_profils.profil_choisi.connect(self._choisir_profil)
        self.ecran_liste.lancer.connect(self._ouvrir_quiz)
        self.ecran_liste.changer_profil.connect(self._aller_profils)
        self.ecran_liste.modifier_cursus.connect(self._modifier_cursus)
        self.ecran_liste.actualiser.connect(self._actualiser)
        self.ecran_lecon.commencer.connect(self._demarrer_questions)
        self.ecran_lecon.retour.connect(self._aller_liste)
        self.ecran_question.termine.connect(self._terminer)
        self.ecran_question.abandon.connect(self._aller_liste)
        self.ecran_bilan.recommencer.connect(lambda: self._ouvrir_quiz(self.quiz_courant))
        self.ecran_bilan.retour.connect(self._aller_liste)

        self._charger_quiz()
        self._aller_profils()

    def _charger_quiz(self):
        self.cursus, self.quiz = decouvrir(self.dossier_quiz)

    # --- Profils ----------------------------------------------------------

    def _aller_profils(self):
        self.ecran_profils.rafraichir(self.cursus)
        self.pile.setCurrentWidget(self.ecran_profils)

    def _choisir_profil(self, profil: Profil):
        self.profil = profil
        self._aller_liste()

    def _modifier_cursus(self):
        if DialogueProfil(self.stockage, self.cursus, self.profil, self).exec():
            # Relit le profil pour récupérer ses nouveaux cursus
            self.profil = next(p for p in self.stockage.lister_profils() if p.id == self.profil.id)
            self._aller_liste()

    # --- Liste des quiz ---------------------------------------------------

    def _actualiser(self):
        self._charger_quiz()
        self._aller_liste()

    def _aller_liste(self):
        resultats = self.stockage.derniers_resultats(self.profil.id)
        self.ecran_liste.afficher(self.profil, self.cursus, self.quiz, resultats)
        self.pile.setCurrentWidget(self.ecran_liste)

    # --- Déroulement d'un quiz -------------------------------------------

    def _ouvrir_quiz(self, quiz: Quiz):
        self.quiz_courant = quiz
        if quiz.lecon:
            self.ecran_lecon.afficher(quiz)
            self.pile.setCurrentWidget(self.ecran_lecon)
        else:
            self._demarrer_questions()

    def _demarrer_questions(self):
        self.session = SessionQuiz(self.quiz_courant)
        cursus = self.cursus.get(self.quiz_courant.cursus)
        caracteres = cursus.caracteres_speciaux if cursus else []
        self.ecran_question.demarrer(self.session, caracteres)
        self.pile.setCurrentWidget(self.ecran_question)

    def _terminer(self):
        bilan = self.session.bilan()
        self.stockage.enregistrer(self.profil.id, bilan, self.session.debut,
                                  self.session.fin or datetime.now())
        self.ecran_bilan.afficher(bilan, self.session.fin or datetime.now())
        self.pile.setCurrentWidget(self.ecran_bilan)

    def closeEvent(self, evenement):
        self.stockage.fermer()
        super().closeEvent(evenement)
