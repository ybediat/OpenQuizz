"""Profils, cursus suivis et historique des résultats (SQLite).

Les dates sont stockées au format ISO (tri fiable) et affichées en
DD/MM/YYYY via format_date().
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .modeles import Bilan
from .normalisation import identifiant, normaliser

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profils (
    id        INTEGER PRIMARY KEY,
    nom       TEXT NOT NULL,
    cree_le   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profil_cursus (
    profil_id INTEGER NOT NULL REFERENCES profils(id) ON DELETE CASCADE,
    cursus_id TEXT NOT NULL,
    PRIMARY KEY (profil_id, cursus_id)
);
CREATE TABLE IF NOT EXISTS sessions (
    id        INTEGER PRIMARY KEY,
    profil_id INTEGER NOT NULL REFERENCES profils(id) ON DELETE CASCADE,
    quiz_id   TEXT NOT NULL,
    debut     TEXT NOT NULL,
    fin       TEXT NOT NULL,
    score     INTEGER NOT NULL,
    total     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reponses (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    quiz_id     TEXT NOT NULL,
    question_id TEXT NOT NULL,
    reponse     TEXT,
    statut      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_profil ON sessions(profil_id, quiz_id);
CREATE INDEX IF NOT EXISTS idx_reponses_question ON reponses(quiz_id, question_id);
"""


def format_date(valeur) -> str:
    """Affiche une date (datetime ou chaîne ISO) au format DD/MM/YYYY."""
    if isinstance(valeur, str):
        valeur = datetime.fromisoformat(valeur)
    return valeur.strftime("%d/%m/%Y")


@dataclass
class Profil:
    id: int
    nom: str
    cree_le: str
    cursus: list[str] = field(default_factory=list)


@dataclass
class DernierResultat:
    score: int
    total: int
    date: str          # déjà formatée DD/MM/YYYY
    nb_parties: int


class Stockage:
    def __init__(self, chemin: Path):
        chemin.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(chemin)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(_SCHEMA)
        self.db.commit()

    def fermer(self):
        self.db.close()

    # --- Profils ----------------------------------------------------------

    def lister_profils(self) -> list[Profil]:
        profils = [Profil(r["id"], r["nom"], r["cree_le"])
                   for r in self.db.execute("SELECT * FROM profils ORDER BY nom COLLATE NOCASE")]
        for p in profils:
            p.cursus = self._cursus_du_profil(p.id)
        return profils

    def _cursus_du_profil(self, profil_id: int) -> list[str]:
        return [r["cursus_id"] for r in self.db.execute(
            "SELECT cursus_id FROM profil_cursus WHERE profil_id = ? ORDER BY cursus_id", (profil_id,))]

    def nom_existe(self, nom: str, sauf_id: int | None = None) -> bool:
        """Comparaison normalisée : « Yannis » et « yannis » sont le même nom."""
        cible = normaliser(nom)
        return any(normaliser(p.nom) == cible and p.id != sauf_id for p in self.lister_profils())

    def creer_profil(self, nom: str, cursus: list[str]) -> Profil:
        # split() sans argument coupe aussi sur les espaces insécables
        nom = " ".join(str(nom).split())
        if not nom:
            raise ValueError("Le nom du profil est vide.")
        if self.nom_existe(nom):
            raise ValueError(f"Le profil « {nom} » existe déjà.")
        cur = self.db.execute("INSERT INTO profils (nom, cree_le) VALUES (?, ?)",
                              (nom, datetime.now().isoformat(timespec="seconds")))
        self.definir_cursus(cur.lastrowid, cursus)
        return next(p for p in self.lister_profils() if p.id == cur.lastrowid)

    def definir_cursus(self, profil_id: int, cursus: list[str]):
        self.db.execute("DELETE FROM profil_cursus WHERE profil_id = ?", (profil_id,))
        self.db.executemany("INSERT OR IGNORE INTO profil_cursus VALUES (?, ?)",
                            [(profil_id, identifiant(c)) for c in cursus])
        self.db.commit()

    def supprimer_profil(self, profil_id: int):
        self.db.execute("DELETE FROM profils WHERE id = ?", (profil_id,))
        self.db.commit()

    # --- Résultats --------------------------------------------------------

    def enregistrer(self, profil_id: int, bilan: Bilan, debut: datetime, fin: datetime):
        cur = self.db.execute(
            "INSERT INTO sessions (profil_id, quiz_id, debut, fin, score, total) VALUES (?,?,?,?,?,?)",
            (profil_id, bilan.quiz.id, debut.isoformat(timespec="seconds"),
             fin.isoformat(timespec="seconds"), bilan.score, bilan.total))
        self.db.executemany(
            "INSERT INTO reponses (session_id, quiz_id, question_id, reponse, statut) VALUES (?,?,?,?,?)",
            [(cur.lastrowid, bilan.quiz.id, r.question.id,
              json.dumps(r.reponse_donnee, ensure_ascii=False),
              "joker" if r.correction.joker else r.correction.statut)
             for r in bilan.resultats])
        self.db.commit()

    def derniers_resultats(self, profil_id: int) -> dict[str, DernierResultat]:
        """Dernier score de chaque quiz pour un profil, indexé par quiz_id."""
        lignes = self.db.execute("""
            SELECT s.quiz_id, s.score, s.total, s.fin,
                   (SELECT COUNT(*) FROM sessions s2
                     WHERE s2.profil_id = s.profil_id AND s2.quiz_id = s.quiz_id) AS nb
            FROM sessions s
            WHERE s.profil_id = ?
              AND s.id = (SELECT MAX(id) FROM sessions s3
                           WHERE s3.profil_id = s.profil_id AND s3.quiz_id = s.quiz_id)
        """, (profil_id,))
        return {r["quiz_id"]: DernierResultat(r["score"], r["total"], format_date(r["fin"]), r["nb"])
                for r in lignes}
