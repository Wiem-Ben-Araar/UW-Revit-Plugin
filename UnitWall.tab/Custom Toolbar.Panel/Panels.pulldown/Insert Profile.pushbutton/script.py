# -*- coding: utf-8 -*-
import clr
import traceback
import os
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.DB import IFamilyLoadOptions

clr.AddReference('System.Windows.Forms')

import csv
from Autodesk.Revit.UI import TaskDialog

# Nom du fichier CSV
csv_file = "C:\\Users\\wiemb\\Desktop\\PyRevit\\MyExtension.extension\\profiles_data.csv"

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
          #  print("Le fichier {csv_file} a été créé avec succès avec les en-têtes.")
        except Exception as e:
            print("Erreur lors de la création du fichier CSV : {e}")
# Appel de la fonction pour créer le fichier CSV
create_csv_with_headers()

   # print("Le fichier {} a été créé avec succès avec les en-têtes.".format(csv_file))



def save_to_csv(profile_name, insertion_point_x, insertion_point_y, insertion_point_z, distance):
    """Sauvegarde les informations des profils dans un fichier CSV."""
    try:
        with open(csv_file, mode="a") as file:  # 'a' pour ajouter à la fin du fichier
            writer = csv.writer(file, delimiter='|')  # Utiliser une tabulation comme séparateur
            # Écrire chaque valeur dans sa propre colonne
            writer.writerow([profile_name, insertion_point_x, insertion_point_y, insertion_point_z, distance])
    except Exception as e:
        TaskDialog.Show("Error", "Erreur lors de la sauvegarde dans le fichier CSV : {}".format(e))

