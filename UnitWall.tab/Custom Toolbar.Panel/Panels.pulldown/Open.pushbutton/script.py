#' -*- coding: utf-8 -*-
"""
Description:
This script allows adding profiles, including a plenum profile, to a curtain wall panel in Revit.

How to use:
1. Select a panel: The user selects a curtain wall panel from the project.
2. Choose the number of profiles to create: The user specifies how many profiles, including the plenum profile, they want to add to the panel.
3. Insert the distance between profiles: The user inputs the desired distance between each profile.


Version: v2
Author: Wiem BEN ARAAR, Amira DRIDI
"""
import clr
import traceback
import os
import random
import Autodesk
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.DB.Structure import StructuralType
from Autodesk.Revit.DB import IFamilyLoadOptions
from Autodesk.Revit.DB import ElementId, BuiltInParameter

clr.AddReference('System.Windows.Forms')

from Autodesk.Revit.UI import TaskDialog




def add_profiles_to_family(family_doc, profile_symbol, num_profiles, distance_mm):
    """Ajoute plusieurs instances du profil sélectionné à la famille avec une position spécifique, en tenant compte de la largeur du panneau."""
    try:
        # Position initiale
        insertion_point_x_ft = 0
        insertion_point_y_ft = 0
        insertion_point_z_ft = 0

        if profile_symbol.Family.Name == "PROFILE_PLN_124_V_WIN_UP":
            panel = select_panel()
            if panel:
                # Récupérer le paramètre LINTEL pour la hauteur
                panel_height_param = panel.LookupParameter("LINTEL")
                if panel_height_param:
                    lintel_value_ft = panel_height_param.AsDouble()  # En pieds
                    insertion_point_y_ft = 294 / 304.8
                    insertion_point_z_ft = lintel_value_ft


        elif profile_symbol.Family.Name == "PROFILE_STR_152_V_WIN_UP":
            # Sélectionner le panneau
            panel = select_panel()

            if panel is None:
                TaskDialog.Show("Erreur", "Aucun panneau sélectionné.")
            else:

                # Récupérer la valeur du paramètre LINTEL pour définir Z
                panel_height_param = panel.LookupParameter(
                    "LINTEL")  # Assurez-vous que panel est défini et que ce paramètre existe

                if panel_height_param:
                    # Récupérer la valeur de LINTEL en pieds (ou unités internes si nécessaire)
                    lintel_value_ft = panel_height_param.AsDouble()


                    # Calculer la position Z en pieds (utilisation directe de LINTEL)
                    insertion_point_z_ft = lintel_value_ft  # Utilisation de LINTEL pour la position Z
                    insertion_point_y_ft = 126 / 304.8  # Décalage Y

                else:
                    TaskDialog.Show("Erreur", "Le paramètre LINTEL n'a pas pu être récupéré.")

        elif profile_symbol.Family.Name == "PROFILE_PLN_124_V_WIN_DOWN":
            # Calculer l'élévation Y en pieds (convertir 168 mm en pieds)
            insertion_point_y_ft = 294 / 304.8  # 168 mm converti en pieds


        elif profile_symbol.Family.Name == "PROFILE_STR_152_V_WIN_DOWN":

            height_param = profile_symbol.LookupParameter("H_STR_152")
            if height_param and not height_param.IsReadOnly:
                height_param.Set("SILL")

        elif profile_symbol.Family.Name == "PROFILE_PLN_124_H_WIN_LEFT":

            panel=select_panel()

            # Récupérer la valeur de LEFT pour définir la position du profil

            left_param = panel.LookupParameter("LEFT")

            largeur_param = profile_symbol.LookupParameter("L_STR_152_WIN_LEFT")  # Paramètre de largeur à modifier

            if left_param and left_param.HasValue:

                left_value = left_param.AsDouble()  # Récupère la valeur actuelle de LEFT en pieds

            else:

                TaskDialog.Show("Erreur", "Le paramètre LEFT est introuvable ou sans valeur.")

            # Récupérer la longueur (largeur) du panneau en millimètres

            panel_length_param = panel.LookupParameter("Largeur")

            if panel_length_param and panel_length_param.HasValue:

                panel_length_mm = panel_length_param.AsDouble() * 304.8  # Convertir la longueur de pieds à millimètres



                # Calcul de la moitié de la longueur du panneau et de la position basée sur LEFT

                half_panel_length_mm = panel_length_mm / 2

                half_left_value_mm = left_value * 304.8 / 2  # Convertir LEFT en millimètres et diviser par 2

                # Calculer la position X pour le profil en partant du centre du panneau

                insertion_point_x_mm = half_panel_length_mm - half_left_value_mm

                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion en pieds

                insertion_point_y_ft = 294 / 304.8  # Conversion de 168 mm en pieds



            else:

                TaskDialog.Show("Erreur", "Le paramètre Largeur est introuvable ou sans valeur.")

        elif profile_symbol.Family.Name == "PROFILE_STR_152_H_WIN_LEFT":
            panel=select_panel()

            # Récupérer la valeur de LEFT pour définir la position du profil
            left_param = panel.LookupParameter("LEFT")
            largeur_param = profile_symbol.LookupParameter("L_STR_152_WIN_LEFT")  # Paramètre de largeur à modifier

            if left_param and left_param.HasValue:
                left_value = left_param.AsDouble()  # Récupère la valeur actuelle de LEFT en pieds



            else:
                TaskDialog.Show("Erreur", "Le paramètre LEFT est introuvable ou sans valeur.")

            # Récupérer la longueur (largeur) du panneau en millimètres
            panel_length_param = panel.LookupParameter("Largeur")
            if panel_length_param and panel_length_param.HasValue:
                panel_length_mm = panel_length_param.AsDouble() * 304.8  # Convertir la longueur de pieds à millimètres


                # Calcul de la moitié de la longueur du panneau et de la position basée sur LEFT
                half_panel_length_mm = panel_length_mm / 2
                half_left_value_mm = left_value * 304.8 / 2  # Convertir LEFT en millimètres et diviser par 2

                # Calculer la position X pour le profil en partant du centre du panneau
                insertion_point_x_mm = half_panel_length_mm - half_left_value_mm
                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion en pieds
                insertion_point_y_ft = 126 / 304.8  # Conversion de 168 mm en pieds



            else:
                TaskDialog.Show("Erreur", "Le paramètre Largeur est introuvable ou sans valeur.")

        elif profile_symbol.Family.Name == "PROFILE_PLN_124_H_WIN_RIGHT":
            panel = select_panel()

            # Récupérer la valeur du paramètre RIGHT depuis le panneau
            right_value_param = panel.LookupParameter("RIGHT")

            if right_value_param and right_value_param.HasValue:
                # Convertir la valeur de `RIGHT` en pieds
                right_value = right_value_param.AsDouble()
            else:
                TaskDialog.Show("Erreur", "Le paramètre 'RIGHT' est introuvable ou sans valeur dans le panneau.")
                return  # Sortir si `RIGHT` est manquant pour éviter des erreurs

            # Ouvrir la famille dans l'éditeur pour modifier le paramètre `L_STR_152_WIN_RIGHT`
            family_doc = open_family_in_editor(panel)

            if family_doc:
                # Accéder aux paramètres de la famille
                parameters = family_doc.FamilyManager.Parameters

                # Rechercher le paramètre `L_STR_152_WIN_RIGHT`
                largeur_param = None
                for param in parameters:
                    if param.Definition.Name == "L_STR_152_WIN_RIGHT":
                        largeur_param = param
                        break


            else:
                TaskDialog.Show("Erreur", "Impossible d'ouvrir la famille dans l'éditeur.")

            # Calculer la position X pour l'insertion basée sur le centre du panneau
            panel_length_param = panel.LookupParameter("Largeur")
            if panel_length_param and panel_length_param.HasValue:
                panel_length_mm = panel_length_param.AsDouble() * 304.8  # Convertir la longueur en millimètres


                # Calcul de la moitié de la longueur du panneau et de la position basée sur `RIGHT`
                half_panel_length_mm = panel_length_mm / 2
                half_right_value_mm = right_value * 304.8 / 2  # Convertir `RIGHT` en millimètres et diviser par 2

                # Calculer la position X pour le profil
                insertion_point_x_mm = -half_panel_length_mm + half_right_value_mm
                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion en pieds
                insertion_point_y_ft = 294 / 304.8  # Conversion de 168 mm en pieds


            else:
                TaskDialog.Show("Erreur", "Le paramètre Largeur est introuvable ou sans valeur.")

        # Vérifier si le profil correspond à PROFILE_STR_152_H_WIN_RIGHT
        elif profile_symbol.Family.Name == "PROFILE_STR_152_H_WIN_RIGHT":
            panel = select_panel()

            if panel:
                # Récupérer la valeur du paramètre RIGHT depuis le panneau
                right_value_param = panel.LookupParameter("RIGHT")
                if right_value_param and right_value_param.HasValue:
                    # Convertir la valeur de `RIGHT` en pieds
                    right_value = right_value_param.AsDouble()
                else:
                    TaskDialog.Show("Erreur", "Le paramètre 'RIGHT' est introuvable ou sans valeur dans le panneau.")
                    return  # Sortir si `RIGHT` est manquant pour éviter des erreurs

                # Ouvrir la famille dans l'éditeur pour modifier le paramètre `L_STR_152_WIN_RIGHT`
                family_doc = open_family_in_editor(panel)

                if family_doc:
                    # Accéder aux paramètres de la famille
                    parameters = family_doc.FamilyManager.Parameters

                    # Rechercher le paramètre `L_STR_152_WIN_RIGHT`
                    largeur_param = next(
                        (param for param in parameters if param.Definition.Name == "L_STR_152_WIN_RIGHT"), None)


                else:
                    TaskDialog.Show("Erreur", "Impossible d'ouvrir la famille dans l'éditeur.")

                # Calculer la position X pour l'insertion basée sur le centre du panneau
                panel_length_param = panel.LookupParameter("Largeur")
                if panel_length_param and panel_length_param.HasValue:
                    panel_length_mm = panel_length_param.AsDouble() * 304.8  # Convertir la longueur en millimètres


                    # Calcul de la moitié de la longueur du panneau et de la position basée sur `RIGHT`
                    half_panel_length_mm = panel_length_mm / 2
                    half_right_value_mm = right_value * 304.8 / 2  # Convertir `RIGHT` en millimètres et diviser par 2

                    # Calculer la position X pour le profil
                    insertion_point_x_mm = -half_panel_length_mm + half_right_value_mm
                    insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion en pieds
                    insertion_point_y_ft = 126 / 304.8  # Conversion de 168 mm en pieds


                else:
                    TaskDialog.Show("Erreur", "Le paramètre 'Largeur' est introuvable ou sans valeur dans le panneau.")
            else:
                TaskDialog.Show("Erreur", "Aucun panneau n'a été sélectionné.")

        # Fonction pour demander la valeur Z en mm pour certains profils
        if profile_symbol.Family.Name in ["PROFILE_STR_152_H_WIN_RIGHT", "PROFILE_PLN_124_H_WIN_LEFT",
                                          "PROFILE_PLN_124_H_WIN_RIGHT", "PROFILE_STR_152_H_WIN_LEFT"]:
            user_input_z_mm = forms.ask_for_string(
                prompt="Enter the Z value (in mm) for {}".format(profile_symbol.Family.Name),
                title="Value of Z"
            )
            if user_input_z_mm:
                try:
                    insertion_point_z_ft = float(user_input_z_mm) / 304.8  # Conversion mm -> pieds
                except ValueError:
                    forms.alert("The value entered for Z is not valid. Please enter a number.")
                    return

        if num_profiles == 1:
            with Transaction(family_doc, "Add profile to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                # Insertion à la position ajustée
                insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)
                family_instance = family_doc.FamilyCreate.NewFamilyInstance(insertion_point, profile_symbol, StructuralType.NonStructural)

                t.Commit()

        else:
            with Transaction(family_doc, "Add profiles to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                for i in range(num_profiles):
                    try:
                        # Incrémentation des positions
                        if i > 0:
                            # Vérifier si le profil n'est pas de type "H" pour incrémenter X
                            if profile_symbol and profile_symbol.Family.Name not in ["PROFILE_PLN_124_H_WIN_LEFT",
                                                                                     "PROFILE_PLN_124_H_WIN_RIGHT","PROFILE_STR_152_H_WIN_LEFT","PROFILE_STR_152_H_WIN_RIGHT"]:
                                insertion_point_x_ft += distance_mm / 304.8  # Conversion mm à pieds
                                # Incrémenter la position Z si c'est un profil de type H
                            if profile_symbol.Family.Name in ["PROFILE_PLN_124_H_WIN_LEFT", "PROFILE_PLN_124_H_WIN_RIGHT","PROFILE_STR_152_H_WIN_LEFT","PROFILE_STR_152_H_WIN_RIGHT"]:
                                insertion_point_z_ft += distance_mm / 304.8  # Incrémentation de la position Z

                        # Créer le point d'insertion
                        insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)

                        # Vérifier si `family_doc` est valide avant de créer une instance
                        if family_doc:
                            family_instance = family_doc.FamilyCreate.NewFamilyInstance(
                                insertion_point, profile_symbol, StructuralType.NonStructural
                            )
                        else:
                            TaskDialog.Show("Erreur", "Document de la famille invalide.")
                    except Exception as e:
                        TaskDialog.Show("Erreur", "Une erreur est survenue : {str(e)}")

                t.Commit()

        if num_profiles > 0:
            family_doc.Save()

    except Exception as e:
        forms.alert("Error adding profiles to family: {}\nTraceback : {}".format(e, traceback.format_exc()), exitscript=True)

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
        TaskDialog.Show("Error", "An error occurred while selecting the panel: " + str(e))
        return None

