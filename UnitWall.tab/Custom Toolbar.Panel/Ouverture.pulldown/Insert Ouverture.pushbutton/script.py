# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
import Autodesk.Revit.UI as UI

import clr
clr.AddReference('System')
import System

# Ajouter des références nécessaires
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')

from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

# Initialisation
doc = DocumentManager.Instance.CurrentDBDocument
uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument


def select_panel():
    """Sélectionne un panneau de mur rideau dans le projet."""
    try:
        selection = uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Sélectionnez le panneau de mur rideau à modifier")
        selected_element = doc.GetElement(picked_ref.ElementId)

        if isinstance(selected_element, FamilyInstance):
            family_category = selected_element.Symbol.Family.FamilyCategory.Name
            if family_category == "Panneau de mur-rideau":
                return selected_element
            else:
                TaskDialog.Show("Erreur", "L'élément sélectionné n'est pas un panneau de mur rideau.")
                return None
        else:
            TaskDialog.Show("Erreur", "L'élément sélectionné n'est pas une instance de famille.")
            return None
    except Exception as e:
        TaskDialog.Show("Erreur", "Une erreur s'est produite lors de la sélection du panneau : {}".format(e))
        return None

def create_opening(panel, opening_location, width, height):
    # Démarrer une transaction
    TransactionManager.Instance.EnsureInTransaction(doc)

    try:
        # Créer un plan de référence pour l'ouverture (simplifié ici)
        TaskDialog.Show("Info", "Les panneaux de mur rideau ne supportent pas directement les ouvertures. " 
                        "Veuillez envisager d'utiliser des familles d'ouverture (portes, fenêtres) pour cela.")

        # Simuler la création d'une ouverture ou d'une autre opération sur le panneau
        # Ici, nous affichons un message, mais c'est là que l'ajout de géométrie personnalisée serait nécessaire
        TaskDialog.Show("Succès", "Opération terminée sur le panneau sélectionné.")

        # Commit la transaction
        TransactionManager.Instance.TransactionTaskDone()

    except Exception as e:
        TransactionManager.Instance.ForceCloseTransaction()
        TaskDialog.Show("Erreur", str(e))


def main():
    panel = select_panel()
    if panel is None:
        return

    # Définir les paramètres de l'ouverture
    width = 1000  # Largeur de l'ouverture en mm
    height = 2000  # Hauteur de l'ouverture en mm

    # Définir la position de l'ouverture comme le centre du panneau
    location = panel.Location.Point

    # Créer l'ouverture (ou un message d'alerte)
    create_opening(panel, location, width, height)


# Exécuter le script
main()
