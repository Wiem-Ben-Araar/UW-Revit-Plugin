# -*- coding: utf-8 -*-
import clr
import traceback

clr.AddReference('RevitServices')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import *
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.DB.Structure import StructuralType

def select_profile():
    """Sélectionne un profilé à ajouter à la famille."""
    try:
        # Filtrer les symboles de famille qui sont des profilés
        collector = FilteredElementCollector(revit.doc).OfClass(FamilySymbol)
        profiles = {symbol.Id: symbol for symbol in collector if symbol.Family.Name.startswith("PROFILE")}

        if not profiles:
            forms.alert("Aucun profilé trouvé dans la famille.", exitscript=True)

        # Afficher les noms des familles de profilés à l'utilisateur
        profile_names = ["{} {}".format(symbol.Family.Name, symbol.Id) for id, symbol in profiles.items()]
        selected_profile_name = forms.SelectFromList.show(profile_names, title="Sélectionnez un profilé", multiselect=False)

        # Si aucun profilé n'est sélectionné
        if not selected_profile_name:
            forms.alert("Aucun profilé sélectionné.", exitscript=True)

        selected_profile_id = next(
            (id for id, symbol in profiles.items() if "{} {}".format(symbol.Family.Name, id) == selected_profile_name),
            None
        )

        return profiles[selected_profile_id] if selected_profile_id else None

    except Exception as e:
        forms.alert("Erreur lors de la sélection du profilé : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)
        return None


def pick_point_interactively():
    """Permet à l'utilisateur de choisir un point dans la vue active."""
    try:
        uidoc = revit.uidoc
        return uidoc.Selection.PickPoint("Sélectionnez le point d'insertion du profilé")
    except Exception as e:
        forms.alert("Erreur lors de la sélection du point : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)
        return None


def add_profile_to_family(profile_symbol, insertion_point):
    """Ajoute une instance du profilé sélectionné à la famille actuellement ouverte dans l'éditeur de famille."""
    try:
        with revit.Transaction("Ajouter Profilé à la Famille"):
            if not profile_symbol.IsActive:
                profile_symbol.Activate()
                revit.doc.Regenerate()

            # Ajouter le profilé à la position donnée
            new_instance = revit.doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)
            revit.doc.Regenerate()

            if new_instance:
                forms.alert(
                    "Profilé ajouté avec succès à la position ({:.2f}, {:.2f}, {:.2f})".format(
                        insertion_point.X, insertion_point.Y, insertion_point.Z))
            else:
                forms.alert("Le profilé n'a pas été ajouté correctement.")
            return new_instance

    except Exception as e:
        forms.alert("Erreur lors de l'ajout du profilé : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)
        return None

def load_family_to_project():
    """Charge la famille modifiée dans le projet en cours."""
    try:
        with revit.Transaction("Charger la famille dans le projet"):
            family = revit.doc.LoadFamily(revit.uidoc.Application.ActiveUIDocument.Document)
            if family:
                forms.alert("La famille a été chargée avec succès dans le projet.")
            else:
                forms.alert("La famille n'a pas pu être chargée dans le projet.")
    except Exception as e:
        forms.alert("Erreur lors du chargement de la famille dans le projet : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)

def main():
    """Fonction principale pour ajouter un profilé dans la famille actuellement ouverte."""
    profile_symbol = select_profile()
    if not profile_symbol:
        return

    insertion_point = pick_point_interactively()

    if insertion_point:
        add_profile_to_family(profile_symbol, insertion_point)
        load_family_to_project()  # Charger la famille dans le projet après l'insertion
    else:
        forms.alert("Le point d'insertion n'a pas été défini.", exitscript=True)

main()
