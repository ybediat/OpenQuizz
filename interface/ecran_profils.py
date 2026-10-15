"""Écran d'accueil : choix ou création du profil."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QGridLayout,
                               QLineEdit, QMenu, QMessageBox, QVBoxLayout, QWidget)

from moteur.modeles import Cursus
from moteur.stockage import Profil, Stockage, format_date

from .commun import bouton, etiquette, vider_layout


class DialogueProfil(QDialog):
    """Création d'un profil, ou modification de ses cursus (profil fourni)."""

    def __init__(self, stockage: Stockage, cursus: dict[str, Cursus],
                 profil: Profil | None = None, parent=None):
        super().__init__(parent)
        self.stockage, self.profil = stockage, profil
        self.setWindowTitle("Mes cursus" if profil else "Nouveau profil")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)

        self.champ_nom = QLineEdit(profil.nom if profil else "")
        self.champ_nom.setPlaceholderText("Ton prénom")
        self.champ_nom.setEnabled(profil is None)
        layout.addWidget(etiquette("Nom du profil", "etiquetteChamp"))
        layout.addWidget(self.champ_nom)

        layout.addWidget(etiquette("Cursus suivis", "etiquetteChamp"))
        self.cases: dict[str, QCheckBox] = {}
        for c in sorted(cursus.values(), key=lambda c: c.titre.casefold()):
            case = QCheckBox(c.titre)
            case.setToolTip(c.description)
            case.setChecked(profil is None or c.id in profil.cursus)
            self.cases[c.id] = case
            layout.addWidget(case)
        if not cursus:
            layout.addWidget(etiquette("Aucun cursus trouvé dans le dossier quiz.", "texteDiscret"))

        self.erreur = etiquette("", "messageErreur")
        self.erreur.hide()
        layout.addWidget(self.erreur)

        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Ok).setText("Enregistrer")
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        boutons.accepted.connect(self._valider)
        boutons.rejected.connect(self.reject)
        layout.addWidget(boutons)

    def cursus_coches(self) -> list[str]:
        return [cid for cid, case in self.cases.items() if case.isChecked()]

    def _valider(self):
        try:
            if self.profil:
                self.stockage.definir_cursus(self.profil.id, self.cursus_coches())
            else:
                self.profil = self.stockage.creer_profil(self.champ_nom.text(), self.cursus_coches())
        except ValueError as e:
            self.erreur.setText(str(e))
            self.erreur.show()
            return
        self.accept()


class EcranProfils(QWidget):
    profil_choisi = Signal(object)  # Profil

    def __init__(self, stockage: Stockage, parent=None):
        super().__init__(parent)
        self.stockage = stockage
        self.cursus: dict[str, Cursus] = {}

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(etiquette("OpenQuizz", "titreApplication"), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(etiquette("Qui révise aujourd'hui ?", "sousTitre"), alignment=Qt.AlignmentFlag.AlignCenter)

        self.grille = QGridLayout()
        self.grille.setSpacing(16)
        layout.addLayout(self.grille)
        layout.addWidget(bouton("+  Nouveau profil", "boutonSecondaire", self._nouveau),
                         alignment=Qt.AlignmentFlag.AlignCenter)

    def rafraichir(self, cursus: dict[str, Cursus]):
        self.cursus = cursus
        vider_layout(self.grille)
        profils = self.stockage.lister_profils()
        if not profils:
            self.grille.addWidget(etiquette("Crée ton premier profil pour commencer.", "texteDiscret"), 0, 0)
        for i, p in enumerate(profils):
            titres = [self.cursus[c].titre for c in p.cursus if c in self.cursus]
            texte = f"{p.nom}\n{', '.join(titres) or 'aucun cursus'}"
            b = bouton(texte, "carteProfil", lambda _=False, p=p: self.profil_choisi.emit(p))
            b.setToolTip(f"Profil créé le {format_date(p.cree_le)}. Clic droit pour modifier.")
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda pos, p=p, b=b: self._menu(p, b, pos))
            self.grille.addWidget(b, i // 3, i % 3)

    def _nouveau(self):
        dialogue = DialogueProfil(self.stockage, self.cursus, parent=self)
        if dialogue.exec():
            self.rafraichir(self.cursus)

    def _menu(self, profil: Profil, widget, position):
        menu = QMenu(self)
        modifier = menu.addAction("Modifier les cursus")
        supprimer = menu.addAction("Supprimer le profil")
        choix = menu.exec(widget.mapToGlobal(position))
        if choix == modifier:
            if DialogueProfil(self.stockage, self.cursus, profil, self).exec():
                self.rafraichir(self.cursus)
        elif choix == supprimer:
            reponse = QMessageBox.question(
                self, "Supprimer le profil",
                f"Supprimer « {profil.nom} » et tout son historique ?\nCette action est définitive.")
            if reponse == QMessageBox.StandardButton.Yes:
                self.stockage.supprimer_profil(profil.id)
                self.rafraichir(self.cursus)
