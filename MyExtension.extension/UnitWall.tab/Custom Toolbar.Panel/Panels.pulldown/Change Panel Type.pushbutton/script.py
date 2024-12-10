# -*- coding: utf-8 -*-
"""

Description:
This script allows the user to select a curtain wall panel type and updates the panel type.

Mode of use:
1. Select a curtain wall panel in Revit.
2. Choose a panel type in the dialog box.
3. The script will update the panel type.

Version: v2
Author: Wiem Ben Araar
"""


from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import forms

# Initialisation
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

def get_panel_types(doc, element):
    """Récupère tous les types de panneaux disponibles dans le document qui sont valides pour l'élément sélectionné."""
    panel_types = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_CurtainWallPanels).WhereElementIsElementType().ToElements()
    valid_types = element.GetValidTypes()
    result = {}
    for panel_type in panel_types:
        if panel_type.Id in valid_types:
            try:
                family_name = panel_type.FamilyName if hasattr(panel_type, 'FamilyName') else 'Unknown Family'
            except:
                family_name = 'Unknown Family'
            try:
                name = panel_type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() if panel_type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM) else 'Unknown Name'
            except:
                name = 'Unknown Name'
            display_name = "{} : {}".format(family_name, name)
            result[display_name] = panel_type
    return result


try:
    # Sélectionner un panneau de mur-rideau
    selection = uidoc.Selection
    picked_ref = selection.PickObject(ObjectType.Element, "Select a curtain wall panel")
    element = doc.GetElement(picked_ref.ElementId)

    if not isinstance(element, FamilyInstance):
        raise Exception("The selected item is not a curtain wall panel.")

    # Récupérer les types de panneaux disponibles et valides
    panel_types = get_panel_types(doc, element)

    if not panel_types:
        raise Exception("No valid panel type available in the document.")

    # Demander à l'utilisateur de sélectionner un type de panneau
    selected_panel_type_name = forms.ask_for_one_item(
        panel_types.keys(),
        default=next(iter(panel_types.keys())),
        prompt="Choose a panel type for the curtain wall:",
        title="Panel Type Selection"
    )

    if selected_panel_type_name:
        selected_panel_type = panel_types[selected_panel_type_name]

        # Démarrer une transaction pour modifier le type de panneau
        with Transaction(doc, "Change Panel Type") as t:
            t.Start()

            # Changer le type de panneau
            element.ChangeTypeId(selected_panel_type.Id)

            t.Commit()


    else:
        TaskDialog.Show("Cancel", "No panel type selected.")

except Exception as e:
    # Afficher plus d'informations sur l'erreur
    import traceback
    error_message = traceback.format_exc()
    TaskDialog.Show("Error", "An error has occurred : {}\n\nDetails :\n{}".format(str(e), error_message))
