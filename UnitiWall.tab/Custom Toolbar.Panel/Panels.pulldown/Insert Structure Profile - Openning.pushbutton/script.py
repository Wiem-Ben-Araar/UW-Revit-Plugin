# -*- coding: utf-8 -*-
"""
Description:
This script facilitates the addition of structural profiles to a curtain wall panel in Revit. It offers two insertion modes:

1.Custom Mode: Allows the user to select existing profiles, define the count, spacing, and Z-position.

2.Default Mode: Automatically inserts two horizontal profiles (PROFILE_STR_152_H) to create the frame of the opening.

How to Use:

1.Select a Panel: The user selects a curtain wall panel from the project.

2.Choose Insertion Method:

  .Existing Profiles: Follow the custom workflow to select a profile, specify the count, spacing, and Z-value.

  .Default Profiles: Automatically inserts two PROFILE_STR_152_H profiles for the opening frame.

 .Add Profiles: The profiles are added, and the family is reloaded into the project.

Version: v3
Authors: Wiem Ben Araar, Amira Dridi
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
    SizeType, ColumnStyle, RowStyle, PictureBoxSizeMode
)
from System.Drawing import Image, ContentAlignment, Size


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

# --- This is the modified ProfilesInputForm class with larger UI ---

class ProfilesInputForm(Form):
    """
    Interface utilisateur élégante et professionnelle avec:
    - Une image principale au centre
    - Des champs de saisie stylisés
    - Des boutons modernes
    """

    def __init__(self, image_path):
        super(ProfilesInputForm, self).__init__()

        # Configuration de base de la fenêtre
        self.Text = "Adding profiles to the panel"
        self.Width = 1200
        self.Height = 800
        self.StartPosition = FormStartPosition.CenterScreen
        self.BackColor = System.Drawing.Color.FromArgb(240, 240, 245)  # Fond subtil
        self.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog
        self.MaximizeBox = False
        self.MinimizeBox = True
        self.Icon = System.Drawing.Icon.ExtractAssociatedIcon(System.Windows.Forms.Application.ExecutablePath)

        # Création du tableau principal avec une seule cellule pour le contenu
        self.mainLayout = TableLayoutPanel()
        self.mainLayout.Dock = DockStyle.Fill
        self.mainLayout.ColumnCount = 1
        self.mainLayout.RowCount = 1
        self.mainLayout.Padding = System.Windows.Forms.Padding(30)
        self.Controls.Add(self.mainLayout)

        # Panneau de contenu avec ombre
        self.contentPanel = System.Windows.Forms.Panel()
        self.contentPanel.BackColor = System.Drawing.Color.White
        self.contentPanel.Dock = DockStyle.Fill
        # Ajouter une ombre au panneau
        self.contentPanel.Paint += self.AddShadow
        self.mainLayout.Controls.Add(self.contentPanel, 0, 0)

        # Organisation du contenu dans le panneau
        self.contentLayout = TableLayoutPanel()
        self.contentLayout.Dock = DockStyle.Fill
        self.contentLayout.ColumnCount = 1
        self.contentLayout.RowCount = 3
        self.contentLayout.Padding = System.Windows.Forms.Padding(25)
        self.contentLayout.RowStyles.Add(RowStyle(SizeType.Percent, 70))  # Image (70%)
        self.contentLayout.RowStyles.Add(RowStyle(SizeType.Percent, 20))  # Champs (20%)
        self.contentLayout.RowStyles.Add(RowStyle(SizeType.Percent, 10))  # Boutons (10%)
        self.contentPanel.Controls.Add(self.contentLayout)

        # --- Zone de l'image ---
        self.imagePanel = System.Windows.Forms.Panel()
        self.imagePanel.Dock = DockStyle.Fill
        self.imagePanel.Padding = System.Windows.Forms.Padding(20)
        self.imagePanel.BackColor = System.Drawing.Color.FromArgb(245, 245, 250)
        self.contentLayout.Controls.Add(self.imagePanel, 0, 0)

        # Image avec bordure
        self.pictureBox = PictureBox()
        self.pictureBox.Dock = DockStyle.Fill
        self.pictureBox.SizeMode = PictureBoxSizeMode.Zoom
        self.pictureBox.Paint += self.AddImageBorder
        try:
            self.pictureBox.Image = Image.FromFile(image_path)
        except Exception as e:
            print("Error loading image: " + str(e))
            self.pictureBox.BackColor = System.Drawing.Color.LightGray
        self.imagePanel.Controls.Add(self.pictureBox)

        # --- Zone des champs de saisie ---
        self.inputPanel = TableLayoutPanel()
        self.inputPanel.Dock = DockStyle.Fill
        self.inputPanel.ColumnCount = 2
        self.inputPanel.RowCount = 2
        self.inputPanel.ColumnStyles.Add(ColumnStyle(SizeType.Percent, 50))
        self.inputPanel.ColumnStyles.Add(ColumnStyle(SizeType.Percent, 50))
        self.contentLayout.Controls.Add(self.inputPanel, 0, 1)

        # Champ 1: Nombre de profils
        self.createInputField(0, "Number of profiles", "1")

        # Champ 2: Distance entre profils
        self.createInputField(1, "Distance between profiles (mm)", "100")

        # --- Zone des boutons ---
        self.buttonPanel = FlowLayoutPanel()
        self.buttonPanel.Dock = DockStyle.Fill
        self.buttonPanel.FlowDirection = System.Windows.Forms.FlowDirection.RightToLeft
        self.contentLayout.Controls.Add(self.buttonPanel, 0, 2)

        # Bouton Annuler
        self.cancelButton = self.createStyledButton("Cancel", System.Drawing.Color.FromArgb(245, 245, 245),
                                                    DialogResult.Cancel)
        self.buttonPanel.Controls.Add(self.cancelButton)

        # Bouton OK
        self.okButton = self.createStyledButton("OK", System.Drawing.Color.FromArgb(63, 81, 181), DialogResult.OK)
        self.okButton.ForeColor = System.Drawing.Color.White
        self.buttonPanel.Controls.Add(self.okButton)

        # Association des boutons
        self.AcceptButton = self.okButton
        self.CancelButton = self.cancelButton

    def AddShadow(self, sender, e):
        """Ajoute une ombre douce au panneau de contenu"""
        control = sender
        g = e.Graphics
        rect = System.Drawing.Rectangle(0, 0, control.Width, control.Height)
        g.FillRectangle(System.Drawing.SolidBrush(System.Drawing.Color.White), rect)

        # Dessiner une bordure très légère
        pen = System.Drawing.Pen(System.Drawing.Color.FromArgb(220, 220, 220), 1)
        g.DrawRectangle(pen, 0, 0, control.Width - 1, control.Height - 1)

    def AddImageBorder(self, sender, e):
        """Ajoute une bordure élégante à l'image"""
        control = sender
        g = e.Graphics
        rect = System.Drawing.Rectangle(0, 0, control.Width - 1, control.Height - 1)

        # Dessiner une bordure
        pen = System.Drawing.Pen(System.Drawing.Color.FromArgb(200, 200, 200), 1)
        g.DrawRectangle(pen, rect)

    def createInputField(self, index, labelText, defaultValue):
        """Crée un champ de saisie stylisé avec étiquette"""
        # Panneau pour grouper l'étiquette et le champ
        fieldPanel = System.Windows.Forms.Panel()
        fieldPanel.Dock = DockStyle.Fill
        fieldPanel.Padding = System.Windows.Forms.Padding(10)
        self.inputPanel.Controls.Add(fieldPanel, 0 if index == 0 else 1, 0)

        # Disposition verticale pour l'étiquette et le champ
        fieldLayout = TableLayoutPanel()
        fieldLayout.Dock = DockStyle.Fill
        fieldLayout.ColumnCount = 1
        fieldLayout.RowCount = 2
        fieldLayout.RowStyles.Add(RowStyle(SizeType.Absolute, 30))
        fieldLayout.RowStyles.Add(RowStyle(SizeType.Absolute, 40))
        fieldPanel.Controls.Add(fieldLayout)

        # Étiquette
        label = Label()
        label.Text = labelText
        label.Font = System.Drawing.Font("Segoe UI", 10, System.Drawing.FontStyle.Regular)
        label.ForeColor = System.Drawing.Color.FromArgb(80, 80, 80)
        label.Dock = DockStyle.Fill
        label.TextAlign = ContentAlignment.BottomLeft
        fieldLayout.Controls.Add(label, 0, 0)

        # Champ de texte
        textBox = TextBox()
        textBox.Text = defaultValue
        textBox.Font = System.Drawing.Font("Segoe UI", 12)
        textBox.Dock = DockStyle.Fill
        textBox.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle
        fieldLayout.Controls.Add(textBox, 0, 1)

        # Stocker la référence au champ
        if index == 0:
            self.textBoxNumProfiles = textBox
        else:
            self.textBoxDistance = textBox

    def createStyledButton(self, text, color, dialogResult):
        """Crée un bouton stylisé avec effet de survol"""
        button = Button()
        button.Text = text
        button.BackColor = color
        button.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        button.FlatAppearance.BorderSize = 0
        button.Font = System.Drawing.Font("Segoe UI", 11)
        button.Size = System.Drawing.Size(150, 45)
        button.Margin = System.Windows.Forms.Padding(10, 5, 10, 5)
        button.DialogResult = dialogResult
        button.Cursor = System.Windows.Forms.Cursors.Hand

        # Ajouter les événements de survol
        button.MouseEnter += self.button_MouseEnter
        button.MouseLeave += self.button_MouseLeave

        return button

    def button_MouseEnter(self, sender, e):
        """Effet de survol: assombrir légèrement le bouton"""
        button = sender
        original_color = button.BackColor
        r = max(0, original_color.R - 20)
        g = max(0, original_color.G - 20)
        b = max(0, original_color.B - 20)
        button.BackColor = System.Drawing.Color.FromArgb(r, g, b)

    def button_MouseLeave(self, sender, e):
        """Rétablir la couleur d'origine au départ du survol"""
        button = sender
        if button == self.okButton:
            button.BackColor = System.Drawing.Color.FromArgb(63, 81, 181)
        else:
            button.BackColor = System.Drawing.Color.FromArgb(245, 245, 245)


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
        TaskDialog.Show("Error", "An error occurred while selecting the panel : {}".format(e))
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
        TaskDialog.Show("Error", "An error occurred while getting the length: {}".format(e))
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
        profiles = {f.Id: f for f in collector if "STR" in f.Family.Name and "WIN" not in f.Family.Name }

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
    """Adds multiple instances of the selected profile to the family with a specific position, taking into account the panel width."""
    try:
        # Initial position
        insertion_point_x_ft = 0
        insertion_point_y_ft = 0
        insertion_point_z_ft = 0
        # Get SILL and LINTEL values for the Z constraints
        panel = select_panel()
        if not panel:
            TaskDialog.Show("Error", "No panel selected.")
            return
        sill_param = panel.LookupParameter("SILL")
        right_param = panel.LookupParameter("RIGHT")
        lintel_param = panel.LookupParameter("LINTEL")
        left_param = panel.LookupParameter("LEFT")
        l_window_param = panel.LookupParameter("L_WINDOW")
        h_panneau_param = panel.LookupParameter("H_PANNEAU")

        if not sill_param or not lintel_param or not left_param or not l_window_param:
            TaskDialog.Show("Error",
                            "The parameters SILL, LINTEL, LEFT or L_WINDOW are not found in the panel.")
            return

        sill_value_ft = sill_param.AsDouble()  # SILL value in feet
        right_value_ft = right_param.AsDouble()
        lintel_value_ft = lintel_param.AsDouble()  # LINTEL value in feet
        left_value_ft = left_param.AsDouble()  # LEFT value in feet
        l_window_value_ft = l_window_param.AsDouble()  # L_WINDOW value in feet
        h_panneau_value_ft = h_panneau_param.AsDouble()
        # Convert LEFT and L_WINDOW to millimeters for display
        left_value_mm = left_value_ft * 304.8
        h_panneau_value_mm = h_panneau_value_ft * 304.8

        l_window_value_mm = l_window_value_ft * 304.8
        right_value_mm = right_value_ft * 304.8
        # Specific conditions for each profile

        if profile_symbol.Family.Name == "PROFILE_STR_152_V_RENFORT":
            # Ask the user for the new X position in mm
            user_input_x_mm = forms.ask_for_string(
                prompt="Enter the new X position (in mm) for PROFILE_STR_152_V_RENFORT",
                title="Value of X"
            )
            while True:
                # Define the minimal and maximal interval
                intervalle_min_mm = right_value_mm - 32 - (num_profiles - 1) * distance_mm
                intervalle_max_mm = right_value_mm + l_window_value_mm + 32

                # Check if space is insufficient
                espace_disponible_gauche = intervalle_min_mm  # Space before the min
                espace_disponible_droite = panel_length_mm - intervalle_max_mm  # Space after the max
                espace_requis = (num_profiles - 1) * distance_mm  # Total space required

                if espace_disponible_gauche < espace_requis and espace_disponible_droite < espace_requis:
                    forms.alert(
                        "Error: Not enough space available for " + str(num_profiles) +
                        " profiles with a spacing of " + str(distance_mm) + " mm between them.\n" +
                        "Please reduce the number of profiles or decrease the spacing between them."
                    )

                    # Ask for new values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new spacing between profiles (in mm):",
                        title="Spacing between profiles"
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
                        break  # Exit if the user cancels

                # Ask for the X position
                user_input_x_mm = forms.ask_for_string(
                    prompt="Enter the X value (in mm) for " + profile_symbol.Family.Name +
                           " (before " + str(round(intervalle_min_mm, 2)) + " mm or after " +
                           str(round(intervalle_max_mm, 2)) + " mm) while respecting the available space.",
                    title="X Value"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Strict check: X must be BEFORE min or AFTER max while accounting for the spacing
                        if (position_x_mm < intervalle_min_mm and position_x_mm >= 0) or \
                           (position_x_mm > intervalle_max_mm and (position_x_mm + (num_profiles - 1) * distance_mm) <= panel_length_mm):

                            if panel_length_mm is not None:  # Explicit check
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Convert mm to feet
                                break
                            else:
                                forms.alert("Error: panel_length_mm is not defined.")
                                return
                        else:
                            forms.alert(
                                "The X value must be BETWEEN 0 and " +
                                str(round(intervalle_min_mm, 2)) + " mm or between " +
                                str(round(intervalle_max_mm, 2)) + " mm and " +
                                str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) +
                                " mm while taking the spacing into account."
                            )
                    except ValueError:
                        forms.alert("The value entered for X is not valid. Please enter a number.")
                else:
                    forms.alert("No value was entered for X.")
                    return

            insertion_point_y_ft = 82 / 304.8  # Y offset
        elif profile_symbol.Family.Name == "PROFILE_STR_152_V":
            while True:
                # Define the minimal and maximal interval
                intervalle_min_mm = right_value_mm - 32 - (num_profiles - 1) * distance_mm
                intervalle_max_mm = right_value_mm + l_window_value_mm + 32

                # Check if space is insufficient
                espace_disponible_gauche = intervalle_min_mm  # Space before the min
                espace_disponible_droite = panel_length_mm - intervalle_max_mm  # Space after the max
                espace_requis = (num_profiles - 1) * distance_mm  # Total space required

                if espace_disponible_gauche < espace_requis and espace_disponible_droite < espace_requis:
                    forms.alert(
                        "Error: Not enough space available for " + str(num_profiles) +
                        " profiles with a spacing of " + str(distance_mm) + " mm between them.\n" +
                        "Please reduce the number of profiles or decrease the spacing between them."
                    )

                    # Ask for new values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new spacing between profiles (in mm):",
                        title="Spacing between profiles"
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
                        break  # Exit if the user cancels

                # Ask for the X position
                user_input_x_mm = forms.ask_for_string(
                    prompt="Enter the X value (in mm) for " + profile_symbol.Family.Name +
                           " (before " + str(round(intervalle_min_mm, 2)) + " mm or after " +
                           str(round(intervalle_max_mm, 2)) + " mm) while respecting the available space.",
                    title="X Value"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Strict check: X must be BEFORE min or AFTER max while accounting for the spacing
                        if (position_x_mm < intervalle_min_mm and position_x_mm >= 0) or \
                           (position_x_mm > intervalle_max_mm and (position_x_mm + (num_profiles - 1) * distance_mm) <= panel_length_mm):

                            if panel_length_mm is not None:  # Explicit check
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Convert mm to feet
                                break
                            else:
                                forms.alert("Error: panel_length_mm is not defined.")
                                return
                        else:
                            forms.alert(
                                "The X value must be BETWEEN 0 and " +
                                str(round(intervalle_min_mm, 2)) + " mm or between " +
                                str(round(intervalle_max_mm, 2)) + " mm and " +
                                str(round(panel_length_mm - ((num_profiles - 1) * distance_mm))) +
                                " mm while taking the spacing into account."
                            )
                    except ValueError:
                        forms.alert("The value entered for X is not valid. Please enter a number.")
                else:
                    forms.alert("No value was entered for X.")
                    return
        insertion_point_y_ft = 126 / 304.8  # Y offset
        # Ask for the Z value for the appropriate profiles
        if profile_symbol.Family.Name in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
            insertion_point_y_ft = 126 / 304.8  # Y offset
            while True:
                # ✅ Ensure that z_max_mm is greater than z_min_mm before continuing
                z_max_mm = (lintel_value_ft * 304.8) - 32
                z_min_mm = (sill_value_ft * 304.8) + 32 - ((num_profiles - 1) * distance_mm)
                espace_disponible_bas = z_min_mm  # Space before the min
                espace_disponible_haut = h_panneau_value_mm - z_max_mm  # Space after the max
                espace_requis = (num_profiles - 1) * distance_mm  # Total space required

                if espace_disponible_bas < espace_requis and espace_disponible_haut < espace_requis:
                    forms.alert(
                        "Error: Not enough space available for " + str(num_profiles) +
                        " profiles with a spacing of " + str(distance_mm) + " mm between them.\n" +
                        "Please reduce the number of profiles or decrease the spacing between them."
                    )
                    # ✅ Allow the user to change the values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new spacing between profiles (in mm):",
                        title="Spacing between profiles"
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
                        break  # Exit if the user cancels
                # ✅ Ask for the Z value
                if z_min_mm < 0:
                    # If z_min_mm is negative, only show the option "after z_max_mm"
                    prompt_message = (
                        "Enter the Z value (in mm) for " + profile_symbol.Family.Name +
                        " between [" + str(round(z_max_mm + 64, 2)) + " , " +
                        str(round(h_panneau_value_mm - ((num_profiles - 1) * distance_mm)) - 32) +
                        " ]"
                    )
                else:
                    # Otherwise, show both options (before z_min_mm or after z_max_mm)
                    prompt_message = (
                        "Enter the Z value (in mm) for " + profile_symbol.Family.Name +
                        " between [96 , " + str(round(z_min_mm, 2) ) + "] or between [" +
                        str(round(z_max_mm + 64, 2)) + " , " +
                        str(round(h_panneau_value_mm - ((num_profiles - 1) * distance_mm)) - 32) +
                        " ]"
                    )

                user_input_z_mm = forms.ask_for_string(
                    prompt=prompt_message,
                    title="Z Value"
                )

                # If the user cancels or does not enter a value, cancel the operation
                if not user_input_z_mm:
                    forms.alert("No value was entered for Z. Operation cancelled.")
                    return  # Arrêt immédiat de la fonction

                try:
                    insertion_point_z_mm = float(user_input_z_mm)
                    insertion_point_z_ft = insertion_point_z_mm / 304.8  # Convert to feet

                    if (insertion_point_z_mm < z_min_mm and insertion_point_z_mm >= 0) or \
                            (insertion_point_z_mm > z_max_mm and (
                                    insertion_point_z_mm + (num_profiles - 1) * distance_mm) <= h_panneau_value_mm):
                        break  # Correct value, exit loop
                    else:
                        # ✅ Ask again for the Z value
                        if z_min_mm < 0:
                            prompt_message = (
                                "Enter the Z value (in mm) for " + profile_symbol.Family.Name +
                                " between [" + str(round(z_max_mm + 64, 2)) + " , " +
                                str(round(h_panneau_value_mm - ((num_profiles - 1) * distance_mm)) - 32) +
                                " ]"
                            )
                        else:
                            prompt_message = (
                                "Enter the Z value (in mm) for " + profile_symbol.Family.Name +
                                " between [96 , " + str(round(z_min_mm, 2) ) + "] or between [" +
                                str(round(z_max_mm + 64, 2)) + " , " +
                                str(round(h_panneau_value_mm - ((num_profiles - 1) * distance_mm)) - 32) +
                                " ]"
                            )

                        user_input_z_mm = forms.ask_for_string(
                            prompt=prompt_message,
                            title="Z Value"
                        )
                except ValueError:
                    forms.alert("Error: The value entered for Z is not valid. Please enter a number.")

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

        # If multiple profiles are to be added, use a loop
        else:
            with Transaction(family_doc, "Add profiles to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                for i in range(num_profiles):
                    # For the first profile, do not increment
                    if i > 0:
                        # Increment the X position if not an H-type profile
                        if profile_symbol.Family.Name not in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
                            insertion_point_x_ft += distance_mm / 304.8  # Convert mm to feet

                        # Increment the Z position if it is an H-type profile
                        if profile_symbol.Family.Name in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
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
        forms.alert("Error adding profiles to family: {}\nTraceback: {}".format(e, traceback.format_exc()), exitscript=True)

def main():
    """Main entry point for profile addition."""
    # 1. Panel selection
    panel = select_panel()
    if not panel:
        return

    # 2. Open family document
    family_doc = open_family_in_editor(panel)
    if not family_doc:
        return

    # 3. Insertion method selection
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
        image_path = r"C:\Users\wiemb\Desktop\PyRevit\MyExtension.extension\Tutto Structure.png"
        num_profiles, distance_mm = get_profiles_input(image_path)
        if None in (num_profiles, distance_mm):
            return

        panel_length_mm = get_panel_length_from_project(panel)
        add_profiles_to_family(family_doc, profile_symbol, panel_length_mm, int(num_profiles), int(distance_mm))

    else:
        # Default PROFILE_STR_152_H workflow
        collector = FilteredElementCollector(family_doc).OfClass(FamilySymbol)
        profile_symbols = [sym for sym in collector if sym.Family.Name == "PROFILE_STR_152_H"]

        if not profile_symbols:
            forms.alert("PROFILE_STR_152_H family not found.", exitscript=True)
        profile_symbol = profile_symbols[0]

        # Get Z positions
        sill_param = panel.LookupParameter("SILL")
        lintel_param = panel.LookupParameter("LINTEL")
        if not sill_param or not lintel_param:
            forms.alert("Required parameters not found.", exitscript=True)

        z_min = sill_param.AsDouble() + (32 / 304.8)
        z_max = lintel_param.AsDouble() - (32 / 304.8)

        # Create instances
        with Transaction(family_doc, "Add Default Profiles") as t:
            t.Start()
            if not profile_symbol.IsActive:
                profile_symbol.Activate()

            # Create instances at calculated positions
            insertion_point = XYZ(0, 126 / 304.8, z_min)
            family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)

            insertion_point = XYZ(0, 126 / 304.8, z_max)
            family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)

            t.Commit()

    # Save and reload family
    family_doc.Save()
    load_family_back_to_project(family_doc)


# The rest of your existing helper functions remain unchanged here...

if __name__ == "__main__":
    main()