"""Découverte et validation des quiz JSON.

Organisation attendue (libre, le dossier est parcouru récursivement) :

    quiz/
      haitien/
        cursus.json          -> déclare le cursus « haitien »
        01-salutations.json  -> un quiz, qui contient "cursus": "haitien"

Un fichier invalide ne fait jamais planter l'application : le quiz est
renvoyé avec la liste de ses erreurs, et l'interface l'affiche grisé.
"""

import json
from pathlib import Path

from .modeles import (QCM, SAISIE, TROUS, TYPES_QUESTION, VRAI_FAUX,
                      Cursus, Lecon, Question, Quiz)
from .normalisation import TOLERANCES, identifiant, normaliser

NOM_FICHIER_CURSUS = "cursus.json"
FORMATS_GERES = (1,)

# Plusieurs orthographes acceptées pour une même clé (après identifiant())
_ALIAS = {
    "accepte": "acceptees",
    "reponses": "acceptees",
    "reponses_acceptees": "acceptees",
    "reponse": "bonne_reponse",
    "question": "enonce",
    "choix_possibles": "choix",
    "explications": "explication",
    "tolerance": "tolerance_accents",
}


def _cles(donnees: dict) -> dict:
    """Normalise les clés d'un dictionnaire JSON (casse, accents, alias)."""
    resultat = {}
    for cle, valeur in donnees.items():
        cle_n = identifiant(cle)
        resultat[_ALIAS.get(cle_n, cle_n)] = valeur
    return resultat


def _lire_json(chemin: Path):
    # utf-8-sig : accepte les fichiers enregistrés avec un BOM (Bloc-notes)
    with open(chemin, encoding="utf-8-sig") as f:
        return json.load(f)


def _liste_textes(valeur) -> list[str]:
    """Accepte une chaîne seule ou une liste de chaînes."""
    if valeur is None:
        return []
    if isinstance(valeur, (list, tuple)):
        return [str(v) for v in valeur if str(v).strip()]
    return [str(valeur)] if str(valeur).strip() else []


def _booleen(valeur):
    """Interprète true/false/"vrai"/"faux"/"oui"/"non". None si illisible."""
    if isinstance(valeur, bool):
        return valeur
    mot = identifiant(valeur)
    if mot in ("vrai", "true", "oui", "yes", "v", "1"):
        return True
    if mot in ("faux", "false", "non", "no", "f", "0"):
        return False
    return None


def _lire_question(brut, position: int, erreurs: list[str]) -> Question | None:
    if not isinstance(brut, dict):
        erreurs.append(f"question n°{position} : ce n'est pas un objet JSON")
        return None
    d = _cles(brut)
    qid = str(d.get("id") or f"q{position}").strip()
    nom = f"question « {qid} »"
    type_q = identifiant(d.get("type", ""))
    if type_q not in TYPES_QUESTION:
        erreurs.append(f"{nom} : type « {d.get('type')} » inconnu "
                       f"(attendu : {', '.join(TYPES_QUESTION)})")
        return None

    enonce = str(d.get("enonce", "")).strip()
    if not enonce:
        erreurs.append(f"{nom} : énoncé manquant")

    tolerance = identifiant(d.get("tolerance_accents", "avertir")) or "avertir"
    if tolerance not in TOLERANCES:
        erreurs.append(f"{nom} : tolerance_accents doit valoir {', '.join(TOLERANCES)}")
        tolerance = "avertir"

    q = Question(id=qid, type=type_q, enonce=enonce,
                 explication=str(d.get("explication", "")).strip(),
                 tolerance_accents=tolerance)

    if type_q == QCM:
        q.choix = _liste_textes(d.get("choix"))
        if len(q.choix) < 2:
            erreurs.append(f"{nom} : un QCM demande au moins deux choix")
        bonne = d.get("bonne_reponse")
        if isinstance(bonne, bool) or bonne is None:
            erreurs.append(f"{nom} : bonne_reponse manquante")
        elif isinstance(bonne, int):
            # Index du bon choix (0 = premier)
            if not 0 <= bonne < len(q.choix):
                erreurs.append(f"{nom} : bonne_reponse {bonne} hors des choix")
            q.bonne_reponse = bonne
        else:
            # On accepte aussi le texte du bon choix
            cibles = [i for i, c in enumerate(q.choix) if normaliser(c) == normaliser(bonne)]
            if not cibles:
                erreurs.append(f"{nom} : « {bonne} » ne figure pas dans les choix")
            q.bonne_reponse = cibles[0] if cibles else 0

    elif type_q == VRAI_FAUX:
        q.bonne_reponse = _booleen(d.get("bonne_reponse"))
        if q.bonne_reponse is None:
            erreurs.append(f"{nom} : bonne_reponse doit valoir vrai ou faux")

    elif type_q == TROUS:
        trous = d.get("trous")
        if not isinstance(trous, dict) or not trous:
            erreurs.append(f"{nom} : champ « trous » manquant")
        else:
            q.trous = {str(k).strip(): _liste_textes(v) for k, v in trous.items()}
            for cle, acceptees in q.trous.items():
                if "{" + cle + "}" not in enonce:
                    erreurs.append(f"{nom} : le trou {{{cle}}} n'apparaît pas dans l'énoncé")
                if not acceptees:
                    erreurs.append(f"{nom} : aucune réponse pour le trou {{{cle}}}")

    elif type_q == SAISIE:
        q.acceptees = _liste_textes(d.get("acceptees"))
        if not q.acceptees:
            erreurs.append(f"{nom} : aucune réponse acceptée")

    return q