def open_family_in_editor(panel):
    """Ouvre la famille associée au panneau dans l'éditeur de famille."""
    try:
        if not isinstance(panel, FamilyInstance):
            TaskDialog.Show("Erreur", "L'élément sélectionné n'est pas une instance de famille.")
            return None

        family = panel.Symbol.Family
        if not family:
            TaskDialog.Show("Erreur", "Impossible de récupérer la famille associée au panneau.")
            return None

        family_doc = revit.doc.EditFamily(family)
        return family_doc

    except Exception as e:
        TaskDialog.Show("Erreur", "Erreur lors de l'ouverture de la famille : " + str(e))
        return None


def select_profile_symbol(family_doc):
    """Permet à l'utilisateur de sélectionner un symbole de profil disponible dans l'éditeur de famille."""
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilySymbol)
        profiles = {f.Id: f for f in collector if "WIN" in f.Family.Name}

        if not profiles:
            forms.alert("No family profiles found.", exitscript=True)

        profile_names = [profile.Family.Name + " " + str(profile.Id) for profile in profiles.values()]
        selected_profile_name = forms.SelectFromList.show(profile_names, title="Select a profile", multiselect=False)

        if not selected_profile_name:
            forms.alert("No profile selected.", exitscript=True)

        selected_profile_id = next((id for id, profile in profiles.items() if
                                     profile.Family.Name + " " + str(id) == selected_profile_name), None)
        return profiles[selected_profile_id]

    except Exception as e:
        forms.alert("Error selecting profile symbol: " + str(e) + "\nTraceback : " + traceback.format_exc(), exitscript=True)
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
        if not family_path:
            TaskDialog.Show("Erreur", "Le chemin de la famille est invalide.")
            return

        family_doc.Close(False)  # Assurez-vous de fermer le document avant de le charger

        familyLoadOptions = FamilyLoadOptions()

        with Transaction(revit.doc, "Charger la famille modifiée") as tx:
            tx.Start()
            if revit.doc.LoadFamily(family_path, familyLoadOptions):
                TaskDialog.Show("Succès", "La famille a été rechargée dans le projet.")
            else:
                TaskDialog.Show("Erreur", "Échec du chargement de la famille.")
            tx.Commit()
    except Exception as e:
        TaskDialog.Show("Erreur", "Erreur lors du chargement de la famille : " + str(e))
