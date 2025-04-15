# -*- coding: utf-8 -*-
"""
Description:
This script allows adding profiles, including a structural profile, to a curtain wall panel in Revit.

How to use:
1. Select a panel: The user selects a curtain wall panel from the project.
2. Choose insertion method: Insert existing profiles or default PROFILE_STR_152_H at min/max Z positions.
3a. For existing profiles: Follow existing workflow (select profile, specify count/distance).
3b. For default profiles: Automatically insert two profiles at calculated Z positions.
4. Profiles are added and family reloaded into the project.

Version: v3
Author: Your Name
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

class ProfilesInputForm(Form):
    """
    Fenêtre personnalisée permettant de saisir :
    - le nombre de profils
    - la distance entre les profils (en mm)
    - avec une image explicative en haut
    """

    def __init__(self, image_path):
        super(ProfilesInputForm, self).__init__()

        # Configuration basique de la fenêtre
        self.Text = "Add Profiles to Panel"
        self.Width = 600
        self.Height = 400
        self.StartPosition = FormStartPosition.CenterScreen

        # --- TableLayoutPanel pour organiser l'UI en grille ---
        self.tableLayout = TableLayoutPanel()
        self.tableLayout.Dock = DockStyle.Fill
        self.tableLayout.ColumnCount = 2
        self.tableLayout.RowCount = 4

        # Largeur des colonnes (30% pour la première, 70% pour la deuxième)
        self.tableLayout.ColumnStyles.Add(ColumnStyle(SizeType.Percent, 30))
        self.tableLayout.ColumnStyles.Add(ColumnStyle(SizeType.Percent, 70))

        # Hauteur des lignes
        # 1) Ligne pour l'image (150 px de hauteur)
        # 2) Ligne pour "Number of Profiles" (AutoSize)
        # 3) Ligne pour "Distance" (AutoSize)
        # 4) Ligne pour les boutons (reçoit le FlowLayoutPanel)
        self.tableLayout.RowStyles.Add(RowStyle(SizeType.Absolute, 150))
        self.tableLayout.RowStyles.Add(RowStyle(SizeType.AutoSize))
        self.tableLayout.RowStyles.Add(RowStyle(SizeType.AutoSize))
        self.tableLayout.RowStyles.Add(RowStyle(SizeType.Absolute, 50))

        self.Controls.Add(self.tableLayout)

        # --- Image en haut (PictureBox) ---
        self.pictureBox = PictureBox()
        self.pictureBox.Dock = DockStyle.Fill
        self.pictureBox.SizeMode = PictureBoxSizeMode.Zoom
        try:
            self.pictureBox.Image = Image.FromFile(image_path)
        except:
            pass  # Gérer le cas où l'image n'est pas trouvée

        # Faire span sur 2 colonnes (pour occuper toute la largeur)
        self.tableLayout.SetColumnSpan(self.pictureBox, 2)
        self.tableLayout.Controls.Add(self.pictureBox, 0, 0)

        # --- Label : "How many profiles" ---
        self.labelNumProfiles = Label()
        self.labelNumProfiles.Text = "How many profiles do you want to add?"
        self.labelNumProfiles.TextAlign = ContentAlignment.MiddleRight
        self.labelNumProfiles.AutoSize = True  # Activer AutoSize
        self.tableLayout.Controls.Add(self.labelNumProfiles, 0, 1)

        # --- TextBox pour le nombre de profils ---
        self.textBoxNumProfiles = TextBox()
        self.textBoxNumProfiles.Text = "1"  # Valeur par défaut
        self.tableLayout.Controls.Add(self.textBoxNumProfiles, 1, 1)

        # --- Label : "Distance between profiles" ---
        self.labelDistance = Label()
        self.labelDistance.Text = "Distance between the profiles (in mm)?"
        self.labelDistance.TextAlign = ContentAlignment.MiddleRight
        self.labelDistance.AutoSize = True  # Activer AutoSize
        self.tableLayout.Controls.Add(self.labelDistance, 0, 2)

        # --- TextBox pour la distance ---
        self.textBoxDistance = TextBox()
        self.textBoxDistance.Text = "100"  # Valeur par défaut
        self.tableLayout.Controls.Add(self.textBoxDistance, 1, 2)

        # --- FlowLayoutPanel pour les boutons (OK / Cancel) ---
        self.buttonPanel = FlowLayoutPanel()
        self.buttonPanel.FlowDirection = System.Windows.Forms.FlowDirection.RightToLeft
        self.buttonPanel.Dock = DockStyle.Fill
        self.tableLayout.SetColumnSpan(self.buttonPanel, 2)
        self.tableLayout.Controls.Add(self.buttonPanel, 0, 3)

        # --- Bouton OK ---
        self.okButton = Button()
        self.okButton.Text = "OK"
        self.okButton.DialogResult = DialogResult.OK
        self.buttonPanel.Controls.Add(self.okButton)

        # --- Bouton Cancel ---
        self.cancelButton = Button()
        self.cancelButton.Text = "Cancel"
        self.cancelButton.DialogResult = DialogResult.Cancel
        self.buttonPanel.Controls.Add(self.cancelButton)

        # Associer les boutons OK et Annuler
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
    """Ajoute plusieurs instances du profil sélectionné à la famille avec une position spécifique, en tenant compte de la largeur du panneau."""
    try:
        # Position initiale
        insertion_point_x_ft = 0
        insertion_point_y_ft = 0
        insertion_point_z_ft = 0
        # Récupérer les valeurs de SILL et LINTEL pour les contraintes de Z
        panel = select_panel()
        if not panel:
            TaskDialog.Show("Erreur", "Aucun panneau sélectionné.")
            return
        sill_param = panel.LookupParameter("SILL")
        right_param = panel.LookupParameter("RIGHT")
        lintel_param = panel.LookupParameter("LINTEL")
        left_param = panel.LookupParameter("LEFT")
        l_window_param = panel.LookupParameter("L_WINDOW")
        h_panneau_param = panel.LookupParameter("H_PANNEAU")

        if not sill_param or not lintel_param or not left_param or not l_window_param:
            TaskDialog.Show("Erreur",
                            "Les paramètres SILL, LINTEL, LEFT ou L_WINDOW sont introuvables dans le panneau.")
            return

        sill_value_ft = sill_param.AsDouble()  # Valeur de SILL en pieds
        right_value_ft = right_param.AsDouble()
        lintel_value_ft = lintel_param.AsDouble()  # Valeur de LINTEL en pieds
        left_value_ft = left_param.AsDouble()  # Valeur de LEFT en pieds
        l_window_value_ft = l_window_param.AsDouble()  # Valeur de L_WINDOW en pieds
        h_panneau_value_ft = h_panneau_param.AsDouble()
        # Convertir LEFT et L_WINDOW en millimètres pour l'affichage
        left_value_mm = left_value_ft * 304.8
        h_panneau_value_mm = h_panneau_value_ft * 304.8

        l_window_value_mm = l_window_value_ft * 304.8
        right_value_mm = right_value_ft * 304.8
        # Conditions spécifiques pour chaque profil

        if profile_symbol.Family.Name == "PROFILE_STR_152_V_RENFORT":
            # Demander à l'utilisateur d'entrer la position X en mm
            user_input_x_mm = forms.ask_for_string(
                prompt="Enter the new X position (in mm) for PROFILE_STR_152_V_RENFORT",
                title="Value of X"
            )
            while True:
                # Définition de l'intervalle minimal et maximal
                intervalle_min_mm = right_value_mm - 32 - (num_profiles - 1) * distance_mm
                intervalle_max_mm = right_value_mm + l_window_value_mm + 32

                # Vérification si l'espace est insuffisant
                espace_disponible_gauche = intervalle_min_mm  # Espace avant le min
                espace_disponible_droite = panel_length_mm - intervalle_max_mm  # Espace après le max
                espace_requis = (num_profiles - 1) * distance_mm  # Espace total nécessaire

                if espace_disponible_gauche < espace_requis and espace_disponible_droite < espace_requis:
                    forms.alert(
                        "Erreur : L'espace disponible est insuffisant pour " + str(num_profiles) +
                        " profilés avec une distance de " + str(distance_mm) + " mm entre eux.\n" +
                        "Veuillez réduire le nombre de profilés, diminuer la distance entre eux."
                    )

                    # Demander de nouvelles valeurs à l'utilisateur
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Entrez un nouveau nombre de profilés :",
                        title="Nombre de profilés"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Entrez une nouvelle distance entre les profilés (en mm) :",
                        title="Distance entre profilés"
                    )

                    if user_input_num_profiles and user_input_distance_mm:
                        try:
                            num_profiles = int(user_input_num_profiles)
                            distance_mm = float(user_input_distance_mm)
                            continue  # Recalculer avec les nouvelles valeurs
                        except ValueError:
                            forms.alert("Valeur invalide. Veuillez entrer des nombres valides.")
                            continue  # Redemander la saisie
                    else:
                        forms.alert("Aucune valeur saisie. Opération annulée.")
                        break  # Quitter si l'utilisateur ne veut pas saisir de nouvelles valeurs

                # Demander la position X
                user_input_x_mm = forms.ask_for_string(
                    prompt="Entrez la valeur de X (en mm) pour " + profile_symbol.Family.Name +
                           " (avant " + str(round(intervalle_min_mm, 2)) + " mm ou après " +
                           str(round(intervalle_max_mm, 2)) + " mm) tout en respectant l'espace disponible.",
                    title="Valeur de X"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Vérification stricte : X doit être AVANT min ou APRÈS max tout en respectant l'incrémentation
                        if (position_x_mm < intervalle_min_mm and (
                                position_x_mm) >= 0) or \
                                (position_x_mm > intervalle_max_mm and (
                                        position_x_mm + (num_profiles - 1) * distance_mm) <= panel_length_mm):

                            if panel_length_mm is not None:  # Vérification explicite
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion mm -> pieds
                                break
                            else:
                                forms.alert("Erreur : panel_length_mm n'est pas défini.")
                                return
                        else:
                            forms.alert(
                                "La valeur de X doit être ENTRE 0 et " +
                                str(round(intervalle_min_mm, 2)) + " mm ou entre  " +
                                str(round(intervalle_max_mm, 2)) + " mm et" +
                                str(round(
                                    panel_length_mm - (
                                                num_profiles - 1) * distance_mm)) + " mm tout en tenant compte de l'incrémentation."
                            )
                    except ValueError:
                        forms.alert("La valeur saisie pour X n'est pas valide. Veuillez entrer un nombre.")
                else:
                    forms.alert("Aucune valeur n'a été saisie pour X.")
                    return

            insertion_point_y_ft = 82 / 304.8  # Décalage Y
        elif profile_symbol.Family.Name == "PROFILE_STR_152_V":
            while True:
                # Définition de l'intervalle minimal et maximal
                intervalle_min_mm = right_value_mm - 32 - (num_profiles - 1) * distance_mm
                intervalle_max_mm = right_value_mm + l_window_value_mm + 32

                # Vérification si l'espace est insuffisant
                espace_disponible_gauche = intervalle_min_mm  # Espace avant le min
                espace_disponible_droite = panel_length_mm - intervalle_max_mm  # Espace après le max
                espace_requis = (num_profiles - 1) * distance_mm  # Espace total nécessaire

                if espace_disponible_gauche < espace_requis and espace_disponible_droite < espace_requis:
                    forms.alert(
                        "Erreur : L'espace disponible est insuffisant pour " + str(num_profiles) +
                        " profilés avec une distance de " + str(distance_mm) + " mm entre eux.\n" +
                        "Veuillez réduire le nombre de profilés, diminuer la distance entre eux."
                    )

                    # Demander de nouvelles valeurs à l'utilisateur
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Entrez un nouveau nombre de profilés :",
                        title="Nombre de profilés"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Entrez une nouvelle distance entre les profilés (en mm) :",
                        title="Distance entre profilés"
                    )

                    if user_input_num_profiles and user_input_distance_mm:
                        try:
                            num_profiles = int(user_input_num_profiles)
                            distance_mm = float(user_input_distance_mm)
                            continue  # Recalculer avec les nouvelles valeurs
                        except ValueError:
                            forms.alert("Valeur invalide. Veuillez entrer des nombres valides.")
                            continue  # Redemander la saisie
                    else:
                        forms.alert("Aucune valeur saisie. Opération annulée.")
                        break  # Quitter si l'utilisateur ne veut pas saisir de nouvelles valeurs

                # Demander la position X
                user_input_x_mm = forms.ask_for_string(
                    prompt="Entrez la valeur de X (en mm) pour " + profile_symbol.Family.Name +
                           " (avant " + str(round(intervalle_min_mm, 2)) + " mm ou après " +
                           str(round(intervalle_max_mm, 2)) + " mm) tout en respectant l'espace disponible.",
                    title="Valeur de X"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Vérification stricte : X doit être AVANT min ou APRÈS max tout en respectant l'incrémentation
                        if (position_x_mm < intervalle_min_mm and (
                                position_x_mm) >= 0) or \
                                (position_x_mm > intervalle_max_mm and (
                                        position_x_mm + (num_profiles - 1) * distance_mm) <= panel_length_mm):

                            if panel_length_mm is not None:  # Vérification explicite
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion mm -> pieds
                                break
                            else:
                                forms.alert("Erreur : panel_length_mm n'est pas défini.")
                                return
                        else:
                            forms.alert(
                                "La valeur de X doit être ENTRE 0 et " +
                                str(round(intervalle_min_mm, 2)) + " mm ou entre  " +
                                str(round(intervalle_max_mm, 2)) + " mm et" +
                                str(round(
                                    panel_length_mm - (
                                                num_profiles - 1) * distance_mm)) + " mm tout en tenant compte de l'incrémentation."
                            )
                    except ValueError:
                        forms.alert("La valeur saisie pour X n'est pas valide. Veuillez entrer un nombre.")
                else:
                    forms.alert("Aucune valeur n'a été saisie pour X.")
                    return
        insertion_point_y_ft = 126 / 304.8  # Décalage Y
        # Demander la valeur de Z pour les profils appropriés
        if profile_symbol.Family.Name in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
            insertion_point_y_ft = 126 / 304.8  # Décalage Y
            while True:
                # ✅ Vérifier que z_max_mm est bien supérieur à z_min_mm avant de continuer
                z_max_mm = (lintel_value_ft * 304.8) - 32
                z_min_mm = (sill_value_ft * 304.8) + 32 - ((num_profiles - 1) * distance_mm)
                espace_disponible_bas = z_min_mm  # Espace avant le min
                espace_disponible_haut = h_panneau_value_mm - z_max_mm  # Espace après le max
                espace_requis = (num_profiles - 1) * distance_mm  # Espace total nécessaire

                if espace_disponible_bas < espace_requis and espace_disponible_haut < espace_requis:
                    forms.alert(
                        "Erreur : L'espace disponible est insuffisant pour " + str(num_profiles) +
                        " profilés avec une distance de " + str(distance_mm) + " mm entre eux.\n" +
                        "Veuillez réduire le nombre de profilés ou diminuer la distance entre eux."
                    )
                    # ✅ Permettre à l'utilisateur de modifier les valeurs
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Entrez un nouveau nombre de profilés :",
                        title="Nombre de profilés"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Entrez une nouvelle distance entre les profilés (en mm) :",
                        title="Distance entre profilés"
                    )

                    if user_input_num_profiles and user_input_distance_mm:
                        try:
                            num_profiles = int(user_input_num_profiles)
                            distance_mm = float(user_input_distance_mm)
                            continue  # Recalculer avec les nouvelles valeurs
                        except ValueError:
                            forms.alert("Valeur invalide. Veuillez entrer des nombres valides.")
                            continue  # Redemander la saisie
                    else:
                        forms.alert("Aucune valeur saisie. Opération annulée.")
                        break  # Quitter si l'utilisateur ne veut pas saisir de nouvelles valeurs
                # ✅ Demande de la valeur de Z
                if z_min_mm < 0:
                    # Si z_min_mm est négatif, on n'affiche que la partie "après z_max_mm"
                    prompt_message = (
                            "Entrez la valeur de Z (en mm) pour " + profile_symbol.Family.Name +
                            " (entre " +
                                    str(round(z_max_mm +64, 2)) + " mm) et "+
                            str(round(h_panneau_value_mm - ((num_profiles - 1) * distance_mm)) - 32) +
 "tout en respectant l'espace disponible."
                    )
                else:
                    # Sinon, on affiche les deux options (avant z_min_mm ou après z_max_mm)
                    prompt_message = (
                            "Entrez la valeur de Z (en mm) pour " + profile_symbol.Family.Name +
                                    " (entre 96 et " + str(round(z_min_mm, 2)) + " mm ou entre " +
                                    str(round(z_max_mm + 64, 2)) + " mm) et "+
                            str(round(h_panneau_value_mm - ((num_profiles - 1) * distance_mm)) - 32) +
 "tout en respectant l'espace disponible."

                    )

                # Demander la valeur de Z à l'utilisateur
                user_input_z_mm = forms.ask_for_string(
                    prompt=prompt_message,
                    title="Valeur de Z"
                )

                # Si l'utilisateur annule ou n'entre pas de valeur, on annule l'opération
                if not user_input_z_mm:
                    forms.alert("Aucune valeur n'a été saisie pour Z. Opération annulée.")
                    break  # Sortir de la boucle

                try:
                    insertion_point_z_mm = float(user_input_z_mm)
                    insertion_point_z_ft = insertion_point_z_mm / 304.8  # Conversion en pieds

                    if (insertion_point_z_mm < z_min_mm and insertion_point_z_mm >= 0) or \
                            (insertion_point_z_mm > z_max_mm and (
                                    insertion_point_z_mm + (num_profiles - 1) * distance_mm) <= h_panneau_value_mm):
                        break  # Valeur correcte, on sort de la boucle
                    else:
                        # ✅ Demande de la valeur de Z
                        if z_min_mm < 0:
                            # Si z_min_mm est négatif, on n'affiche que la partie "après z_max_mm"
                            prompt_message = (
                                    "Entrez la valeur de Z (en mm) pour " + profile_symbol.Family.Name +
                                    " (entre " +
                                    str(round(z_max_mm +64, 2)) + " mm) et "+
                            str(round(h_panneau_value_mm - ((num_profiles - 1) * distance_mm)) - 32) +
 "tout en respectant l'espace disponible."
                            )
                        else:
                            # Sinon, on affiche les deux options (avant z_min_mm ou après z_max_mm)
                            prompt_message = (
                                    "Entrez la valeur de Z (en mm) pour " + profile_symbol.Family.Name +
                                    " (entre 96 et " + str(round(z_min_mm, 2)) + " mm ou entre " +
                                    str(round(z_max_mm + 64 , 2)) + " mm) et "+
                            str(round(h_panneau_value_mm - ((num_profiles - 1) * distance_mm)) - 32) +
 "tout en respectant l'espace disponible."
                            )

                        # Demander la valeur de Z à l'utilisateur
                        user_input_z_mm = forms.ask_for_string(
                            prompt=prompt_message,
                            title="Valeur de Z"
                        )
                except ValueError:
                    forms.alert("Erreur : La valeur saisie pour Z n'est pas valide. Veuillez entrer un nombre.")

        # Si un seul profil doit être ajouté, sortir de la boucle après la première insertion
        if num_profiles == 1:
            with Transaction(family_doc, "Add profile to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                # Insertion à la position ajustée
                insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)
                family_instance = family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)
                # Sauvegarder les informations dans le fichier CSV
                save_to_csv(profile_symbol.Family.Name, insertion_point_x_ft * 304.8, insertion_point_y_ft * 304.8,
                            insertion_point_z_ft * 304.8, distance_mm)



                t.Commit()

        # Si plusieurs profils doivent être ajoutés, utiliser une boucle
        else:
            with Transaction(family_doc, "Add profiles to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                for i in range(num_profiles):
                    # Si c'est le premier profil, ne pas incrémenter
                    if i > 0:
                        # Incrémenter la position X si ce n'est pas un profil de type H
                        if profile_symbol.Family.Name not in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
                            insertion_point_x_ft += distance_mm / 304.8  # Conversion de mm à pieds

                        # Incrémenter la position Z si c'est un profil de type H
                        if profile_symbol.Family.Name in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
                            insertion_point_z_ft += distance_mm / 304.8  # Incrémentation de la position Z

                    # Insertion à la position ajustée
                    insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)
                    family_instance = family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol,
                                                                                StructuralType.NonStructural)
                    # Sauvegarder les informations dans le fichier CSV
                    save_to_csv(profile_symbol.Family.Name, insertion_point_x_ft * 304.8, insertion_point_y_ft * 304.8,
                                insertion_point_z_ft * 304.8, distance_mm)



                t.Commit()

        # Sauvegarder la famille seulement si des profils ont été ajoutés
        if num_profiles > 0:
            family_doc.Save()

    except Exception as e:
        forms.alert("Error adding profiles to family: {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)

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
        ["Insert Existing Profiles", "Insert Cadre openning"],
        default="Insert Existing Profiles",
        title="Select Insertion Method",
        prompt="Choose an option:"
    )

    if not insertion_method:
        return

    if insertion_method == 'Insert Existing Profiles':
        # Existing workflow
        profile_symbol = select_profile_symbol(family_doc)
        if not profile_symbol:
            return

        # Get user input for profiles
        image_path = r"C:\Users\wiemb\Desktop\MainBefore.jpg"
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