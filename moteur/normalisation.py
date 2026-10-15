"""Normalisation des textes : réponses saisies, réponses attendues et identifiants.

Toutes les comparaisons de l'application passent par ce module, pour qu'une
majuscule, un espace insécable ou une apostrophe typographique ne transforme
jamais une bonne réponse en erreur.
"""

import re
import unicodedata

# Espaces « exotiques » copiés-collés depuis Word, le web, etc.
_ESPACES = {
    " ",  # espace insécable
    " ",  # espace fine insécable (typographie française)
    " ",  # espace tabulaire
    " ",  # espace fine
    " ",  # espace ultra-fine
    "　",  # espace idéographique
    "\t",
    "\r",
    "\n",
}
# Caractères invisibles à supprimer purement et simplement
_INVISIBLES = {"​", "‌", "‍", "﻿", "­"}

_APOSTROPHES = {"’", "‘", "ʼ", "′", "`", "´"}
_TIRETS = {"‐", "‑", "‒", "–", "—", "−"}

# Ponctuation ignorée en début / fin de réponse (« Mèsi ! » == « mèsi »)
_PONCTUATION_BORDS = " .,;:!?¡¿…\"«»()[]"

_TABLE = str.maketrans(
    {**{c: " " for c in _ESPACES},
     **{c: "" for c in _INVISIBLES},
     **{c: "'" for c in _APOSTROPHES},
     **{c: "-" for c in _TIRETS}}
)


def normaliser(texte) -> str:
    """Forme canonique d'un texte pour la comparaison (accents conservés)."""
    if texte is None:
        return ""
    texte = unicodedata.normalize("NFC", str(texte))
    texte = texte.translate(_TABLE)
    texte = re.sub(r" +", " ", texte)
    # Pas d'espace autour des apostrophes : « m 'ap » == « m'ap »
    texte = re.sub(r" ?' ?", "'", texte)
    texte = texte.strip(_PONCTUATION_BORDS)
    return texte.casefold()


def sans_accents(texte: str) -> str:
    """Retire les diacritiques (ò -> o, è -> e...). À appliquer après normaliser()."""
    decompose = unicodedata.normalize("NFD", texte)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decompose if not unicodedata.combining(c))
    )


def identifiant(texte) -> str:
    """Forme canonique d'un identifiant ou d'un mot-clé lu dans un fichier.

    « Haïtien », « HAITIEN » et « haitien » donnent tous « haitien » ;
    « Vrai / Faux » et « vrai_faux » donnent « vrai_faux ».
    """
    texte = sans_accents(normaliser(texte))
    texte = re.sub(r"[^a-z0-9]+", "_", texte)
    return texte.strip("_")


# Statuts possibles d'une comparaison
JUSTE = "juste"
ACCENT = "accent"  # juste, mais avec une faute d'accent signalée
FAUX = "faux"

# Valeurs autorisées pour tolerance_accents
TOLERANCES = ("refuser", "avertir", "accepter")


def comparer(saisie, acceptees, tolerance: str = "avertir") -> tuple[str, str]:
    """Compare une saisie à une liste de réponses acceptées.

    Retourne (statut, reponse_de_reference) où statut vaut JUSTE, ACCENT ou FAUX
    et reponse_de_reference est la forme attendue à montrer à l'apprenant.
    """
    if isinstance(acceptees, str):
        acceptees = [acceptees]
    acceptees = [a for a in acceptees if a is not None]
    reference = str(acceptees[0]) if acceptees else ""

    saisie_n = normaliser(saisie)
    if not saisie_n:
        return FAUX, reference

    # 1) Correspondance exacte (aux normalisations près)
    for attendue in acceptees:
        if saisie_n == normaliser(attendue):
            return JUSTE, str(attendue)

    # 2) Correspondance en ignorant les accents
    if tolerance != "refuser":
        saisie_sa = sans_accents(saisie_n)
        for attendue in acceptees:
            if saisie_sa == sans_accents(normaliser(attendue)):
                statut = JUSTE if tolerance == "accepter" else ACCENT
                return statut, str(attendue)

    return FAUX, reference