def generate_random_name(base_name):
    """Génère un nouveau nom avec 4 chiffres aléatoires."""
    random_digits = random.randint(1000, 9999)
    return base_name + "_" + str(random_digits)

def duplicate_and_modify_family(panel):
    """Duplique une famille, applique des modifications et la charge dans le projet."""
    try:
        family = panel.Symbol.Family
        family_doc = revit.doc.EditFamily(family)

        original_path = family_doc.PathName
        if not original_path:
            TaskDialog.Show("Erreur", "La famille sélectionnée n'a pas de chemin valide.")
            return None

        new_name = generate_random_name(family.Name)
        new_path = os.path.join(os.path.dirname(original_path), new_name + ".rfa")

        family_doc.SaveAs(new_path)

        modify_panel_family(family_doc)

        family_doc.Save()
        family_doc.Close(False)

        familyLoadOptions = FamilyLoadOptions()
        with Transaction(revit.doc, "Charger la famille modifiée") as tx:
            tx.Start()
            if revit.doc.LoadFamily(new_path, familyLoadOptions):
                TaskDialog.Show("Succès", "La famille '" + new_name + "' a été modifiée et chargée avec succès.")
                tx.Commit()
                return new_name
            else:
                TaskDialog.Show("Erreur", "Échec du chargement de la famille modifiée.")
                tx.RollBack()
                return None

    except Exception as e:
        TaskDialog.Show("Erreur", "Une erreur est survenue : " + str(e))
        return None


