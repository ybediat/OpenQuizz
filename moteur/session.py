"""Déroulement d'un quiz : ordre des questions, correction, bilan."""

import copy
import random
from datetime import datetime

from .modeles import (QCM, SAISIE, TROUS, VRAI_FAUX, Bilan, Correction,
                      Question, Quiz, ResultatQuestion)
from .normalisation import ACCENT, FAUX, JUSTE, comparer


class SessionQuiz:
    """Une partie en cours. L'interface appelle question_courante(),
    repondre(), puis suivante() jusqu'à ce que terminee soit vrai."""

    def __init__(self, quiz: Quiz, graine: int | None = None):
        self.quiz = quiz
        self.debut = datetime.now()
        self.fin: datetime | None = None
        self._rng = random.Random(graine)
        # Copie des questions pour pouvoir mélanger sans toucher au quiz chargé
        self.questions = [copy.deepcopy(q) for q in quiz.questions]
        if quiz.melanger_questions:
            self._rng.shuffle(self.questions)
        if quiz.melanger_choix:
            for q in self.questions:
                if q.type == QCM:
                    self._melanger_choix(q)
        self.index = 0
        self.resultats: list[ResultatQuestion] = []

    def _melanger_choix(self, q: Question):
        bon = q.choix[q.bonne_reponse]
        self._rng.shuffle(q.choix)
        q.bonne_reponse = q.choix.index(bon)

    # --- Navigation -------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self.questions)

    @property
    def terminee(self) -> bool:
        return self.index >= self.total

    def question_courante(self) -> Question | None:
        return None if self.terminee else self.questions[self.index]

    def suivante(self):
        self.index += 1
        if self.terminee and self.fin is None:
            self.fin = datetime.now()

    # --- Correction -------------------------------------------------------

    def repondre(self, reponse, joker: bool = False) -> Correction:
        """Corrige la réponse à la question courante et l'enregistre.

        Format de `reponse` selon le type :
          qcm       -> index du choix (int) ou None
          vrai_faux -> bool ou None
          trous     -> {"1": "texte", "2": "texte"}
          saisie    -> texte
        joker : la leçon a été consultée pendant la question, qui compte
        alors comme fausse quelle que soit la réponse.
        """
        q = self.question_courante()
        correction, lisible = corriger(q, reponse)
        if joker:
            correction.joker = True
            correction.statut_reel = correction.statut
            correction.statut = FAUX
        self.resultats.append(ResultatQuestion(q, reponse, lisible, correction))
        return correction

    def bilan(self) -> Bilan:
        return Bilan(quiz=self.quiz, resultats=list(self.resultats))


def corriger(q: Question, reponse) -> tuple[Correction, str]:
    """Retourne (correction, réponse donnée sous forme lisible)."""
    if q.type == QCM:
        attendu = q.choix[q.bonne_reponse]
        donnee = q.choix[reponse] if isinstance(reponse, int) and 0 <= reponse < len(q.choix) else ""
        statut = JUSTE if reponse == q.bonne_reponse else FAUX
        return Correction(statut, attendu, q.explication), donnee

    if q.type == VRAI_FAUX:
        texte = {True: "Vrai", False: "Faux", None: ""}
        statut = JUSTE if reponse is not None and reponse == q.bonne_reponse else FAUX
        return Correction(statut, texte[q.bonne_reponse], q.explication), texte.get(reponse, "")

    if q.type == SAISIE:
        statut, attendu = comparer(reponse, q.acceptees, q.tolerance_accents)
        correction = Correction(statut, attendu, q.explication)
        if statut == ACCENT:
            correction.remarque = f"Attention aux accents : on écrit « {attendu} »."
        return correction, str(reponse or "")

    if q.type == TROUS:
        reponse = reponse or {}
        detail, phrase_attendue, phrase_donnee = {}, q.enonce, q.enonce
        accents = []
        for cle, acceptees in q.trous.items():
            saisie = reponse.get(cle, "")
            statut, attendu = comparer(saisie, acceptees, q.tolerance_accents)
            detail[cle] = statut
            if statut == ACCENT:
                accents.append(attendu)
            phrase_attendue = phrase_attendue.replace("{" + cle + "}", attendu)
            phrase_donnee = phrase_donnee.replace("{" + cle + "}", saisie.strip() or "…")
        if FAUX in detail.values():
            statut = FAUX
        elif ACCENT in detail.values():
            statut = ACCENT
        else:
            statut = JUSTE
        correction = Correction(statut, phrase_attendue, q.explication, detail=detail)
        if accents:
            correction.remarque = "Attention aux accents : " + ", ".join(f"« {a} »" for a in accents) + "."
        return correction, phrase_donnee

    raise ValueError(f"type de question inconnu : {q.type}")