def charger_quiz(chemin: Path) -> Quiz:
    """Lit un fichier de quiz. Ne lève jamais d'exception : voir Quiz.erreurs."""
    quiz = Quiz(id=chemin.stem, titre=chemin.stem, chemin=chemin)
    try:
        brut = _lire_json(chemin)
    except (OSError, UnicodeDecodeError) as e:
        quiz.erreurs.append(f"fichier illisible : {e}")
        return quiz
    except json.JSONDecodeError as e:
        quiz.erreurs.append(f"JSON invalide ligne {e.lineno}, colonne {e.colno} : {e.msg}")
        return quiz
    if not isinstance(brut, dict):
        quiz.erreurs.append("le fichier doit contenir un objet JSON { ... }")
        return quiz

    d = _cles(brut)
    fmt = d.get("format", 1)
    if fmt not in FORMATS_GERES:
        quiz.erreurs.append(f"format {fmt} non géré par cette version")

    quiz.id = identifiant(d.get("id") or chemin.stem)
    quiz.titre = str(d.get("titre") or chemin.stem).strip()
    quiz.description = str(d.get("description", "")).strip()
    quiz.cursus = identifiant(d.get("cursus", ""))
    quiz.niveau = str(d.get("niveau", "")).strip()
    quiz.tags = _liste_textes(d.get("tags"))
    quiz.melanger_questions = bool(d.get("melanger_questions", False))
    quiz.melanger_choix = bool(d.get("melanger_choix", True))
    try:
        quiz.ordre = int(d.get("ordre", 0))
    except (TypeError, ValueError):
        quiz.erreurs.append("« ordre » doit être un nombre entier")

    lecon = d.get("lecon")
    if isinstance(lecon, dict):
        l = _cles(lecon)
        texte = l.get("texte", "")
        if isinstance(texte, list):  # permet d'écrire la leçon ligne par ligne
            texte = "\n".join(str(t) for t in texte)
        quiz.lecon = Lecon(titre=str(l.get("titre", quiz.titre)), texte=str(texte))
    elif isinstance(lecon, str) and lecon.strip():
        quiz.lecon = Lecon(titre=quiz.titre, texte=lecon)

    questions = d.get("questions")
    if not isinstance(questions, list) or not questions:
        quiz.erreurs.append("aucune question")
        questions = []
    vus = set()
    for i, brut_q in enumerate(questions, start=1):
        q = _lire_question(brut_q, i, quiz.erreurs)
        if q is None:
            continue
        if q.id in vus:
            quiz.erreurs.append(f"identifiant de question « {q.id} » en double")
        vus.add(q.id)
        quiz.questions.append(q)
    return quiz


def charger_cursus(chemin: Path) -> Cursus | None:
    try:
        d = _cles(_lire_json(chemin))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return None
    cid = identifiant(d.get("id") or chemin.parent.name)
    return Cursus(id=cid,
                  titre=str(d.get("titre") or cid),
                  description=str(d.get("description", "")),
                  caracteres_speciaux=_liste_textes(d.get("caracteres_speciaux")))


def decouvrir(dossier: Path) -> tuple[dict[str, Cursus], list[Quiz]]:
    """Parcourt le dossier des quiz. Retourne (cursus par id, liste des quiz)."""
    cursus: dict[str, Cursus] = {}
    quiz: list[Quiz] = []
    if not dossier.is_dir():
        return cursus, quiz

    for chemin in sorted(dossier.rglob("*.json")):
        if identifiant(chemin.name) == identifiant(NOM_FICHIER_CURSUS):
            c = charger_cursus(chemin)
            if c:
                cursus[c.id] = c
        else:
            quiz.append(charger_quiz(chemin))

    # Doublons d'identifiant : le second est signalé comme erreur
    vus: dict[str, Path] = {}
    for q in quiz:
        if q.id in vus:
            q.erreurs.append(f"identifiant « {q.id} » déjà utilisé par {vus[q.id].name}")
        else:
            vus[q.id] = q.chemin

    # Un quiz qui cite un cursus sans cursus.json : on crée un cursus minimal
    for q in quiz:
        if q.cursus and q.cursus not in cursus:
            cursus[q.cursus] = Cursus(id=q.cursus, titre=q.cursus.replace("_", " ").capitalize())

    quiz.sort(key=lambda q: (q.cursus, q.ordre, q.titre.casefold()))
    return cursus, quiz
