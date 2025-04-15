# -*- coding: utf-8 -*-
"""
**Description:**
This script allows adding vertical profiles, including plenum profiles, to a curtain wall panel in Revit. It supports two workflows:
1. **Custom Insertion:** The user specifies the number of profiles, spacing between them, and their X-position.
2. **Default Insertion:** Automatically places two profiles to create the frame of the opening

---

**How to Use:**
1. **Select a Panel:** The user selects a curtain wall panel from the project.
2. **Choose Insertion Method:**
   - **Custom Mode:**
     - Specify the number of profiles to create.
     - Define the spacing between profiles.
     - Set the X-position of the first profile relative to the panel's start.
   - **Default Mode:**
     - Automatically inserts two profiles at predefined positions.
3. **Execute:** The profiles are added, and the family is reloaded into the project.

---

**Version:** v3
**Authors:** Wiem Ben Araar, Amira Dridi

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
from Autodesk.Revit.DB import IFamilyLoadOptions

clr.AddReference('System.Windows.Forms')

clr.AddReference('System.Drawing')
import System
from System.Windows.Forms import (
    Form, Label, TextBox, Button, PictureBox, DialogResult,
    DockStyle, FormStartPosition, TableLayoutPanel, FlowLayoutPanel,
    SizeType, ColumnStyle, RowStyle, PictureBoxSizeMode, FormBorderStyle
)
from System.Drawing import Image, ContentAlignment, Size, Font

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


class ProfilesInputForm(Form):
    """
    A custom form to input:
    - Number of profiles
    - Distance between profiles (in mm)
    - With an explanatory image
    """

    def __init__(self, image_path):
        super(ProfilesInputForm, self).__init__()

        # ---- Basic form configuration ----
        self.Text = "Add Profiles to Panel"
        self.Width = 1200
        self.Height = 800
        self.StartPosition = FormStartPosition.CenterScreen
        self.Font = Font("Arial", 12)
        self.FormBorderStyle = FormBorderStyle.Sizable  # Allow resizing

        # ---- TableLayoutPanel to organize UI in a grid ----
        self.tableLayout = TableLayoutPanel()
        self.tableLayout.Dock = DockStyle.Fill
        self.tableLayout.ColumnCount = 2
        self.tableLayout.RowCount = 4  # Back to 4 rows, removing the explanatory text

        # Column widths: 40% for the first (text), 60% for the second (image)
        self.tableLayout.ColumnStyles.Add(ColumnStyle(SizeType.Percent, 40))
        self.tableLayout.ColumnStyles.Add(ColumnStyle(SizeType.Percent, 60))

        # Row heights:
        # 1) Row for image (70% of height)
        # 2) Row for "Number of profiles" (AutoSize)
        # 3) Row for "Distance" (AutoSize)
        # 4) Row for buttons (60 px)
        self.tableLayout.RowStyles.Add(RowStyle(SizeType.Percent, 70))
        self.tableLayout.RowStyles.Add(RowStyle(SizeType.AutoSize))
        self.tableLayout.RowStyles.Add(RowStyle(SizeType.AutoSize))
        self.tableLayout.RowStyles.Add(RowStyle(SizeType.Absolute, 60))

        self.Controls.Add(self.tableLayout)

        # ---- PictureBox for the image ----
        self.pictureBox = PictureBox()
        self.pictureBox.Dock = DockStyle.Fill
        self.pictureBox.SizeMode = PictureBoxSizeMode.Zoom
        self.pictureBox.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle  # Add a border
        try:
            self.pictureBox.Image = Image.FromFile(image_path)
        except Exception as e:
            TaskDialog.Show("Error", "Unable to load image: {}".format(e))

        # Occupy both columns and the first row for the image
        self.tableLayout.SetColumnSpan(self.pictureBox, 2)
        self.tableLayout.Controls.Add(self.pictureBox, 0, 0)

        # ---- Label: "How many profiles" ----
        self.labelNumProfiles = Label()
        self.labelNumProfiles.Text = "How many profiles do you want to add?"
        self.labelNumProfiles.TextAlign = ContentAlignment.MiddleRight
        self.labelNumProfiles.AutoSize = True
        self.labelNumProfiles.Font = Font("Arial", 14)
        self.tableLayout.Controls.Add(self.labelNumProfiles, 0, 1)

        # ---- TextBox for number of profiles ----
        self.textBoxNumProfiles = TextBox()
        self.textBoxNumProfiles.Text = "1"  # Default value
        self.textBoxNumProfiles.Font = Font("Arial", 14)
        self.textBoxNumProfiles.Width = 200
        self.tableLayout.Controls.Add(self.textBoxNumProfiles, 1, 1)

        # ---- Label: "Distance between profiles" ----
        self.labelDistance = Label()
        self.labelDistance.Text = "Distance between profiles (in mm)?"
        self.labelDistance.TextAlign = ContentAlignment.MiddleRight
        self.labelDistance.AutoSize = True
        self.labelDistance.Font = Font("Arial", 14)
        self.tableLayout.Controls.Add(self.labelDistance, 0, 2)

        # ---- TextBox for distance ----
        self.textBoxDistance = TextBox()
        self.textBoxDistance.Text = "100"  # Default value
        self.textBoxDistance.Font = Font("Arial", 14)
        self.textBoxDistance.Width = 200
        self.tableLayout.Controls.Add(self.textBoxDistance, 1, 2)

        # ---- FlowLayoutPanel for OK / Cancel buttons ----
        self.buttonPanel = FlowLayoutPanel()
        self.buttonPanel.FlowDirection = System.Windows.Forms.FlowDirection.RightToLeft
        self.buttonPanel.Dock = DockStyle.Fill
        self.buttonPanel.Padding = System.Windows.Forms.Padding(10)
        self.tableLayout.SetColumnSpan(self.buttonPanel, 2)
        self.tableLayout.Controls.Add(self.buttonPanel, 0, 3)

        # ---- OK Button ----
        self.okButton = Button()
        self.okButton.Text = "OK"
        self.okButton.DialogResult = DialogResult.OK
        self.okButton.Font = Font("Arial", 14, System.Drawing.FontStyle.Bold)
        self.okButton.Padding = System.Windows.Forms.Padding(15, 5, 15, 5)
        self.okButton.MinimumSize = Size(120, 40)
        self.buttonPanel.Controls.Add(self.okButton)

        # ---- Cancel Button ----
        self.cancelButton = Button()
        self.cancelButton.Text = "Cancel"
        self.cancelButton.DialogResult = DialogResult.Cancel
        self.cancelButton.Font = Font("Arial", 14)
        self.cancelButton.Padding = System.Windows.Forms.Padding(15, 5, 15, 5)
        self.cancelButton.MinimumSize = Size(150, 40)
        self.buttonPanel.Controls.Add(self.cancelButton)

        # Associate OK and Cancel buttons
        self.AcceptButton = self.okButton
        self.CancelButton = self.cancelButton
def get_profiles_input(image_path):
    """
    Ouvre la fenêtre ProfilesInputForm et renvoie (nombre_de_profils, distance_mm).
    Si l'utilisateur annule, renvoie (None, None).
    """
    form = ProfilesInputForm(image_path)
    result = form.ShowDialog()
    if result == DialogResult.OK:
        return form.textBoxNumProfiles.Text, form.textBoxDistance.Text
    else:
        return None, None
def select_panel():
    """Sélectionne un panneau de mur rideau dans le projet."""
    try:
        selection = revit.uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Select the curtain wall panel to modify")
        selected_element = revit.doc.GetElement(picked_ref.ElementId)

        if isinstance(selected_element, FamilyInstance):
            return selected_element
        else:
            TaskDialog.Show("Error", "The selected item is not an instance of a curtain wall panel.")
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
        TaskDialog.Show("Error", "Une erreur est survenue lors de l'obtention de la longueur : {}".format(e))
        return None

def open_family_in_editor(family_instance):
    """Ouvre la famille sélectionnée dans l'éditeur de famille."""
    try:
        family = family_instance.Symbol.Family
        family_doc = revit.doc.EditFamily(family)
        return family_doc if family_doc else None
    except Exception as e:
        TaskDialog.Show("Error", "An error occurred while opening the family:{}".format(e))
        return None

