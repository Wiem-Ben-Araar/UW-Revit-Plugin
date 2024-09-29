# -*- coding: utf-8 -*-
import clr
import traceback
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.DB import IFamilyLoadOptions

clr.AddReference('System.Windows.Forms')

def select_panel():
    """Sélectionne un panneau de mur rideau dans le projet."""
    try:
        selection = revit.uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Select the curtain wall panel to modify")
        selected_element = revit.doc.GetElement(picked_ref.ElementId)

        if isinstance(selected_element, FamilyInstance):
            return selected_element
        else:
            TaskDialog.Show("Error", "The selected item is not a curtain wall panel instance.")
            return None
    except Exception as e:
        TaskDialog.Show("Error", "An error occurred while selecting the panel: {}".format(e))
        return None

def get_panel_length_from_project(panel):
    """Retourne la longueur du panneau en millimètres directement depuis le projet."""
    try:
        length_param = panel.LookupParameter("L_PANNEAU")
        if length_param:
            length_value = length_param.AsDouble()  # Valeur en pieds
            length_in_mm = length_value * 304.8  # Conversion des pieds en millimètres
            return length_in_mm
        else:
            param_names = [param.Definition.Name for param in panel.Parameters]
            TaskDialog.Show("Error", "The parameter 'L_PANNEAU' was not found.\nAvailable parameters: {}".format(
                ', '.join(param_names)))
            return None
    except Exception as e:
        TaskDialog.Show("Error", "An error occurred while obtaining the length: {}".format(e))
        return None

def open_family_in_editor(family_instance):
    """Ouvre la famille sélectionnée dans l'éditeur de famille."""
    try:
        family = family_instance.Symbol.Family
        family_doc = revit.doc.EditFamily(family)
        return family_doc if family_doc else None
    except Exception as e:
        TaskDialog.Show("Error", "An error occurred while opening the family: {}".format(e))
        return None

def select_profile_symbol(family_doc):
    """Permet à l'utilisateur de sélectionner un symbole de profil disponible dans l'éditeur de famille."""
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilySymbol)
        profiles = {f.Id: f for f in collector if "PROFILE" in f.Family.Name}

        if not profiles:
            forms.alert("No family profile found.", exitscript=True)

        profile_names = ["{} {}".format(profile.Family.Name, profile.Id) for id, profile in profiles.items()]
        selected_profile_name = forms.SelectFromList.show(profile_names, title="Select a profile", multiselect=False)

        if not selected_profile_name:
            forms.alert("No profile selected.", exitscript=True)

        selected_profile_id = next((id for id, profile in profiles.items() if "{} {}".format(profile.Family.Name, id) == selected_profile_name), None)
        return profiles[selected_profile_id] if selected_profile_id else None

    except Exception as e:
        forms.alert("Error selecting profile symbol : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)
        return None

def add_profile_to_family(family_doc, profile_symbol, panel_length_mm):
    """Ajoute une instance du profil sélectionné à la famille et demande les positions en fonction du profil."""
    try:
        # Initialisation des valeurs par défaut
        insertion_point_x_ft = 0
        insertion_point_y_ft = 0
        insertion_point_z_ft = 0

        # Vérifie si le profil est 'PROFILE_PLN_124_V'
        if profile_symbol.Family.Name == "PROFILE_PLN_124_V":
            insertion_point_y_mm = -168  # Y en bas
            insertion_point_y_ft = insertion_point_y_mm / 304.8

            user_input_x_mm = forms.ask_for_string(prompt="Entrez la nouvelle position X (en mm) pour PROFILE_PLN_124_V", title="Valeur de X")
            if user_input_x_mm:
                try:
                    position_x_mm = float(user_input_x_mm)
                    half_panel_length_mm = panel_length_mm / 2
                    insertion_point_x_mm = position_x_mm - half_panel_length_mm
                    insertion_point_x_ft = insertion_point_x_mm / 304.8
                except ValueError:
                    forms.alert("La valeur saisie pour X n'est pas valide. Veuillez entrer un nombre.")
                    return

        # Vérifie si le profil est 'PROFILE_STR_152_V'
        elif profile_symbol.Family.Name == "PROFILE_STR_152_V":
            insertion_point_y_mm = 44  # Décalage Y
            insertion_point_y_ft = insertion_point_y_mm / 304.8

            user_input_x_mm = forms.ask_for_string(prompt="Entrez la nouvelle position X (en mm) pour PROFILE_STR_152_V", title="Valeur de X")
            if user_input_x_mm:
                try:
                    position_x_mm = float(user_input_x_mm)
                    half_panel_length_mm = panel_length_mm / 2
                    insertion_point_x_mm = position_x_mm - half_panel_length_mm
                    insertion_point_x_ft = insertion_point_x_mm / 304.8
                except ValueError:
                    forms.alert("La valeur saisie pour X n'est pas valide. Veuillez entrer un nombre.")
                    return

        # Vérifie si le profil est 'PROFILE_STR_152_H'
        elif profile_symbol.Family.Name == "PROFILE_STR_152_H" or profile_symbol.Family.Name == "PROFILE_STR_152_H_DOUBLE":
            user_input_z_mm = forms.ask_for_string(
                prompt="Entrez la valeur de Z (en mm) pour {}".format(profile_symbol.Family.Name), title="Valeur de Z")
            if user_input_z_mm:
                try:
                    insertion_point_z_ft = float(user_input_z_mm) / 304.8
                except ValueError:
                    forms.alert("La valeur saisie pour Z n'est pas valide. Veuillez entrer un nombre.")
                    return

        # Création du point d'insertion (X, Y, Z)
        insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)

        with Transaction(family_doc, "Add a profile to the family") as t:
            t.Start()
            if not profile_symbol.IsActive:
                profile_symbol.Activate()

            # Création d'une nouvelle instance de famille avec les coordonnées spécifiées
            family_instance = family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)

            t.Commit()

        family_doc.Save()

    except Exception as e:
        forms.alert("Erreur lors de l'ajout du profil à la famille : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)


class FamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        # Renvoie True pour écraser les familles existantes si elles sont déjà chargées
        overwriteParameterValues.Value = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

def load_family_back_to_project(family_doc):
    """Charge la famille éditée dans le projet principal."""
    try:
        # Sauvegarde et ferme la famille modifiée
        family_path = family_doc.PathName
        family_doc.Close(False)

        # Créer une instance de FamilyLoadOptions
        familyLoadOptions = FamilyLoadOptions()

        with revit.Transaction("Charger la famille dans le projet"):
            if revit.doc.LoadFamily(family_path, familyLoadOptions):
                forms.alert("La famille a été chargée avec succès dans le projet principal.")
            else:
                forms.alert("Échec du chargement de la famille dans le projet principal.")
    except Exception as e:
        forms.alert("Erreur lors du chargement de la famille dans le projet principal : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)




def main():
    """Fonction principale pour ajouter un profil à une famille."""
    panel = select_panel()
    if panel:
        panel_length = get_panel_length_from_project(panel)

        if panel_length is not None:
            family_doc = open_family_in_editor(panel)
            if family_doc:
                profile_symbol = select_profile_symbol(family_doc)
                if profile_symbol:
                    add_profile_to_family(family_doc, profile_symbol, panel_length)
                    load_family_back_to_project(family_doc)  # Charger la famille dans le projet principal

main()

