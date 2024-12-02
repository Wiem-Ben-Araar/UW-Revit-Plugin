# -*- coding: utf-8 -*-
import csv
import traceback
from pyrevit import forms, revit
from Autodesk.Revit.DB import IFamilyLoadOptions
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory
# Fonction pour afficher le contenu du fichier CSV
def afficher_donnees_csv(fichier_csv):
    """Affiche le contenu du fichier CSV et le retourne sous forme de liste."""
    try:
        with open(fichier_csv, 'r') as csvfile:
            reader = csv.reader(csvfile)
            donnees = list(reader)
            for i, ligne in enumerate(donnees):
                print("Ligne {}: {}".format(i, ligne))
        return donnees
    except Exception as e:
        print("Erreur lors de la lecture du fichier CSV: {}".format(e))
        return []


# Fonction pour modifier une ligne spécifique du fichier CSV
def modifier_donnees_csv(donnees, index, nouvelles_valeurs):
    """Modifie une ligne spécifique dans les données tout en gardant le nom du profil."""
    if 0 < index < len(donnees):  # Commencer à l'index 1 pour éviter l'en-tête
        print("Avant modification: {}".format(donnees[index]))
        # Garder le nom du profil intact
        nom_profil = donnees[index][0]
        # Mettre à jour les autres valeurs
        donnees[index] = [nom_profil] + nouvelles_valeurs  # Conserve le nom du profil
        print("Après modification: {}".format(donnees[index]))
        return donnees
    else:
        print("Index invalide. Modification non effectuée.")
        return donnees



# Fonction pour sauvegarder les données modifiées dans le fichier CSV
def sauvegarder_donnees_csv(fichier_csv, donnees):
    """Sauvegarde les données modifiées dans le fichier CSV."""
    try:
        with open(fichier_csv, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(donnees)
        print("Modifications sauvegardées avec succès.")
    except Exception as e:
        print("Erreur lors de la sauvegarde du fichier CSV: {}".format(e))


# Fonction pour appliquer les nouvelles valeurs des données du CSV aux éléments dans le projet
def appliquer_modifications_au_projet(donnees):
    """Applique les nouvelles valeurs aux éléments dans le projet Revit."""
    try:
        for index in range(1, len(donnees)):  # Skip header row
            ligne = donnees[index]
            profile_name = ligne[0]  # Assuming the profile name is the first column
            nouvelle_valeur = ligne[1:]  # The new values to apply

            # Find elements based on profile name or another unique identifier
            # Here, adapt the logic as per your need to find elements.
            elements = FilteredElementCollector(revit.doc).OfCategory(
                BuiltInCategory.OST_CurtainWallPanels).WhereElementIsNotElementType().ToElements()

            for element in elements:
                if element.Name == profile_name:  # Match the profile name
                    # Assume the parameters correspond to the new values
                    try:
                        element.LookupParameter("X Position (mm)").Set(float(nouvelle_valeur[0]))
                        element.LookupParameter("Y Position (mm)").Set(float(nouvelle_valeur[1]))
                        element.LookupParameter("Z Position (mm)").Set(float(nouvelle_valeur[2]))
                        element.LookupParameter("Distance Between Profiles (mm)").Set(float(nouvelle_valeur[3]))
                        print("Élément '{}' mis à jour avec succès.".format(profile_name))
                    except Exception as param_error:
                        print("Erreur lors de la mise à jour des paramètres de l'élément '{}': {}".format(profile_name,
                                                                                                          param_error))
                    break  # Break once the profile is found
            else:
                print("Aucun élément avec le nom '{}' trouvé.".format(profile_name))
    except Exception as e:
        print("Erreur lors de l'application des modifications: {}\nTraceback: {}".format(e, traceback.format_exc()))


# Classe pour gérer le chargement de la famille dans le projet
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
                forms.alert("La famille a été chargée avec succès dans le projet principal.")
            else:
                forms.alert("Échec du chargement de la famille dans le projet principal.")
    except Exception as e:
        forms.alert("Erreur lors du chargement de la famille dans le projet: {}\nTraceback : {}".format(e,
                                                                                                        traceback.format_exc()),
                    exitscript=True)


# Chemin du fichier CSV
fichier_csv = r"C:\Users\wiemb\Desktop\PyRevit\MyExtension.extension\profiles_data.csv"

# Étape 1 : Afficher les données actuelles
print("Affichage des données actuelles du fichier CSV:")
donnees = afficher_donnees_csv(fichier_csv)

# Vérification si le fichier contient des données
if donnees:
    # Étape 2 : Sélectionner une ligne à modifier
    try:
        index_a_modifier = int(
            forms.ask_for_string(prompt="Entrez le numéro de la ligne à modifier (1 à {}):".format(len(donnees) - 1),
                                 title="Ligne à modifier"))

        # Obtenir les nouvelles valeurs pour cette ligne en utilisant une chaîne de caractères
        nouvelle_valeur = forms.ask_for_string(
            prompt="Entrez les nouvelles valeurs pour cette ligne (séparées par des virgules):",
            title="Valeurs à modifier").split(',')

        # Modifier les données si l'index est valide
        donnees_modifiees = modifier_donnees_csv(donnees, index_a_modifier, nouvelle_valeur)

        # Étape 3 : Sauvegarder les modifications
        sauvegarder_donnees_csv(fichier_csv, donnees_modifiees)

        # Étape 4 : Appliquer les modifications aux éléments dans le projet
        appliquer_modifications_au_projet(donnees_modifiees)

        # Étape 5 : Réafficher les données pour vérifier les modifications
        print("\nVérification des modifications apportées :")
        afficher_donnees_csv(fichier_csv)

    except ValueError:
        print("Entrée invalide. Assurez-vous d'entrer un numéro de ligne valide.")
else:
    print("Aucune donnée à modifier dans le fichier CSV.")
