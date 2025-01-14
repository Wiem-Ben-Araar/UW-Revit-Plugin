# -*- coding: utf-8 -*-
"""
Description:
This script allows adding and modifying structural profiles to a curtain wall panel in Revit.

Version: v3
Author: Wiem Ben Araar, Amira Dridi
"""

import clr
import traceback
import os
import csv
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.DB.Structure import StructuralType

clr.AddReference('System.Windows.Forms')

# Définir un répertoire relatif ou le dossier de l'utilisateur pour le fichier CSV
csv_directory = os.path.join(os.path.expanduser("~"), "Desktop", "PyRevit", "MyExtension.extension")

# Créer le répertoire seulement s'il n'existe pas déjà
if not os.path.exists(csv_directory):
    os.makedirs(csv_directory)

csv_file = os.path.join(csv_directory, "profiles_data.csv")

# En-têtes du fichier CSV
headers = ["Profile Name", "X Position (mm)", "Y Position (mm)", "Z Position (mm)", "Distance Between Profiles (mm)"]

# Création du fichier CSV vide avec les en-têtes
def create_csv_with_headers():
    """Crée un fichier CSV avec des en-têtes si le fichier n'existe pas déjà."""
    if not os.path.exists(csv_file):  # Vérifier si le fichier existe déjà
        try:
            with open(csv_file, mode="w") as file:  # 'w' pour écrire et créer le fichier
                writer = csv.writer(file, delimiter='|')  # Utiliser une tabulation comme séparateur
                writer.writerow(headers)  # Écrire les en-têtes dans le fichier CSV
            print("Le fichier {} a été créé avec succès avec les en-têtes.".format(csv_file))
        except Exception as e:
            print("Error creating CSV file: {}".format(e))

# Appel de la fonction pour créer le fichier CSV
create_csv_with_headers()

# Fonction pour sauvegarder les informations dans le fichier CSV
def save_to_csv(profile_name, insertion_point_x, insertion_point_y, insertion_point_z, distance):
    """Sauvegarde les informations des profils dans un fichier CSV."""
    try:
        with open(csv_file, mode="a") as file:  # 'a' pour ajouter à la fin du fichier
            writer = csv.writer(file, delimiter='|')  # Utiliser une tabulation comme séparateur
            # Écrire chaque valeur dans sa propre colonne
            writer.writerow([profile_name, insertion_point_x, insertion_point_y, insertion_point_z, distance])
    except Exception as e:
        TaskDialog.Show("Error", "Error while saving to CSV file: {}".format(e))
# --- Utility Functions ---
def select_panel():
    """Select a curtain wall panel in the project."""
    try:
        selection = revit.uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Select the curtain wall panel to modify")
        selected_element = revit.doc.GetElement(picked_ref.ElementId)

        if isinstance(selected_element, FamilyInstance):
            return selected_element
        else:
            TaskDialog.Show("Error", "The selected item is not a curtain wall panel.")
            return None
    except Exception as e:
        TaskDialog.Show("Error", "An error occurred while selecting the panel: {}".format(e))
        return None

def get_panel_length_from_project(panel):
    """Retrieve the panel length (L_PANNEAU parameter) in mm."""
    try:
        length_param = panel.LookupParameter("L_PANNEAU")
        if length_param:
            length_value = length_param.AsDouble()  # Feet
            return length_value * 304.8  # Convert to mm
        else:
            TaskDialog.Show("Error", "Parameter 'L_PANNEAU' not found.")
            return None
    except Exception as e:
        TaskDialog.Show("Error", "Error retrieving panel length: {}".format(e))
        return None

def open_family_in_editor(panel):
    """Open the selected panel family in the Family Editor."""
    try:
        family = panel.Symbol.Family
        return revit.doc.EditFamily(family)
    except Exception as e:
        TaskDialog.Show("Error", "Error opening family in editor: {}".format(e))
        return None

