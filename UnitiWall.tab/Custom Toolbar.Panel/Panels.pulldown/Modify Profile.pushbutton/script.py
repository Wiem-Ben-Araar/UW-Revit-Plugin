# -*- coding: utf-8 -*-
import clr
import traceback
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType


def select_panel():
    """Sélectionne un panneau de mur rideau"""
    try:
        selection = revit.uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Sélectionnez le panneau à modifier")
        return revit.doc.GetElement(picked_ref.ElementId)
    except Exception as e:
        TaskDialog.Show("Erreur", "Erreur lors de la sélection : {}".format(e))
        return None


def get_str_profiles(panel):
    """Récupère les profilés STR du panneau"""
    try:
        collector = FilteredElementCollector(revit.doc)
        bbox = panel.get_BoundingBox(None)
        outline = Outline(bbox.Min, bbox.Max)
        bbox_filter = BoundingBoxIntersectsFilter(outline)

        profiles = collector.WherePasses(bbox_filter) \
            .OfClass(FamilyInstance) \
            .ToElements()

        str_profiles = [p for p in profiles if "STR" in p.Symbol.Family.Name]
        return str_profiles
    except Exception as e:
        print("Erreur lors de la récupération des profilés: {}".format(e))
        return []


def modify_profile_position(profile, panel_length):
    """Modifie la position d'un profilé"""
    try:
        # Obtenir la position actuelle
        current_location = profile.Location.Point
        profile_name = profile.Symbol.Family.Name

        # Convertir la position actuelle en mm
        current_x_mm = current_location.X * 304.8
        current_y_mm = current_location.Y * 304.8
        current_z_mm = current_location.Z * 304.8

        # Afficher la position actuelle
        print("\nPosition actuelle de {}:".format(profile_name))
        print("X: {:.2f} mm".format(current_x_mm))
        print("Y: {:.2f} mm".format(current_y_mm))
        print("Z: {:.2f} mm".format(current_z_mm))

        # Demander les nouvelles positions selon le type de profilé
        new_x_mm = current_x_mm
        new_y_mm = current_y_mm
        new_z_mm = current_z_mm

        if "V" in profile_name:  # Profilé vertical
            new_x = forms.ask_for_string(
                prompt="Nouvelle position X pour {} (en mm)".format(profile_name),
                title="Position X",
                default=str(current_x_mm)
            )
            if new_x:
                new_x_mm = float(new_x)
                # Ajuster par rapport au centre du panneau
                half_panel_length = panel_length / 2
                new_x_mm = new_x_mm - half_panel_length

        elif "H" in profile_name:  # Profilé horizontal
            new_z = forms.ask_for_string(
                prompt="Nouvelle position Z pour {} (en mm)".format(profile_name),
                title="Position Z",
                default=str(current_z_mm)
            )
            if new_z:
                new_z_mm = float(new_z)

        # Convertir en pieds pour Revit
        new_location = XYZ(
            new_x_mm / 304.8,
            new_y_mm / 304.8,
            new_z_mm / 304.8
        )

        return new_location
    except Exception as e:
        print("Erreur lors de la modification du profilé : {}".format(e))
        return None


def main():
    # Sélectionner le panneau
    panel = select_panel()
    if not panel:
        return

    # Obtenir la longueur du panneau
    length_param = panel.LookupParameter("L_PANNEAU")
    if not length_param:
        TaskDialog.Show("Erreur", "Paramètre L_PANNEAU non trouvé")
        return
    panel_length = length_param.AsDouble() * 304.8  # Conversion en mm

    # Récupérer tous les profilés STR
    str_profiles = get_str_profiles(panel)
    if not str_profiles:
        TaskDialog.Show("Information", "Aucun profilé STR trouvé dans ce panneau")
        return

    # Afficher les profilés trouvés
    profile_names = ["{} ({})".format(p.Symbol.Family.Name, p.Id) for p in str_profiles]
    selected_profile_name = forms.SelectFromList.show(
        profile_names,
        title="Sélectionnez le profilé à modifier",
        multiselect=False
    )

    if not selected_profile_name:
        return

    # Trouver le profilé sélectionné
    selected_profile = next(
        (p for p in str_profiles if "{} ({})".format(p.Symbol.Family.Name, p.Id) == selected_profile_name),
        None
    )

    if not selected_profile:
        return

    # Modifier la position du profilé
    new_location = modify_profile_position(selected_profile, panel_length)
    if not new_location:
        return

    # Appliquer les modifications
    try:
        with revit.Transaction("Modifier position profilé") as t:
            selected_profile.Location.Point = new_location
            TaskDialog.Show("Succès", "Position du profilé modifiée avec succès")
    except Exception as e:
        TaskDialog.Show("Erreur", "Erreur lors de la modification : {}".format(e))


# Exécuter le script
if __name__ == "__main__":
    main()
