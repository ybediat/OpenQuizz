"""Structures de données partagées par le moteur et l'interface.

Le moteur n'importe jamais PySide6 : ces classes sont de simples dataclasses.
"""

from dataclasses import dataclass, field
from pathlib import Path

# Types de questions gérés par le moteur
QCM = "qcm"
VRAI_FAUX = "vrai_faux"
TROUS = "trous"
SAISIE = "saisie"
TYPES_QUESTION = (QCM, VRAI_FAUX, TROUS, SAISIE)


@dataclass
class Lecon:
    titre: str
    texte: str


@dataclass
class Question:
    id: str
    type: str
    enonce: str
    explication: str = ""
    # qcm : liste des choix et index de la bonne réponse
    choix: list[str] = field(default_factory=list)
    bonne_reponse: object = None  # int (qcm) ou bool (vrai_faux)
    # trous : {"1": ["réponse", "variante"], ...}
    trous: dict[str, list[str]] = field(default_factory=dict)
    # saisie : réponses acceptées
    acceptees: list[str] = field(default_factory=list)
    tolerance_accents: str = "avertir"


@dataclass
class Quiz:
    id: str
    titre: str
    chemin: Path
    description: str = ""
    cursus: str = ""          # identifiant normalisé du cursus ("" = hors cursus)
    niveau: str = ""
    ordre: int = 0            # position dans le parcours du cursus
    tags: list[str] = field(default_factory=list)
    lecon: Lecon | None = None
    questions: list[Question] = field(default_factory=list)
    melanger_questions: bool = False
    melanger_choix: bool = True
    # Rempli quand le fichier est invalide : le quiz est listé mais grisé
    erreurs: list[str] = field(default_factory=list)

    @property
    def valide(self) -> bool:
        return not self.erreurs


@dataclass
class Cursus:
    id: str
    titre: str
    description: str = ""
    # Caractères proposés sous les champs de saisie (ex. ò, è, à)
    caracteres_speciaux: list[str] = field(default_factory=list)


@dataclass
class Correction:
    statut: str               # juste / accent / faux (cf. normalisation)
    reponse_attendue: str     # texte lisible de la bonne réponse
    explication: str = ""
    remarque: str = ""        # ex. « attention à l'accent : mèsi »
    # trous : statut de chaque trou {"1": "juste", "2": "faux"}
    detail: dict[str, str] = field(default_factory=dict)
    # Joker : la leçon a été consultée, la question compte comme fausse.
    # statut_reel garde ce qu'aurait donné la réponse sans joker.
    joker: bool = False
    statut_reel: str = ""

    @property
    def est_juste(self) -> bool:
        return self.statut != "faux"


@dataclass
class ResultatQuestion:
    question: Question
    reponse_donnee: object
    reponse_lisible: str
    correction: Correction


@dataclass
class Bilan:
    quiz: Quiz
    resultats: list[ResultatQuestion]

    @property
    def score(self) -> int:
        return sum(1 for r in self.resultats if r.correction.est_juste)

    @property
    def total(self) -> int:
        return len(self.resultats)

    @property
    def erreurs(self) -> list[ResultatQuestion]:
        return [r for r in self.resultats if not r.correction.est_juste]

    @property
    def jokers(self) -> int:
        return sum(1 for r in self.resultats if r.correction.joker)

    @property
    def avertissements(self) -> list[ResultatQuestion]:
        return [r for r in self.resultats if r.correction.statut == "accent"]