def select_profile_symbol(family_doc):
    """Allow user to select a profile symbol from the family."""
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilySymbol)
        profiles = {f.Id: f for f in collector if "PROFILE" in f.Family.Name}

        if not profiles:
            forms.alert("No profile families found.", exitscript=True)

        profile_names = ["{} (ID: {})".format(profile.Family.Name, id) for id, profile in profiles.items()]
        selected_name = forms.SelectFromList.show(profile_names, title="Select a profile", multiselect=False)

        if not selected_name:
            forms.alert("No profile selected.", exitscript=True)

        selected_id = next(
            id for id, profile in profiles.items() if "{} (ID: {})".format(profile.Family.Name, id) == selected_name)
        return profiles[selected_id]
    except Exception as e:
        forms.alert("Error selecting profile symbol: {}\nTraceback: {}".format(e, traceback.format_exc()), exitscript=True)

# --- Add or Modify Profiles ---
class FamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

def load_family_back_to_project(family_doc):
    """Charge la famille éditée dans le projet principal."""
    try:
        family_path = family_doc.PathName
        family_doc.Close(False)

        familyLoadOptions = FamilyLoadOptions()

        with revit.Transaction("Load family into project"):
            if revit.doc.LoadFamily(family_path, familyLoadOptions):
                forms.alert("The family was successfully loaded into the main project.")
            else:
                forms.alert("Failed to load family into main project.")
    except Exception as e:
        forms.alert("Error loading family into project: {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)

def add_or_modify_profiles(family_doc, profile_symbol, panel_length_mm, mode="add"):
    """Add new profiles or modify existing ones."""
    try:
        num_profiles = int(forms.ask_for_string(prompt="Enter number of profiles:", title="Number of Profiles", default="1"))
        if num_profiles < 1:
            forms.alert("The number of profiles must be at least 1.")
            return

        distance_mm = float(forms.ask_for_string(prompt="Enter distance between profiles (mm):", title="Distance", default="100"))
        if distance_mm < 0:
            forms.alert("Distance cannot be negative.")
            return

        with Transaction(family_doc, "Add or Modify Profiles") as t:
            t.Start()
            existing_instances = [el for el in FilteredElementCollector(family_doc).OfClass(FamilyInstance) if el.Symbol.Id == profile_symbol.Id]
            num_existing = len(existing_instances)

            for i in range(num_profiles):
                position_x_mm = distance_mm * i
                half_panel_length_mm = panel_length_mm / 2
                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                insertion_point_x_ft = insertion_point_x_mm / 304.8
                x_pos = insertion_point_x_ft
                y_pos, z_pos = 0, 0

                if mode == "modify" and i < num_existing:
                    profile_instance = existing_instances[i]
                    current_location = profile_instance.Location.Point
                    new_location = XYZ(x_pos, y_pos / 304.8, z_pos / 304.8)
                    profile_instance.Location.Move(new_location - current_location)
                else:
                    new_location = XYZ(x_pos, y_pos / 304.8, z_pos / 304.8)
                    family_doc.FamilyCreate.NewFamilyInstance(new_location, profile_symbol, StructuralType.NonStructural)
                    save_to_csv(profile_symbol.Family.Name, position_x_mm, y_pos, z_pos, distance_mm)

            if mode == "modify" and num_profiles < num_existing:
                for i in range(num_profiles, num_existing):
                    family_doc.Delete(existing_instances[i].Id)

            t.Commit()

        family_doc.Save()
    except Exception as e:
        forms.alert("Error in {} profiles: {}\nTraceback: {}".format(mode, e, traceback.format_exc()), exitscript=True)

# --- Main Entry Point ---
def main():
    """Main script entry point."""
    panel = select_panel()
    if not panel:
        return

    panel_length_mm = get_panel_length_from_project(panel)
    if not panel_length_mm:
        return

    family_doc = open_family_in_editor(panel)
    if not family_doc:
        return

    profile_symbol = select_profile_symbol(family_doc)
    if not profile_symbol:
        return

    action = forms.alert("Choose action: Add or Modify profiles?", options=["Add", "Modify"])
    if action == "Add":
        add_or_modify_profiles(family_doc, profile_symbol, panel_length_mm, mode="add")
    elif action == "Modify":
        add_or_modify_profiles(family_doc, profile_symbol, panel_length_mm, mode="modify")

    load_family_back_to_project(family_doc)

# Execute script
main()