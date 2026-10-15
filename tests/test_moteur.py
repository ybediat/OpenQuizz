"""Tests du moteur. Lancer depuis la racine : python -m unittest"""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from moteur.chargeur import charger_quiz, decouvrir
from moteur.normalisation import ACCENT, FAUX, JUSTE, comparer, identifiant, normaliser
from moteur.session import SessionQuiz
from moteur.stockage import Stockage, format_date

RACINE = Path(__file__).resolve().parent.parent


class TestNormalisation(unittest.TestCase):
    def test_espaces_casse_apostrophes(self):
        self.assertEqual(normaliser("  Mèsi  ANPIL ! "), "mèsi anpil")
        self.assertEqual(normaliser("M’ap vini"), "m'ap vini")

    def test_unicode_compose(self):
        # « ò » écrit en un caractère ou en o + accent combinant
        self.assertEqual(normaliser("krèyòl"), normaliser("krèyòl"))

    def test_identifiant(self):
        self.assertEqual(identifiant(" Haïtien "), "haitien")
        self.assertEqual(identifiant("Vrai / Faux"), "vrai_faux")

    def test_tolerance_accents(self):
        self.assertEqual(comparer("mesi", ["mèsi"], "avertir")[0], ACCENT)
        self.assertEqual(comparer("mesi", ["mèsi"], "accepter")[0], JUSTE)
        self.assertEqual(comparer("mesi", ["mèsi"], "refuser")[0], FAUX)
        self.assertEqual(comparer("", ["mèsi"])[0], FAUX)


class TestChargeur(unittest.TestCase):
    def test_quiz_fournis_valides(self):
        cursus, quiz = decouvrir(RACINE / "quiz")
        self.assertIn("haitien", cursus)
        for q in quiz:
            self.assertTrue(q.valide, f"{q.chemin.name} : {q.erreurs}")

    def test_fichier_invalide_ne_plante_pas(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = Path(d) / "casse.json"
            chemin.write_text("{ pas du json", encoding="utf-8")
            self.assertFalse(charger_quiz(chemin).valide)
            chemin.write_text(json.dumps({"questions": [{"type": "inconnu"}]}), encoding="utf-8")
            self.assertFalse(charger_quiz(chemin).valide)


class TestSession(unittest.TestCase):
    def test_partie_complete(self):
        quiz = charger_quiz(RACINE / "quiz" / "haitien" / "01-salutations.json")
        s = SessionQuiz(quiz, graine=1)
        while not s.terminee:
            q = s.question_courante()
            # On répond juste à tout, sans accent pour les saisies
            reponse = {"qcm": q.bonne_reponse, "vrai_faux": q.bonne_reponse,
                       "saisie": "mesi anpil",
                       "trous": {k: v[0] for k, v in q.trous.items()}}[q.type]
            s.repondre(reponse)
            s.suivante()
        bilan = s.bilan()
        self.assertEqual(bilan.score, bilan.total)
        self.assertEqual(len(bilan.avertissements), 1)


class TestJoker(unittest.TestCase):
    def test_joker_compte_faux(self):
        quiz = charger_quiz(RACINE / "quiz" / "haitien" / "03-nombres.json")
        s = SessionQuiz(quiz, graine=1)
        q = s.question_courante()
        if q.type == "saisie":
            bonne = q.acceptees[0]
        elif q.type == "trous":
            bonne = {k: v[0] for k, v in q.trous.items()}
        else:
            bonne = q.bonne_reponse
        c = s.repondre(bonne, joker=True)
        self.assertTrue(c.joker)
        self.assertEqual((c.statut, c.statut_reel), (FAUX, JUSTE))
        self.assertEqual((s.bilan().score, s.bilan().jokers), (0, 1))


class TestStockage(unittest.TestCase):
    def test_profils_et_resultats(self):
        with tempfile.TemporaryDirectory() as d:
            st = Stockage(Path(d) / "test.db")
            p = st.creer_profil("Yannis", ["Haïtien"])
            self.assertEqual(p.cursus, ["haitien"])
            with self.assertRaises(ValueError):
                st.creer_profil(" yannis ", [])
            quiz = charger_quiz(RACINE / "quiz" / "haitien" / "03-nombres.json")
            s = SessionQuiz(quiz)
            s.repondre(None)
            st.enregistrer(p.id, s.bilan(), s.debut, datetime.now())
            res = st.derniers_resultats(p.id)[quiz.id]
            self.assertEqual((res.score, res.total, res.nb_parties), (0, 1, 1))
            self.assertEqual(res.date, format_date(datetime.now()))
            st.fermer()


if __name__ == "__main__":
    unittest.main()
