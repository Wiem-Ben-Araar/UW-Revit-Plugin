# -*- coding: utf-8 -*-
import csv

# Fonction pour afficher le contenu du fichier CSV
def afficher_donnees_csv(fichier_csv):
    try:
        with open(fichier_csv) as csvfile:
            reader = csv.reader(csvfile)
            donnees = list(reader)
            for i, ligne in enumerate(donnees):
                print("Ligne {}: {}".format(i, ligne))
        return donnees
    except Exception as e:
        print("Erreur lors de la lecture du fichier CSV: {}".format(e))
        return []

# Fonction pour modifier une ligne spécifique du fichier CSV
def modifier_donnees_csv(donnees, index, nouvelle_valeur):
    if 0 <= index < len(donnees):
        print("Avant modification: {}".format(donnees[index]))
        donnees[index] = nouvelle_valeur
        print("Après modification: {}".format(donnees[index]))
        return donnees
    else:
        print("Index invalide. Modification non effectuée.")
        return donnees

# Fonction pour sauvegarder les données modifiées dans le fichier CSV
def sauvegarder_donnees_csv(fichier_csv, donnees):
    try:
        with open(fichier_csv, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(donnees)
        print("Modifications sauvegardées avec succès.")
    except Exception as e:
        print("Erreur lors de la sauvegarde du fichier CSV: {}".format(e))

# Chemin du fichier CSV
fichier_csv = "C:\Users\wiemb\Desktop\PyRevit\MyExtension.extension\profiles_data.csv"

# Étape 1 : Afficher les données actuelles
print("Affichage des données actuelles du fichier CSV:")
donnees = afficher_donnees_csv(fichier_csv)

# Vérification si le fichier contient des données
if donnees:
    # Étape 2 : Sélectionner une ligne à modifier
    try:
        index_a_modifier = int(input("Entrez le numéro de la ligne à modifier (0 à {}): ".format(len(donnees) - 1)))
        nouvelle_valeur = input("Entrez les nouvelles valeurs pour cette ligne (séparées par des virgules): ").split(',')

        # Vérification si les données modifiées sont correctes
        donnees_modifiees = modifier_donnees_csv(donnees, index_a_modifier, nouvelle_valeur)

        # Étape 3 : Sauvegarder les modifications
        sauvegarder_donnees_csv(fichier_csv, donnees_modifiees)

        # Étape 4 : Réafficher les données pour vérifier les modifications
        print("\nVérification des modifications apportées :")
        afficher_donnees_csv(fichier_csv)

    except ValueError:
        print("Entrée invalide. Assurez-vous d'entrer un numéro de ligne valide.")
else:
    print("Aucune donnée à modifier dans le fichier CSV.")