def modify_panel_family(family_doc):
    """Applique les modifications nécessaires à une famille de panneaux."""
    try:
        family_manager = family_doc.FamilyManager

        # Ajouter un paramètre personnalisé si nécessaire
        with Transaction(family_doc, "Ajouter ou modifier un paramètre") as tx:
            tx.Start()
            parameter = family_manager.get_Parameter("CustomParameter")
            if not parameter:
                family_manager.AddParameter(
                    "CustomParameter",
                    BuiltInParameterGroup.PG_IDENTITY_DATA,
                    ParameterType.Text,
                    False
                )
            else:
                family_manager.Set(parameter, "Nouvelle Valeur")
            tx.Commit()

    except Exception as e:
        TaskDialog.Show("Erreur", "Erreur lors de la modification de la famille : " + str(e))

def update_panel_family(panel, new_family_name):
    """Met à jour le panneau sélectionné pour utiliser la nouvelle famille."""
    try:
        new_family = next((f for f in FilteredElementCollector(revit.doc).OfClass(Family)
                          if f.Name == new_family_name), None)

        if not new_family:
            TaskDialog.Show("Erreur", "La nouvelle famille n'a pas été trouvée dans le projet.")
            return

        new_symbol = next((s for s in new_family.GetFamilySymbolIds()), None)

        with Transaction(revit.doc, "Update panel to new family") as tx:
            tx.Start()
            panel.Symbol = revit.doc.GetElement(new_symbol)
            tx.Commit()

        TaskDialog.Show("Succès", "Le panneau a été mis à jour avec la nouvelle famille.")

    except Exception as e:
        TaskDialog.Show("Erreur", "Une erreur est survenue lors de la mise à jour du panneau : " + str(e))

