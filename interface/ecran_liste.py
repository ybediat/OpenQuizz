"""Liste des quiz disponibles pour le profil, regroupés par cursus."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QHeaderView, QSplitter, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from moteur.modeles import Cursus, Quiz
from moteur.stockage import DernierResultat, Profil

from .commun import bouton, etiquette

HORS_CURSUS = ""


class EcranListe(QWidget):
    lancer = Signal(object)          # Quiz
    changer_profil = Signal()
    modifier_cursus = Signal()
    actualiser = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.profil: Profil | None = None
        self.quiz_selectionne: Quiz | None = None
        self.resultats: dict[str, DernierResultat] = {}

        layout = QVBoxLayout(self)

        # En-tête : salutation + actions sur le profil
        entete = QHBoxLayout()
        self.salutation = etiquette("", "titreEcran")
        entete.addWidget(self.salutation, 1)
        entete.addWidget(bouton("Actualiser", "boutonDiscret", self.actualiser.emit))
        entete.addWidget(bouton("Mes cursus", "boutonDiscret", self.modifier_cursus.emit))
        entete.addWidget(bouton("Changer de profil", "boutonDiscret", self.changer_profil.emit))
        layout.addLayout(entete)

        separateur = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(separateur, 1)

        # Gauche : arbre cursus > quiz
        self.arbre = QTreeWidget()
        self.arbre.setObjectName("listeQuiz")
        self.arbre.setHeaderLabels(["Quiz", "Dernier score"])
        self.arbre.setRootIsDecorated(False)
        self.arbre.setIndentation(12)
        # Colonne « Quiz » élastique, « Dernier score » à la taille du contenu :
        # pas de largeur fixe calculée avant affichage, donc pas de barre horizontale
        entete = self.arbre.header()
        entete.setStretchLastSection(False)
        entete.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        entete.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.arbre.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.arbre.currentItemChanged.connect(self._selection)
        self.arbre.itemDoubleClicked.connect(lambda *_: self._lancer())
        separateur.addWidget(self.arbre)

        # Droite : fiche détaillée du quiz sélectionné
        fiche = QFrame()
        fiche.setObjectName("carte")
        fl = QVBoxLayout(fiche)
        self.titre = etiquette("", "titreCarte")
        self.meta = etiquette("", "texteDiscret")
        self.description = etiquette("", "texteCarte")
        self.historique = etiquette("", "texteDiscret")
        self.erreurs = etiquette("", "messageErreur")
        self.erreurs.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        for w in (self.titre, self.meta, self.description, self.historique, self.erreurs):
            fl.addWidget(w)
        fl.addStretch()
        self.bouton_lancer = bouton("Lancer le quiz", "boutonPrincipal", self._lancer)
        fl.addWidget(self.bouton_lancer, alignment=Qt.AlignmentFlag.AlignRight)
        separateur.addWidget(fiche)
        separateur.setSizes([420, 480])

    def afficher(self, profil: Profil, cursus: dict[str, Cursus], quiz: list[Quiz],
                 resultats: dict[str, DernierResultat]):
        self.profil, self.resultats = profil, resultats
        self.salutation.setText(f"Bonjour {profil.nom} !")
        precedent = self.quiz_selectionne.id if self.quiz_selectionne else None
        self.arbre.clear()

        # Quiz visibles : ceux des cursus suivis, plus ceux sans cursus
        groupes: dict[str, list[Quiz]] = {}
        for q in quiz:
            if q.cursus in profil.cursus or q.cursus == HORS_CURSUS:
                groupes.setdefault(q.cursus, []).append(q)

        a_selectionner = None
        ordre = sorted(groupes, key=lambda c: (c == HORS_CURSUS, cursus[c].titre.casefold() if c in cursus else c))
        for cid in ordre:
            titre = cursus[cid].titre if cid in cursus else "Autres quiz"
            groupe = QTreeWidgetItem([titre])
            groupe.setFlags(Qt.ItemFlag.ItemIsEnabled)  # titre de groupe non sélectionnable
            police = groupe.font(0)
            police.setBold(True)
            groupe.setFont(0, police)
            self.arbre.addTopLevelItem(groupe)
            for q in groupes[cid]:
                res = resultats.get(q.id)
                score = f"{res.score}/{res.total}" if res else "—"
                element = QTreeWidgetItem([q.titre if q.valide else f"⚠ {q.titre}", score])
                element.setData(0, Qt.ItemDataRole.UserRole, q)
                if not q.valide:
                    element.setForeground(0, Qt.GlobalColor.gray)
                groupe.addChild(element)
                if a_selectionner is None or q.id == precedent:
                    a_selectionner = element
            groupe.setExpanded(True)

        if a_selectionner:
            self.arbre.setCurrentItem(a_selectionner)
        else:
            self._afficher_fiche(None)

    def _selection(self, element, _precedent=None):
        q = element.data(0, Qt.ItemDataRole.UserRole) if element else None
        self._afficher_fiche(q)

    def _afficher_fiche(self, q: Quiz | None):
        self.quiz_selectionne = q
        if q is None:
            self.titre.setText("Aucun quiz")
            self.meta.setText("")
            self.description.setText("Aucun quiz ne correspond à tes cursus. "
                                     "Clique sur « Mes cursus » pour en choisir.")
            self.historique.setText("")
            self.erreurs.hide()
            self.bouton_lancer.setEnabled(False)
            return

        self.titre.setText(q.titre)
        infos = [f"{len(q.questions)} question{'s' if len(q.questions) > 1 else ''}"]
        if q.niveau:
            infos.append(q.niveau)
        if q.lecon:
            infos.append("avec leçon")
        if q.tags:
            infos.append(", ".join(q.tags))
        self.meta.setText(" · ".join(infos))
        self.description.setText(q.description)

        res = self.resultats.get(q.id)
        if res:
            parties = f"{res.nb_parties} partie{'s' if res.nb_parties > 1 else ''}"
            self.historique.setText(f"Dernier score : {res.score}/{res.total} le {res.date} ({parties})")
        else:
            self.historique.setText("Jamais fait")

        if q.valide:
            self.erreurs.hide()
        else:
            self.erreurs.setText("Ce quiz contient des erreurs :\n• " + "\n• ".join(q.erreurs)
                                 + f"\n\nFichier : {q.chemin}")
            self.erreurs.show()
        self.bouton_lancer.setEnabled(q.valide)

    def _lancer(self):
        if self.quiz_selectionne and self.quiz_selectionne.valide:
            self.lancer.emit(self.quiz_selectionne)