def select_panel():
    """Sélectionne un panneau de mur rideau dans le projet."""
    try:
        selection = revit.uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Select the curtain wall panel to modify")
        selected_element = revit.doc.GetElement(picked_ref.ElementId)

        if isinstance(selected_element, FamilyInstance):
            return selected_element
        else:
            TaskDialog.Show("Error", "L'élément sélectionné n'est pas une instance de panneau de mur rideau.")
            return None
    except Exception as e:
        TaskDialog.Show("Error", "Une erreur est survenue lors de la sélection du panneau : {}".format(e))
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
            TaskDialog.Show("Error", "Le paramètre 'L_PANNEAU' n'a pas été trouvé.\nParamètres disponibles: {}".format(
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
        TaskDialog.Show("Error", "Une erreur est survenue lors de l'ouverture de la famille : {}".format(e))
        return None

def select_profile_symbol(family_doc):
    """Permet à l'utilisateur de sélectionner un symbole de profil disponible dans l'éditeur de famille."""
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilySymbol)
        profiles = {f.Id: f for f in collector if "PROFILE" in f.Family.Name}

        if not profiles:
            forms.alert("Aucun profil de famille trouvé.", exitscript=True)

        profile_names = ["{} {}".format(profile.Family.Name, profile.Id) for id, profile in profiles.items()]
        selected_profile_name = forms.SelectFromList.show(profile_names, title="Sélectionnez un profil", multiselect=False)

        if not selected_profile_name:
            forms.alert("Aucun profil sélectionné.", exitscript=True)

        selected_profile_id = next((id for id, profile in profiles.items() if
                                     "{} {}".format(profile.Family.Name, id) == selected_profile_name), None)
        return profiles[selected_profile_id] if selected_profile_id else None

    except Exception as e:
        forms.alert("Erreur lors de la sélection du symbole de profil : {}\nTraceback : {}".format(e, traceback.format_exc()),
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

        with revit.Transaction("Charger la famille dans le projet"):
            if revit.doc.LoadFamily(family_path, familyLoadOptions):
                forms.alert("La famille a été chargée avec succès dans le projet principal.")
            else:
                forms.alert("Échec du chargement de la famille dans le projet principal.")
    except Exception as e:
        forms.alert("Erreur lors du chargement de la famille dans le projet : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)


def add_profiles_to_family(family_doc, profile_symbol, panel_length_mm, num_profiles, distance_mm):
    """Ajoute plusieurs instances du profil sélectionné à la famille avec une position spécifique, en tenant compte de la largeur du panneau."""
    try:
        # Position initiale
        insertion_point_x_ft = 0
        insertion_point_y_ft = 0
        insertion_point_z_ft = 0

        # Conditions spécifiques pour chaque profil
        if profile_symbol.Family.Name == "PROFILE_PLN_124_V":
            # Demander à l'utilisateur d'entrer la position X en mm
            user_input_x_mm = forms.ask_for_string(
                prompt="Entrez la nouvelle position X (en mm) pour PROFILE_PLN_124_V",
                title="Valeur de X"
            )
            if user_input_x_mm:
                try:
                    position_x_mm = float(user_input_x_mm)
                    half_panel_length_mm = panel_length_mm / 2
                    insertion_point_x_mm = position_x_mm - half_panel_length_mm
                    insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion mm -> pieds
                except ValueError:
                    forms.alert("La valeur saisie pour X n'est pas valide. Veuillez entrer un nombre.")
                    return
            else:
                return  # Si aucune entrée, sortir de la fonction
            insertion_point_y_ft = -168 / 304.8  # Y en bas
        elif profile_symbol.Family.Name == "PROFILE_PLN_175_V":
            # Demander à l'utilisateur d'entrer la position X en mm
            user_input_x_mm = forms.ask_for_string(
                prompt="Entrez la nouvelle position X (en mm) pour PROFILE_PLN_124_V",
                title="Valeur de X"
            )
            if user_input_x_mm:
                try:
                    position_x_mm = float(user_input_x_mm)
                    half_panel_length_mm = panel_length_mm / 2
                    insertion_point_x_mm = position_x_mm - half_panel_length_mm
                    insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion mm -> pieds
                except ValueError:
                    forms.alert("La valeur saisie pour X n'est pas valide. Veuillez entrer un nombre.")
                    return
            else:
                return  # Si aucune entrée, sortir de la fonction
            insertion_point_y_ft = -193.5 / 304.8  # Y en bas
        elif profile_symbol.Family.Name == "PROFILE_PLN_225_V":
            # Demander à l'utilisateur d'entrer la position X en mm
            user_input_x_mm = forms.ask_for_string(
                prompt="Entrez la nouvelle position X (en mm) pour PROFILE_PLN_124_V",
                title="Valeur de X"
            )
            if user_input_x_mm:
                try:
                    position_x_mm = float(user_input_x_mm)
                    half_panel_length_mm = panel_length_mm / 2
                    insertion_point_x_mm = position_x_mm - half_panel_length_mm
                    insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion mm -> pieds
                except ValueError:
                    forms.alert("La valeur saisie pour X n'est pas valide. Veuillez entrer un nombre.")
                    return
            else:
                return  # Si aucune entrée, sortir de la fonction
            insertion_point_y_ft = -218.5 / 304.8  # Y en bas
        elif profile_symbol.Family.Name == "PROFILE_STR_152_V":
            # Demander à l'utilisateur d'entrer la position X en mm
            user_input_x_mm = forms.ask_for_string(
                prompt="Entrez la nouvelle position X (en mm) pour PROFILE_STR_152_V",
                title="Valeur de X"
            )
            if user_input_x_mm:
                try:
                    position_x_mm = float(user_input_x_mm)
                    half_panel_length_mm = panel_length_mm / 2
                    insertion_point_x_mm = position_x_mm - half_panel_length_mm
                    insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion mm -> pieds
                except ValueError:
                    forms.alert("La valeur saisie pour X n'est pas valide. Veuillez entrer un nombre.")
                    return
            else:
                return  # Si aucune entrée, sortir de la fonction

            insertion_point_y_ft = 44 / 304.8  # Décalage Y

        # Demander la valeur de Z pour les profils appropriés
        if profile_symbol.Family.Name in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
            user_input_z_mm = forms.ask_for_string(
                prompt="Entrez la valeur de Z (en mm) pour {}".format(profile_symbol.Family.Name),
                title="Valeur de Z"
            )
            if user_input_z_mm:
                try:
                    insertion_point_z_ft = float(user_input_z_mm) / 304.8  # Conversion mm -> pieds
                except ValueError:
                    forms.alert("La valeur saisie pour Z n'est pas valide. Veuillez entrer un nombre.")
                    return

        # Si un seul profil doit être ajouté, sortir de la boucle après la première insertion
        if num_profiles == 1:
            with Transaction(family_doc, "Ajouter un profil à la famille") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                # Insertion à la position ajustée
                insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)
                family_instance = family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)

                # Sauvegarder les informations dans le fichier CSV
                save_to_csv(profile_symbol.Family.Name, insertion_point_x_ft * 304.8, insertion_point_y_ft * 304.8, insertion_point_z_ft * 304.8, distance_mm)

                t.Commit()

        # Si plusieurs profils doivent être ajoutés, utiliser une boucle
        else:
            with Transaction(family_doc, "Ajouter des profils à la famille") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                for i in range(num_profiles):
                    # Incrémenter la position X si ce n'est pas un profil de type H
                    if profile_symbol.Family.Name not in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
                        insertion_point_x_ft += distance_mm / 304.8  # Conversion de mm à pieds

                    # Incrémenter la position Z si c'est un profil de type H
                    if profile_symbol.Family.Name in ["PROFILE_STR_152_H", "PROFILE_STR_152_H_DOUBLE"]:
                        insertion_point_z_ft += distance_mm / 304.8  # Incrémentation de la position Z

                    # Insertion à la position ajustée
                    insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)
                    family_instance = family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)

                    # Sauvegarder les informations dans le fichier CSV
                    save_to_csv(profile_symbol.Family.Name, insertion_point_x_ft * 304.8, insertion_point_y_ft * 304.8, insertion_point_z_ft * 304.8, distance_mm)

                t.Commit()

        # Sauvegarder la famille seulement si des profils ont été ajoutés
        if num_profiles > 0:
            family_doc.Save()

    except Exception as e:
        forms.alert("Erreur lors de l'ajout des profils à la famille : {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)




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

    # Sélectionner le symbole de profil
    profile_symbol = select_profile_symbol(family_doc)
    if profile_symbol is None:
        return

    # Demander à l'utilisateur le nombre de profils à ajouter et la distance entre eux
    try:
        user_input_num_profiles = forms.ask_for_string(prompt="Combien de profils voulez-vous ajouter ?",
                                                       title="Nombre de Profils", default="1")
        num_profiles = int(user_input_num_profiles)  # Conversion en entier

        if num_profiles < 1:
            forms.alert("Le nombre de profils doit être au moins 1.")
            return

        user_input_distance_mm = forms.ask_for_string(prompt="Quelle distance entre les profils (en mm) ?",
                                                      title="Distance entre Profils", default="100")
        distance_mm = int(user_input_distance_mm)  # Conversion en entier

        if distance_mm < 0:
            forms.alert("La distance entre les profils ne peut pas être négative.")
            return

        # Appeler la fonction d'ajout de profils avec les valeurs saisies
        add_profiles_to_family(family_doc, profile_symbol, panel_length_mm, num_profiles, distance_mm)

    except ValueError:
        forms.alert("Erreur de saisie : Veuillez entrer des nombres entiers valides.")
    except Exception as e:
        TaskDialog.Show("Error", "Erreur lors de l'entrée des valeurs : {}".format(e))

    load_family_back_to_project(family_doc)

# Exécute le script
main()





