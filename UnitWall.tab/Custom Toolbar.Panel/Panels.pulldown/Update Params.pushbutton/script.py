# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import Transaction
from pyrevit import forms
from Autodesk.Revit.UI.Selection import ObjectType

def update_panel_parameters(doc, element):
    """Met à jour les paramètres 'H_PANNEAU' et 'L_PANNEAU' en fonction de la hauteur et de la largeur du panneau."""
    # Récupérer la hauteur (paramètre d'instance)
    height_param = element.LookupParameter("Hauteur")
    width_param = element.LookupParameter("Largeur")

    if height_param and width_param:
        height_value = height_param.AsDouble()  # La hauteur est souvent stockée en pieds
        width_value = width_param.AsDouble()  # La largeur est souvent stockée en pieds

        # Essayer de récupérer les paramètres d'occurrence "H_PANNEAU" et "L_PANNEAU"
        h_panneau_param = element.LookupParameter("H_PANNEAU")
        l_panneau_param = element.LookupParameter("L_PANNEAU")

        if h_panneau_param and l_panneau_param:
            # Commencez une transaction pour effectuer les modifications
            with Transaction(doc, "Changer les paramètres H_PANNEAU et L_PANNEAU") as t:
                t.Start()

                # Modifier les paramètres d'occurrence
                h_panneau_param.Set(height_value)
                l_panneau_param.Set(width_value)

                t.Commit()

        else:
            forms.alert("Les paramètres d'occurrence 'H_PANNEAU' ou 'L_PANNEAU' n'ont pas été trouvés pour l'élément sélectionné.", exitscript=True)
    else:
        forms.alert("Les paramètres 'Hauteur' ou 'Largeur' n'ont pas été trouvés pour l'élément sélectionné.", exitscript=True)

# Exécution principale
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

try:
    # Sélectionner un panneau de mur-rideau
    selection = uidoc.Selection
    picked_ref = selection.PickObject(ObjectType.Element, "Sélectionnez un panneau de mur-rideau")
    element = doc.GetElement(picked_ref.ElementId)

    if not element:
        raise Exception("Aucun élément sélectionné.")

    update_panel_parameters(doc, element)

except Exception as e:
    forms.alert(str(e), exitscript=True)
