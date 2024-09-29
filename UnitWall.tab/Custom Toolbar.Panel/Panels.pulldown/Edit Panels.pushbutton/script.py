# -*- coding: utf-8 -*-
import math  # Import pour arrondir au supérieur
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import FamilyInstance

# Distance optimale pour la structure horizontale en mètres (16 pouces = 406.4 mm = 0.4064 m)
optimal_horizontal_distance_meters = 0.4064

# Fonction pour sélectionner un panneau de mur rideau
def select_panel():
    """Permet à l'utilisateur de sélectionner un panneau de mur rideau."""
    selection = revit.uidoc.Selection
    picked_ref = selection.PickObject(ObjectType.Element, "Sélectionnez le panneau de mur rideau à modifier")
    selected_element = revit.doc.GetElement(picked_ref.ElementId)

    if isinstance(selected_element, FamilyInstance):
        return selected_element
    else:
        TaskDialog.Show("Error", "L'élément sélectionné n'est pas un panneau de mur rideau.")
        return None

def main():
    # Sélection du panneau par l'utilisateur
    selected_panel = select_panel()
    if not selected_panel:
        return  # Si la sélection échoue, arrêter le script

    # Liste des paramètres verticaux et horizontaux
    vertical_parameters = ['D_V_S_1', 'D_V_S_2', 'D_V_S_3', 'D_V_S_4']
    horizontal_parameters = ['D_H_S_1', 'D_H_S_2', 'D_H_S_3']

    # Dictionnaire pour stocker les valeurs saisies par l'utilisateur
    param_values = {}

    # Demande de saisie de la valeur pour chaque paramètre vertical
    for param_name in vertical_parameters:
        param = selected_panel.LookupParameter(param_name)
        current_value_meters = param.AsDouble() * 0.3048 if param else 0.0  # Conversion de pieds à mètres

        value_text = forms.ask_for_string(
            title="Value for {}".format(param_name),
            prompt="Enter the value in meters for the parameter {} :".format(param_name),
            default=str(round(current_value_meters, 4))
        )

        if value_text is None:
            return  # Si l'utilisateur annule l'une des saisies, arrêter le script

        try:
            value_in_meters = float(value_text)
            param_values[param_name] = value_in_meters  # Garde la valeur en mètres
        except ValueError:
            forms.alert("Please enter a valid numeric value for {}.".format(param_name), title="Error")
            return

    # Calcul automatique pour les paramètres horizontaux
    height_param = selected_panel.LookupParameter("Hauteur")
    if height_param:
        panel_height_meters = height_param.AsDouble() * 0.3048  # Conversion pieds -> mètres

        # Calculer le nombre optimal de divisions: arrondi supérieur
        optimal_count_ceil = math.ceil(panel_height_meters / optimal_horizontal_distance_meters)  # Arrondi supérieur

        # Calculer la distance optimale
        calculated_value_ceil = panel_height_meters / optimal_count_ceil if optimal_count_ceil > 0 else 0

        # Demande de saisie de la valeur pour chaque paramètre horizontal
        for param_name in horizontal_parameters:
            param = selected_panel.LookupParameter(param_name)
            current_value_meters = param.AsDouble() * 0.3048 if param else calculated_value_ceil  # Valeur par défaut basée sur le calcul si le paramètre est inexistant

            message = (
                "Please enter a new value for {} or accept the calculated value:\n"
                "Calculated value (rounded up) : {:.4f} meters\n"
                "Current value : {:.4f} meters".format(param_name, calculated_value_ceil, current_value_meters)
            )

            value_text = forms.ask_for_string(
                title="Value for {}".format(param_name),
                prompt=message,
                default=str(round(current_value_meters, 4))
            )

            if value_text is None:
                return  # Si l'utilisateur annule, arrêter le script

            try:
                value_in_meters = float(value_text)
                param_values[param_name] = value_in_meters  # Garde la valeur en mètres
            except ValueError:
                forms.alert("Please enter a valid numeric value to {}.".format(param_name), title="Error")
                return

    apply_values_to_selected_panel(selected_panel, param_values)

def apply_values_to_selected_panel(panel, param_values):
    with revit.Transaction("Apply Values to Parameters"):
        modified_this_panel = False  # Vérification si ce panneau est modifié
        for param_name, value_in_meters in param_values.items():
            param = panel.LookupParameter(param_name)
            if param and not param.IsReadOnly:  # Vérifiez que le paramètre n'est pas en lecture seule
                value_in_feet = value_in_meters / 0.3048  # Conversion de mètres en pieds pour Revit
                param.Set(value_in_feet)
                modified_this_panel = True  # Indique que ce panneau a été modifié

        # Affiche un message simple pour indiquer le succès
        if modified_this_panel:
            forms.alert("The selected panel has been successfully updated.", title="Success")
        else:
            forms.alert("No editable settings found for the selected panel.", title="Warning")

# Exécution du script principal
main()