def select_profile_symbol(family_doc):
    """Permet à l'utilisateur de sélectionner un symbole de profil disponible dans l'éditeur de famille."""
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilySymbol)
        profiles = {f.Id: f for f in collector if "PLN" in f.Family.Name and "WIN" not in f.Family.Name and "H" not in f.Family.Name}

        if not profiles:
            forms.alert("No family profiles found.", exitscript=True)

        profile_names = ["{} {}".format(profile.Family.Name, profile.Id) for id, profile in profiles.items()]
        selected_profile_name = forms.SelectFromList.show(profile_names, title="Select a profile", multiselect=False)

        if not selected_profile_name:
            forms.alert("No profile selected.", exitscript=True)

        selected_profile_id = next((id for id, profile in profiles.items() if
                                     "{} {}".format(profile.Family.Name, id) == selected_profile_name), None)
        return profiles[selected_profile_id] if selected_profile_id else None

    except Exception as e:
        forms.alert("Error selecting profile symbol: {}\nTraceback : {}".format(e, traceback.format_exc()),
                    exitscript=True)
        return None








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


def add_profiles_to_family(family_doc, profile_symbol, panel_length_mm, num_profiles, distance_mm):
    """Adds multiple instances of the selected profile to the family at a specific position, taking into account the panel width."""
    try:
        # Initial position
        insertion_point_x_ft = 0
        insertion_point_y_ft = 0
        insertion_point_z_ft = 0

        # Retrieve the values of SILL and LINTEL for Z constraints
        panel = select_panel()
        if not panel:
            TaskDialog.Show("Error", "No panel selected.")
            return

        sill_param = panel.LookupParameter("SILL")
        right_param = panel.LookupParameter("RIGHT")
        lintel_param = panel.LookupParameter("LINTEL")
        left_param = panel.LookupParameter("LEFT")
        l_window_param = panel.LookupParameter("L_WINDOW")

        if not sill_param or not lintel_param or not left_param or not l_window_param:
            TaskDialog.Show("Error",
                            "The parameters SILL, LINTEL, LEFT, or L_WINDOW are not found in the panel.")
            return

        sill_value_ft = sill_param.AsDouble()  # SILL value in feet
        right_value_ft = right_param.AsDouble()
        lintel_value_ft = lintel_param.AsDouble()  # LINTEL value in feet
        left_value_ft = left_param.AsDouble()  # LEFT value in feet
        l_window_value_ft = l_window_param.AsDouble()  # L_WINDOW value in feet

        # Convert LEFT and L_WINDOW to millimeters for display
        left_value_mm = left_value_ft * 304.8
        l_window_value_mm = l_window_value_ft * 304.8
        right_value_mm = right_value_ft * 304.8

        # Specific conditions for each profile
        if profile_symbol.Family.Name == "PROFILE_PLN_124_V":
            while True:
                # Define the minimum and maximum interval
                interval_min_mm = right_value_mm - 31.5 - (num_profiles - 1) * distance_mm
                interval_max_mm = right_value_mm + l_window_value_mm + 31.5

                # Check if the space is insufficient
                available_space_left = interval_min_mm  # Space before the min
                available_space_right = panel_length_mm - interval_max_mm  # Space after the max
                required_space = (num_profiles - 1) * distance_mm  # Total required space

                if available_space_left < required_space and available_space_right < required_space:
                    forms.alert(
                        "Error: The available space is insufficient for " + str(num_profiles) +
                        " profiles with a distance of " + str(distance_mm) + " mm between them.\n" +
                        "Please reduce the number of profiles or decrease the distance between them."
                    )

                    # Ask the user for new values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new distance between profiles (in mm):",
                        title="Distance between profiles"
                    )

                    if user_input_num_profiles and user_input_distance_mm:
                        try:
                            num_profiles = int(user_input_num_profiles)
                            distance_mm = float(user_input_distance_mm)
                            continue  # Recalculate with the new values
                        except ValueError:
                            forms.alert("Invalid value. Please enter valid numbers.")
                            continue  # Ask again
                    else:
                        forms.alert("No value entered. Operation cancelled.")
                        break  # Exit if the user does not want to enter new values

                if interval_min_mm < 94.5:
                    # If interval_min_mm is negative, only display the part "after interval_max_mm"
                    prompt_message = (
                        "Enter the value of X (in mm) for " + profile_symbol.Family.Name +
                        " between [" +
                        str(round(interval_max_mm + 63, 2)) + " , " +
                        str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) + "]"
                    )
                else:
                    # Otherwise, display both options (before interval_min_mm or after interval_max_mm)
                    prompt_message = (
                        "The value of X must be between [94.5 , " +
                        str(round(interval_min_mm, 2)) + "] or between [" +
                        str(round(interval_max_mm, 2)) + " , " +
                        str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) + "]"
                    )

                # Ask the user for the value of X
                user_input_x_mm = forms.ask_for_string(
                    prompt=prompt_message,
                    title="Value of X"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Strict check: X must be BEFORE the min or AFTER the max while respecting the incrementation
                        if (position_x_mm < interval_min_mm and position_x_mm > 0) or \
                           (position_x_mm > interval_max_mm and (position_x_mm + (num_profiles - 1) * distance_mm) <= panel_length_mm):

                            if panel_length_mm is not None:  # Explicit check
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Convert mm -> feet
                                break
                            else:
                                forms.alert("Error: panel_length_mm is not defined.")
                                return
                        else:
                            if interval_min_mm < 0:
                                prompt_message = (
                                    "Enter the value of X (in mm) for " + profile_symbol.Family.Name +
                                    " between [" +
                                    str(round(interval_max_mm + 63, 2)) + " , " +
                                    str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) + "]"
                                )
                            else:
                                prompt_message = (
                                    "The value of X must be between [94.5 , " +
                                    str(round(interval_min_mm, 2)) + "] or between [" +
                                    str(round(interval_max_mm, 2)) + " , " +
                                    str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) + "]"
                                )

                            # Ask again for the value of X
                            user_input_x_mm = forms.ask_for_string(
                                prompt=prompt_message,
                                title="Value of X"
                            )

                    except ValueError:
                        forms.alert("The value entered for X is not valid. Please enter a number.")
                else:
                    forms.alert("No value was entered for X.")
                    return

            insertion_point_y_ft = 294 / 304.8  # Y at the bottom

        elif profile_symbol.Family.Name == "PROFILE_PLN_175_V":
            while True:
                # Define the minimum and maximum interval
                interval_min_mm = right_value_mm - 31.5 - (num_profiles - 1) * distance_mm
                interval_max_mm = right_value_mm + l_window_value_mm + 31.5

                # Check if the space is insufficient
                available_space_left = interval_min_mm  # Space before the min
                available_space_right = panel_length_mm - interval_max_mm  # Space after the max
                required_space = (num_profiles - 1) * distance_mm  # Total required space

                if available_space_left < required_space and available_space_right < required_space:
                    forms.alert(
                        "Error: The available space is insufficient for " + str(num_profiles) +
                        " profiles with a distance of " + str(distance_mm) + " mm between them.\n" +
                        "Please reduce the number of profiles or decrease the distance between them."
                    )

                    # Ask the user for new values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new distance between profiles (in mm):",
                        title="Distance between profiles"
                    )

                    if user_input_num_profiles and user_input_distance_mm:
                        try:
                            num_profiles = int(user_input_num_profiles)
                            distance_mm = float(user_input_distance_mm)
                            continue  # Recalculate with the new values
                        except ValueError:
                            forms.alert("Invalid value. Please enter valid numbers.")
                            continue  # Ask again
                    else:
                        forms.alert("No value entered. Operation cancelled.")
                        break  # Exit if the user does not want to enter new values

                # Ask for the X position
                user_input_x_mm = forms.ask_for_string(
                    prompt="The value of X must be between [" + str(round(interval_max_mm, 2)) +
                           " , " + str(round(interval_min_mm, 2)) +
                           "] or between [" + str(round(interval_max_mm + 63, 2)) +
                           " , " + str(round(panel_length_mm - (num_profiles - 1) * distance_mm, 2)) +
                           " ]",
                    title="Value of X"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Strict check: X must be BEFORE the min or AFTER the max while respecting the incrementation
                        if (position_x_mm < interval_min_mm and position_x_mm > 0) or \
                           (position_x_mm > interval_max_mm and (position_x_mm + (num_profiles - 1) * distance_mm) <= panel_length_mm):

                            if panel_length_mm is not None:  # Explicit check
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Convert mm -> feet
                                break
                            else:
                                forms.alert("Error: panel_length_mm is not defined.")
                                return
                        else:
                            forms.alert(
                                "The value of X must be between [" + str(round(interval_max_mm, 2)) +
                                " , " + str(round(interval_min_mm, 2)) +
                                "] or between [" + str(round(interval_max_mm + 63, 2)) +
                                " , " + str(round(panel_length_mm - (num_profiles - 1) * distance_mm, 2)) +
                                "]"
                            )

                    except ValueError:
                        forms.alert("The value entered for X is not valid. Please enter a number.")
                else:
                    forms.alert("No value was entered for X.")
                    return
            insertion_point_y_ft = 319.5 / 304.8  # Y at the bottom

        elif profile_symbol.Family.Name == "PROFILE_PLN_225_V":
            while True:
                # Define the minimum and maximum interval
                interval_min_mm = right_value_mm - 31.5 - (num_profiles - 1) * distance_mm
                interval_max_mm = right_value_mm + l_window_value_mm + 31.5

                # Check if the space is insufficient
                available_space_left = interval_min_mm  # Space before the min
                available_space_right = panel_length_mm - interval_max_mm  # Space after the max
                required_space = (num_profiles - 1) * distance_mm  # Total required space

                if available_space_left < required_space and available_space_right < required_space:
                    forms.alert(
                        "Error: The available space is insufficient for " + str(num_profiles) +
                        " profiles with a distance of " + str(distance_mm) + " mm between them.\n" +
                        "Please reduce the number of profiles or decrease the distance between them."
                    )

                    # Ask the user for new values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new distance between profiles (in mm):",
                        title="Distance between profiles"
                    )

                    if user_input_num_profiles and user_input_distance_mm:
                        try:
                            num_profiles = int(user_input_num_profiles)
                            distance_mm = float(user_input_distance_mm)
                            continue  # Recalculate with the new values
                        except ValueError:
                            forms.alert("Invalid value. Please enter valid numbers.")
                            continue  # Ask again
                    else:
                        forms.alert("No value entered. Operation cancelled.")
                        break  # Exit if the user does not want to enter new values

                # ✅ Ask for the value of X
                if interval_min_mm < 0:
                    # If interval_min_mm is negative, only display the part "after interval_max_mm"
                    prompt_message = (
                        "Enter the value of X (in mm) for " + profile_symbol.Family.Name +
                        " between [" +
                        str(round(interval_max_mm + 63, 2)) + " , " +
                        str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) + "]"
                    )
                else:
                    # Otherwise, display both options (before interval_min_mm or after interval_max_mm)
                    prompt_message = (
                        "The value of X must be between [94.5 , " +
                        str(round(interval_min_mm, 2)) + "] or between [" +
                        str(round(interval_max_mm, 2)) + " , " +
                        str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) + "]"
                    )

                # Ask the user for the value of X
                user_input_x_mm = forms.ask_for_string(
                    prompt=prompt_message,
                    title="Value of X"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Strict check: X must be BEFORE the min or AFTER the max while respecting the incrementation
                        if (position_x_mm < interval_min_mm and position_x_mm >= 0) or \
                           (position_x_mm > interval_max_mm and (position_x_mm + (num_profiles - 1) * distance_mm) <= panel_length_mm):

                            if panel_length_mm is not None:  # Explicit check
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Convert mm -> feet
                                break
                            else:
                                forms.alert("Error: panel_length_mm is not defined.")
                                return
                        else:
                            forms.alert(
                                "The value of X must be between [94.5 , " +
                                str(round(interval_min_mm, 2)) + "] or between [" +
                                str(round(interval_max_mm, 2)) + " , " +
                                str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) + "]"
                            )
                    except ValueError:
                        forms.alert("The value entered for X is not valid. Please enter a number.")
                else:
                    forms.alert("No value was entered for X.")
                    return
            insertion_point_y_ft = 344.5 / 304.8  # Y at the bottom

        # If only one profile is to be added, exit the loop after the first insertion
        if num_profiles == 1:
            with Transaction(family_doc, "Add profile to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                # Insert at the adjusted position
                insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)
                family_instance = family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)

                # Save the information to the CSV file
                save_to_csv(profile_symbol.Family.Name, insertion_point_x_ft * 304.8, insertion_point_y_ft * 304.8,
                            insertion_point_z_ft * 304.8, distance_mm)

                t.Commit()

        # If multiple profiles need to be added, use a loop
        else:
            with Transaction(family_doc, "Add profiles to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                for i in range(num_profiles):
                    # For the first profile, do not increment
                    if i > 0:
                        # Increment the X position if it is not an H-type profile
                        if profile_symbol.Family.Name not in ["PROFILE_PLN_124_H", "PROFILE_PLN_175_H", "PROFILE_PLN_225_H"]:
                            insertion_point_x_ft += distance_mm / 304.8  # Convert mm to feet

                        # Increment the Z position if it is an H-type profile
                        if profile_symbol.Family.Name in ["PROFILE_PLN_124_H", "PROFILE_PLN_175_H", "PROFILE_PLN_225_H"]:
                            insertion_point_z_ft += distance_mm / 304.8  # Increment the Z position

                    # Insert at the adjusted position
                    insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)
                    family_instance = family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol,
                                                                                StructuralType.NonStructural)
                    # Save the information to the CSV file
                    save_to_csv(profile_symbol.Family.Name, insertion_point_x_ft * 304.8, insertion_point_y_ft * 304.8,
                                insertion_point_z_ft * 304.8, distance_mm)

                t.Commit()

        # Save the family only if profiles have been added
        if num_profiles > 0:
            family_doc.Save()

    except Exception as e:
        forms.alert("Error adding profiles to family : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)





def main():
    """Point d'entrée principal pour l'ajout de profils à un panneau."""
    panel = select_panel()
    if panel is None:
        return

    panel_length_mm = get_panel_length_from_project(panel)
    if panel_length_mm is None:
        return

    # Ouvrir la famille dans l'éditeur de famille
    family_doc = open_family_in_editor(panel)
    if family_doc is None:
        return

    insertion_method = forms.ask_for_one_item(
        ["Insert Custom Profiles", "Insert Profiles for Opening Frame"],
        default="Insert Custom Profiles",
        title="Select Insertion Method",
        prompt="Choose an option:"
    )

    if not insertion_method:
        return

    if insertion_method == 'Insert Custom Profiles':
        # Existing workflow
        profile_symbol = select_profile_symbol(family_doc)
        if not profile_symbol:
            return

        # Get user input for profiles
        image_path = r"C:\Users\wiemb\Desktop\PyRevit\MyExtension.extension\Tutto Plenum.png"
        num_profiles, distance_mm = get_profiles_input(image_path)
        if None in (num_profiles, distance_mm):
            return

        panel_length_mm = get_panel_length_from_project(panel)
        add_profiles_to_family(family_doc, profile_symbol, panel_length_mm, int(num_profiles), int(distance_mm))

    else:
        # Default PROFILE_PLN_124_V workflow
        collector = FilteredElementCollector(family_doc).OfClass(FamilySymbol)
        profile_symbols = [sym for sym in collector if sym.Family.Name == "PROFILE_PLN_124_V"]

        if not profile_symbols:
            forms.alert("PROFILE_PLN_124_V family not found.", exitscript=True)
        profile_symbol = profile_symbols[0]

        # Récupérer les valeurs de SILL, LINTEL, LEFT, et L_WINDOW
        sill_param = panel.LookupParameter("SILL")
        right_param = panel.LookupParameter("RIGHT")
        lintel_param = panel.LookupParameter("LINTEL")
        left_param = panel.LookupParameter("LEFT")
        l_window_param = panel.LookupParameter("L_WINDOW")

        if not sill_param or not right_param or not lintel_param or not left_param or not l_window_param:
            TaskDialog.Show("Erreur", "Les paramètres SILL, RIGHT, LINTEL, LEFT ou L_WINDOW sont introuvables dans le panneau.")
            return

        right_value_ft = right_param.AsDouble()
        l_window_value_ft = l_window_param.AsDouble()

        # Convertir en millimètres
        right_value_mm = right_value_ft * 304.8
        l_window_value_mm = l_window_value_ft * 304.8
        half_panel_length_mm = panel_length_mm / 2
        # Calculer les positions min et max
        intervalle_min_mm = right_value_mm + 31.5 - half_panel_length_mm
        intervalle_max_mm = right_value_mm + l_window_value_mm - 31.5 - half_panel_length_mm

        # Convertir en pieds pour Revit
        intervalle_min_ft = intervalle_min_mm / 304.8
        intervalle_max_ft = intervalle_max_mm / 304.8

        # Y position en pieds (fixe pour les profils)
        insertion_point_y_ft = 294 / 304.8

        # Créer les instances de profil
        with Transaction(family_doc, "Add Default Profiles") as t:
            t.Start()
            if not profile_symbol.IsActive:
                profile_symbol.Activate()

            # Créer une instance à x = min
            insertion_point_min = XYZ(intervalle_min_ft, insertion_point_y_ft , 0)
            family_doc.FamilyCreate.NewFamilyInstance(insertion_point_min, profile_symbol, StructuralType.NonStructural)

            # Créer une instance à x = max
            insertion_point_max = XYZ(intervalle_max_ft, insertion_point_y_ft, 0)
            family_doc.FamilyCreate.NewFamilyInstance(insertion_point_max, profile_symbol, StructuralType.NonStructural)

            t.Commit()

    # Sauvegarder et recharger la famille
    family_doc.Save()
    load_family_back_to_project(family_doc)

# Exécute le script
main()