def main():
    """Point d'entrée principal pour l'ajout de profils à un panneau."""
    panel = select_panel()
    if not panel:
        return

    try:
        # Demander à l'utilisateur s'il veut dupliquer la famille avant modification
        duplicate = forms.alert("Voulez-vous dupliquer la famille avant modification ?", options=["Oui", "Non"])

        # Si l'utilisateur choisit de dupliquer la famille, dupliquer et modifier
        if duplicate == "Oui":
            # Dupliquer et modifier la famille
            new_family_name = duplicate_and_modify_family(panel)
            if new_family_name:
                # Mettre à jour la famille du panneau avec la famille dupliquée
                update_panel_family(panel, new_family_name)
            else:
                forms.alert("La duplication de la famille a échoué.")
                return

        # Ouvrir la famille dans l'éditeur de famille
        family_doc = open_family_in_editor(panel)
        if family_doc is None:
            return

        # Sélectionner le symbole de profil
        profile_symbol = select_profile_symbol(family_doc)
        if profile_symbol is None:
            return

        # Demander à l'utilisateur combien de profils ajouter et la distance entre eux
        user_input_num_profiles = forms.ask_for_string(prompt="How many profiles do you want to add?",
                                                       title="Number of Profiles", default="1")
        num_profiles = int(user_input_num_profiles)

        if num_profiles < 1:
            forms.alert("The number of profiles must be at least 1.")
            return

        user_input_distance_mm = forms.ask_for_string(prompt="What distance between the profiles (in mm)?",
                                                      title="Distance between Profiles", default="100")
        distance_mm = int(user_input_distance_mm)

        if distance_mm < 0:
            forms.alert("The distance between profiles cannot be negative.")
            return

        # Appeler la fonction d'ajout de profils
        add_profiles_to_family(family_doc, profile_symbol, num_profiles, distance_mm)

        # Charger la famille modifiée dans le projet
        load_family_back_to_project(family_doc)

    except ValueError:
        forms.alert("Input error: Please enter valid integers.")
    except Exception as e:
        TaskDialog.Show("Error", "Error entering values : {}".format(e))


if __name__ == "__main__":
    main()
