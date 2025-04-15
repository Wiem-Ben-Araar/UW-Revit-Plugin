# -*- coding: utf-8 -*-
import clr
import traceback
from Autodesk.Revit.DB import *
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI import TaskDialogCommonButtons, TaskDialogResult


def select_panel():
    """Permet à l'utilisateur de sélectionner un panneau dans le projet."""
    try:
        panel = revit.pick_element(message="Sélectionnez un panneau")
        return panel
    except Exception as e:
        forms.alert("Erreur lors de la sélection du panneau : {}".format(e))
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
    """Ouvre la famille du panneau sélectionné dans l'éditeur de famille."""
    try:
        family = family_instance.Symbol.Family
        family_doc = revit.doc.EditFamily(family)
        if not family_doc:
            forms.alert("Impossible d'ouvrir la famille dans l'éditeur.", exitscript=True)
        return family_doc
    except Exception as e:
        forms.alert("Erreur lors de l'ouverture de la famille : {}".format(e))
        return None


def select_profile_type():
    """Demande à l'utilisateur de choisir entre PLN ou STR."""
    options = ["Profil PLN", "Profil STR"]
    selected = forms.SelectFromList.show(
        options,
        title="Choisissez le type de profil à supprimer",
        multiselect=False,
        button_name="Sélectionner"
    )

    if selected == "Profil PLN":
        return "PLN"
    elif selected == "Profil STR":
        return "STR"
    else:
        return None


def get_profile_location(profile_instance):
    """
    Récupère la position X d'un profil en mm.
    Peut être utilisée pour les profils PLN et STR.
    """
    if hasattr(profile_instance, 'Location') and profile_instance.Location and hasattr(profile_instance.Location,
                                                                                       'Point'):
        return profile_instance.Location.Point.X * 304.8  # Conversion en mm
    return float('inf')  # Pour les profils sans location


def list_all_profile_instances(family_doc, profile_type, panel_length=None):
    """
    Liste toutes les instances de profils du type spécifié (PLN ou STR) dans la famille,
    triées par leur position X croissante.
    """
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilyInstance)
        profiles = []

        # Récupération des profils en fonction du type
        for inst in collector:
            if inst.Symbol and inst.Symbol.Family and profile_type in inst.Symbol.Family.Name:
                profiles.append(inst)

        if not profiles:
            forms.alert("Aucun profil de type « {} » trouvé dans la famille.".format(profile_type), exitscript=True)
            return None

        # Créer une liste de tuples (instance, position X, info d'affichage)
        profile_data = []
        for inst in profiles:
            try:
                # Position absolue dans la famille
                absolute_x_mm = get_profile_location(inst)

                # Simplification de l'affichage
                if panel_length is not None:
                    half_panel_length = panel_length / 2
                    relative_x_mm = absolute_x_mm + half_panel_length
                    position_text = "{:.0f} mm".format(relative_x_mm)
                else:
                    position_text = "{:.0f} mm".format(absolute_x_mm)

                # Si la position est infinie (pas de location), afficher N/A
                if absolute_x_mm == float('inf'):
                    position_text = "N/A"

                family_name = inst.Symbol.Family.Name if inst.Symbol and inst.Symbol.Family else "Inconnu"
                display_text = "{} : {} | Position : {} | ID: {}".format(
                    profile_type,
                    family_name,
                    position_text,
                    inst.Id.IntegerValue
                )
                profile_data.append((inst, absolute_x_mm, display_text))
            except Exception as ex:
                # En cas d'erreur, ajouter quand même le profil mais sans tri
                display_text = "{} : {} | ID: {}".format(
                    profile_type,
                    inst.Symbol.Family.Name if inst.Symbol and inst.Symbol.Family else "Inconnu",
                    inst.Id.IntegerValue
                )
                profile_data.append((inst, float('inf'), display_text))

        # Tri par valeur X croissante (position)
        profile_data.sort(key=lambda x: x[1])

        # Extraction des instances triées et des chaînes d'affichage
        profile_instances = [data[0] for data in profile_data]
        profile_list = [data[2] for data in profile_data]

        # Afficher la liste triée pour sélection
        selected_index = forms.SelectFromList.show(
            profile_list,
            title="Sélectionnez un profil {} à supprimer (triés par position)".format(profile_type),
            multiselect=False,
            button_name="Sélectionner"
        )

        if selected_index is None:
            forms.alert("Aucun profil sélectionné.", exitscript=True)
            return None

        # Trouver l'instance correspondante
        try:
            # Si SelectFromList.show retourne l'indice
            if isinstance(selected_index, int):
                return profile_instances[selected_index]
            # Si SelectFromList.show retourne la valeur
            else:
                selected_id = int(selected_index.split("ID: ")[1])
                return next((inst for inst in profiles if inst.Id.IntegerValue == selected_id), None)
        except Exception as ex:
            forms.alert("Erreur lors de la sélection du profil: {}".format(ex), exitscript=True)
            return None

    except Exception as e:
        forms.alert("Erreur lors du listing des profils : {}\n{}".format(e, traceback.format_exc()), exitscript=True)
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
    if not family_doc:
        forms.alert("Document de famille non valide à charger.", exitscript=True)
        return False

    try:
        # Sauvegarde du document de famille
        family_doc.Save()
        family_path = family_doc.PathName
        family_doc.Close(False)  # Fermer sans sauvegarder car déjà sauvegardé

        # Création des options de chargement
        familyLoadOptions = FamilyLoadOptions()

        # Création d'une transaction dans le document principal
        t = Transaction(revit.doc, "Charger famille dans le projet")
        t.Start()
        try:
            # Chargement de la famille
            success = revit.doc.LoadFamily(family_path, familyLoadOptions)
            t.Commit()

            if success:
                forms.alert("La famille a été chargée avec succès dans le projet principal.")
                return True
            else:
                forms.alert("Échec du chargement de la famille dans le projet principal.")
                return False
        except Exception as ex:
            t.RollBack()
            forms.alert("Erreur lors du chargement : {}\n{}".format(ex, traceback.format_exc()))
            return False
    except Exception as e:
        forms.alert("Erreur lors du chargement de la famille dans le projet : {}\n{}".format(e, traceback.format_exc()),
                    exitscript=True)
        return False


def delete_profile(family_doc, profile_instance):
    """
    Supprime le profil sélectionné dans une transaction séparée.
    """
    if not family_doc or not profile_instance:
        return False

    # Demander confirmation avant suppression
    family_name = profile_instance.Symbol.Family.Name if profile_instance.Symbol and profile_instance.Symbol.Family else "Inconnu"
    position_info = ""

    x_mm = get_profile_location(profile_instance)
    if x_mm != float('inf'):
        position_info = " à la position {:.0f} mm".format(x_mm)

    # Confirmation de suppression
    message = "Êtes-vous sûr de vouloir supprimer ce profil?\n{}{}".format(family_name, position_info)
    result = TaskDialog.Show("Confirmation", message,
                             TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No,
                             TaskDialogResult.No)

    if result != TaskDialogResult.Yes:
        return False

    # Création d'une transaction dans le document de famille
    t = Transaction(family_doc, "Supprimer profil")
    t.Start()
    try:
        # Supprimer l'instance
        family_doc.Delete(profile_instance.Id)
        # Validation de la transaction
        t.Commit()
        forms.alert("Profil supprimé avec succès.")
        return True
    except Exception as ex:
        # Annulation en cas d'erreur
        if t.HasStarted():
            t.RollBack()
        forms.alert("Erreur lors de la suppression : {}\n{}".format(ex, traceback.format_exc()))
        return False


def main():
    family_doc = None
    try:
        # 1. Sélectionner un panneau dans le projet
        panel = select_panel()
        if not panel:
            return

        # 1.1 Obtenir la longueur du panneau (pour l'affichage des positions relatives)
        panel_length = get_panel_length_from_project(panel)

        # 2. Ouvrir la famille du panneau dans l'éditeur
        family_doc = open_family_in_editor(panel)
        if not family_doc:
            return

        # 3. Choisir le type de profil à supprimer (PLN ou STR)
        profile_type = select_profile_type()
        if not profile_type:
            if family_doc:
                family_doc.Close(False)
            return

        # 4. Lister et sélectionner un profil à supprimer
        profile_instance = list_all_profile_instances(family_doc, profile_type, panel_length)
        if not profile_instance:
            # Si aucun profil n'est sélectionné, fermer la famille sans sauvegarder
            if family_doc:
                family_doc.Close(False)
            return

        # 5. Supprimer le profil sélectionné
        success = delete_profile(family_doc, profile_instance)
        if not success:
            if family_doc:
                family_doc.Close(False)
            return

        # 6. Charger la famille modifiée dans le projet principal
        load_family_back_to_project(family_doc)
        family_doc = None  # Pour éviter double fermeture si une exception est levée plus tard

    except Exception as e:
        forms.alert("Erreur lors de l'exécution : {}\n{}".format(e, traceback.format_exc()))
        # Tenter de fermer la famille en cas d'erreur
        try:
            if family_doc:
                family_doc.Close(False)
        except:
            pass


if __name__ == "__main__":
    main()# -*- coding: utf-8 -*-
import clr
import traceback
from Autodesk.Revit.DB import *
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI import TaskDialogCommonButtons, TaskDialogResult


def select_panel():
    """Permet à l'utilisateur de sélectionner un panneau dans le projet."""
    try:
        panel = revit.pick_element(message="Sélectionnez un panneau")
        return panel
    except Exception as e:
        forms.alert("Erreur lors de la sélection du panneau : {}".format(e))
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
    """Ouvre la famille du panneau sélectionné dans l'éditeur de famille."""
    try:
        family = family_instance.Symbol.Family
        family_doc = revit.doc.EditFamily(family)
        if not family_doc:
            forms.alert("Impossible d'ouvrir la famille dans l'éditeur.", exitscript=True)
        return family_doc
    except Exception as e:
        forms.alert("Erreur lors de l'ouverture de la famille : {}".format(e))
        return None


def select_profile_type():
    """Demande à l'utilisateur de choisir entre PLN ou STR."""
    options = ["Profil PLN", "Profil STR"]
    selected = forms.SelectFromList.show(
        options,
        title="Choisissez le type de profil à supprimer",
        multiselect=False,
        button_name="Sélectionner"
    )

    if selected == "Profil PLN":
        return "PLN"
    elif selected == "Profil STR":
        return "STR"
    else:
        return None


def get_profile_location(profile_instance):
    """
    Récupère la position X d'un profil en mm.
    Peut être utilisée pour les profils PLN et STR.
    """
    if hasattr(profile_instance, 'Location') and profile_instance.Location and hasattr(profile_instance.Location, 'Point'):
        return profile_instance.Location.Point.X * 304.8  # Conversion en mm
    return float('inf')  # Pour les profils sans location


def list_all_profile_instances(family_doc, profile_type, panel_length=None):
    """
    Liste toutes les instances de profils du type spécifié (PLN ou STR) dans la famille,
    triées par leur position X croissante.
    """
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilyInstance)
        profiles = []

        # Récupération des profils en fonction du type
        for inst in collector:
            if inst.Symbol and inst.Symbol.Family and profile_type in inst.Symbol.Family.Name:
                profiles.append(inst)

        if not profiles:
            forms.alert("Aucun profil de type « {} » trouvé dans la famille.".format(profile_type), exitscript=True)
            return None

        # Créer une liste de tuples (instance, position X, info d'affichage)
        profile_data = []
        for inst in profiles:
            try:
                # Position absolue dans la famille
                absolute_x_mm = get_profile_location(inst)

                # Simplification de l'affichage
                if panel_length is not None:
                    half_panel_length = panel_length / 2
                    relative_x_mm = absolute_x_mm + half_panel_length
                    position_text = "{:.0f} mm".format(relative_x_mm)
                else:
                    position_text = "{:.0f} mm".format(absolute_x_mm)

                # Si la position est infinie (pas de location), afficher N/A
                if absolute_x_mm == float('inf'):
                    position_text = "N/A"

                family_name = inst.Symbol.Family.Name if inst.Symbol and inst.Symbol.Family else "Inconnu"
                display_text = "{} : {} | Position : {} | ID: {}".format(
                    profile_type,
                    family_name,
                    position_text,
                    inst.Id.IntegerValue
                )
                profile_data.append((inst, absolute_x_mm, display_text))
            except Exception as ex:
                # En cas d'erreur, ajouter quand même le profil mais sans tri
                display_text = "{} : {} | ID: {}".format(
                    profile_type,
                    inst.Symbol.Family.Name if inst.Symbol and inst.Symbol.Family else "Inconnu",
                    inst.Id.IntegerValue
                )
                profile_data.append((inst, float('inf'), display_text))

        # Tri par valeur X croissante (position)
        profile_data.sort(key=lambda x: x[1])

        # Extraction des instances triées et des chaînes d'affichage
        profile_instances = [data[0] for data in profile_data]
        profile_list = [data[2] for data in profile_data]

        # Afficher la liste triée pour sélection
        selected_index = forms.SelectFromList.show(
            profile_list,
            title="Sélectionnez un profil {} à supprimer (triés par position)".format(profile_type),
            multiselect=False,
            button_name="Sélectionner"
        )

        if selected_index is None:
            forms.alert("Aucun profil sélectionné.", exitscript=True)
            return None

        # Trouver l'instance correspondante
        try:
            # Si SelectFromList.show retourne l'indice
            if isinstance(selected_index, int):
                return profile_instances[selected_index]
            # Si SelectFromList.show retourne la valeur
            else:
                selected_id = int(selected_index.split("ID: ")[1])
                return next((inst for inst in profiles if inst.Id.IntegerValue == selected_id), None)
        except Exception as ex:
            forms.alert("Erreur lors de la sélection du profil: {}".format(ex), exitscript=True)
            return None

    except Exception as e:
        forms.alert("Erreur lors du listing des profils : {}\n{}".format(e, traceback.format_exc()), exitscript=True)
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
    if not family_doc:
        forms.alert("Document de famille non valide à charger.", exitscript=True)
        return False

    try:
        # Sauvegarde du document de famille
        family_doc.Save()
        family_path = family_doc.PathName
        family_doc.Close(False)  # Fermer sans sauvegarder car déjà sauvegardé

        # Création des options de chargement
        familyLoadOptions = FamilyLoadOptions()

        # Création d'une transaction dans le document principal
        t = Transaction(revit.doc, "Charger famille dans le projet")
        t.Start()
        try:
            # Chargement de la famille
            success = revit.doc.LoadFamily(family_path, familyLoadOptions)
            t.Commit()

            if success:
                forms.alert("La famille a été chargée avec succès dans le projet principal.")
                return True
            else:
                forms.alert("Échec du chargement de la famille dans le projet principal.")
                return False
        except Exception as ex:
            t.RollBack()
            forms.alert("Erreur lors du chargement : {}\n{}".format(ex, traceback.format_exc()))
            return False
    except Exception as e:
        forms.alert("Erreur lors du chargement de la famille dans le projet : {}\n{}".format(e, traceback.format_exc()),
                    exitscript=True)
        return False


def delete_profile(family_doc, profile_instance):
    """
    Supprime le profil sélectionné dans une transaction séparée.
    """
    if not family_doc or not profile_instance:
        return False

    # Demander confirmation avant suppression
    family_name = profile_instance.Symbol.Family.Name if profile_instance.Symbol and profile_instance.Symbol.Family else "Inconnu"
    position_info = ""

    x_mm = get_profile_location(profile_instance)
    if x_mm != float('inf'):
        position_info = " à la position {:.0f} mm".format(x_mm)

    # Confirmation de suppression
    message = "Êtes-vous sûr de vouloir supprimer ce profil?\n{}{}".format(family_name, position_info)
    result = TaskDialog.Show("Confirmation", message,
                             TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No,
                             TaskDialogResult.No)

    if result != TaskDialogResult.Yes:
        return False

    # Création d'une transaction dans le document de famille
    t = Transaction(family_doc, "Supprimer profil")
    t.Start()
    try:
        # Supprimer l'instance
        family_doc.Delete(profile_instance.Id)
        # Validation de la transaction
        t.Commit()
        forms.alert("Profil supprimé avec succès.")
        return True
    except Exception as ex:
        # Annulation en cas d'erreur
        if t.HasStarted():
            t.RollBack()
        forms.alert("Erreur lors de la suppression : {}\n{}".format(ex, traceback.format_exc()))
        return False


def main():
    family_doc = None
    try:
        # 1. Sélectionner un panneau dans le projet
        panel = select_panel()
        if not panel:
            return

        # 1.1 Obtenir la longueur du panneau (pour l'affichage des positions relatives)
        panel_length = get_panel_length_from_project(panel)

        # 2. Ouvrir la famille du panneau dans l'éditeur
        family_doc = open_family_in_editor(panel)
        if not family_doc:
            return

        # 3. Choisir le type de profil à supprimer (PLN ou STR)
        profile_type = select_profile_type()
        if not profile_type:
            if family_doc:
                family_doc.Close(False)
            return

        # 4. Lister et sélectionner un profil à supprimer
        profile_instance = list_all_profile_instances(family_doc, profile_type, panel_length)
        if not profile_instance:
            # Si aucun profil n'est sélectionné, fermer la famille sans sauvegarder
            if family_doc:
                family_doc.Close(False)
            return

        # 5. Supprimer le profil sélectionné
        success = delete_profile(family_doc, profile_instance)
        if not success:
            if family_doc:
                family_doc.Close(False)
            return

        # 6. Charger la famille modifiée dans le projet principal
        load_family_back_to_project(family_doc)
        family_doc = None  # Pour éviter double fermeture si une exception est levée plus tard

    except Exception as e:
        forms.alert("Erreur lors de l'exécution : {}\n{}".format(e, traceback.format_exc()))
        # Tenter de fermer la famille en cas d'erreur
        try:
            if family_doc:
                family_doc.Close(False)
        except:
            pass


if __name__ == "__main__":
    main()# -*- coding: utf-8 -*-
import clr
import traceback
from Autodesk.Revit.DB import *
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI import TaskDialogCommonButtons, TaskDialogResult


def select_panel():
    """Permet à l'utilisateur de sélectionner un panneau dans le projet."""
    try:
        panel = revit.pick_element(message="Sélectionnez un panneau")
        return panel
    except Exception as e:
        forms.alert("Erreur lors de la sélection du panneau : {}".format(e))
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
    """Ouvre la famille du panneau sélectionné dans l'éditeur de famille."""
    try:
        family = family_instance.Symbol.Family
        family_doc = revit.doc.EditFamily(family)
        if not family_doc:
            forms.alert("Impossible d'ouvrir la famille dans l'éditeur.", exitscript=True)
        return family_doc
    except Exception as e:
        forms.alert("Erreur lors de l'ouverture de la famille : {}".format(e))
        return None


def select_profile_type():
    """Demande à l'utilisateur de choisir entre PLN ou STR."""
    options = ["Profil PLN", "Profil STR"]
    selected = forms.SelectFromList.show(
        options,
        title="Choisissez le type de profil à supprimer",
        multiselect=False,
        button_name="Sélectionner"
    )

    if selected == "Profil PLN":
        return "PLN"
    elif selected == "Profil STR":
        return "STR"
    else:
        return None


def get_profile_location(profile_instance):
    """
    Récupère la position X d'un profil en mm.
    Peut être utilisée pour les profils PLN et STR.
    """
    if hasattr(profile_instance, 'Location') and profile_instance.Location and hasattr(profile_instance.Location, 'Point'):
        return profile_instance.Location.Point.X * 304.8  # Conversion en mm
    return float('inf')  # Pour les profils sans location


def list_all_profile_instances(family_doc, profile_type, panel_length=None):
    """
    Liste toutes les instances de profils du type spécifié (PLN ou STR) dans la famille,
    triées par leur position X croissante.
    """
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilyInstance)
        profiles = []

        # Récupération des profils en fonction du type
        for inst in collector:
            if inst.Symbol and inst.Symbol.Family and profile_type in inst.Symbol.Family.Name:
                profiles.append(inst)

        if not profiles:
            forms.alert("Aucun profil de type « {} » trouvé dans la famille.".format(profile_type), exitscript=True)
            return None

        # Créer une liste de tuples (instance, position X, info d'affichage)
        profile_data = []
        for inst in profiles:
            try:
                # Position absolue dans la famille
                absolute_x_mm = get_profile_location(inst)

                # Simplification de l'affichage
                if panel_length is not None:
                    half_panel_length = panel_length / 2
                    relative_x_mm = absolute_x_mm + half_panel_length
                    position_text = "{:.0f} mm".format(relative_x_mm)
                else:
                    position_text = "{:.0f} mm".format(absolute_x_mm)

                # Si la position est infinie (pas de location), afficher N/A
                if absolute_x_mm == float('inf'):
                    position_text = "N/A"

                family_name = inst.Symbol.Family.Name if inst.Symbol and inst.Symbol.Family else "Inconnu"
                display_text = "{} : {} | Position : {} | ID: {}".format(
                    profile_type,
                    family_name,
                    position_text,
                    inst.Id.IntegerValue
                )
                profile_data.append((inst, absolute_x_mm, display_text))
            except Exception as ex:
                # En cas d'erreur, ajouter quand même le profil mais sans tri
                display_text = "{} : {} | ID: {}".format(
                    profile_type,
                    inst.Symbol.Family.Name if inst.Symbol and inst.Symbol.Family else "Inconnu",
                    inst.Id.IntegerValue
                )
                profile_data.append((inst, float('inf'), display_text))

        # Tri par valeur X croissante (position)
        profile_data.sort(key=lambda x: x[1])

        # Extraction des instances triées et des chaînes d'affichage
        profile_instances = [data[0] for data in profile_data]
        profile_list = [data[2] for data in profile_data]

        # Afficher la liste triée pour sélection
        selected_index = forms.SelectFromList.show(
            profile_list,
            title="Sélectionnez un profil {} à supprimer (triés par position)".format(profile_type),
            multiselect=False,
            button_name="Sélectionner"
        )

        if selected_index is None:
            forms.alert("Aucun profil sélectionné.", exitscript=True)
            return None

        # Trouver l'instance correspondante
        try:
            # Si SelectFromList.show retourne l'indice
            if isinstance(selected_index, int):
                return profile_instances[selected_index]
            # Si SelectFromList.show retourne la valeur
            else:
                selected_id = int(selected_index.split("ID: ")[1])
                return next((inst for inst in profiles if inst.Id.IntegerValue == selected_id), None)
        except Exception as ex:
            forms.alert("Erreur lors de la sélection du profil: {}".format(ex), exitscript=True)
            return None

    except Exception as e:
        forms.alert("Erreur lors du listing des profils : {}\n{}".format(e, traceback.format_exc()), exitscript=True)
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
    if not family_doc:
        forms.alert("Document de famille non valide à charger.", exitscript=True)
        return False

    try:
        # Sauvegarde du document de famille
        family_doc.Save()
        family_path = family_doc.PathName
        family_doc.Close(False)  # Fermer sans sauvegarder car déjà sauvegardé

        # Création des options de chargement
        familyLoadOptions = FamilyLoadOptions()

        # Création d'une transaction dans le document principal
        t = Transaction(revit.doc, "Charger famille dans le projet")
        t.Start()
        try:
            # Chargement de la famille
            success = revit.doc.LoadFamily(family_path, familyLoadOptions)
            t.Commit()

            if success:
                forms.alert("La famille a été chargée avec succès dans le projet principal.")
                return True
            else:
                forms.alert("Échec du chargement de la famille dans le projet principal.")
                return False
        except Exception as ex:
            t.RollBack()
            forms.alert("Erreur lors du chargement : {}\n{}".format(ex, traceback.format_exc()))
            return False
    except Exception as e:
        forms.alert("Erreur lors du chargement de la famille dans le projet : {}\n{}".format(e, traceback.format_exc()),
                    exitscript=True)
        return False


def delete_profile(family_doc, profile_instance):
    """
    Supprime le profil sélectionné dans une transaction séparée.
    """
    if not family_doc or not profile_instance:
        return False

    # Demander confirmation avant suppression
    family_name = profile_instance.Symbol.Family.Name if profile_instance.Symbol and profile_instance.Symbol.Family else "Inconnu"
    position_info = ""

    x_mm = get_profile_location(profile_instance)
    if x_mm != float('inf'):
        position_info = " à la position {:.0f} mm".format(x_mm)

    # Confirmation de suppression
    message = "Êtes-vous sûr de vouloir supprimer ce profil?\n{}{}".format(family_name, position_info)
    result = TaskDialog.Show("Confirmation", message,
                             TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No,
                             TaskDialogResult.No)

    if result != TaskDialogResult.Yes:
        return False

    # Création d'une transaction dans le document de famille
    t = Transaction(family_doc, "Supprimer profil")
    t.Start()
    try:
        # Supprimer l'instance
        family_doc.Delete(profile_instance.Id)
        # Validation de la transaction
        t.Commit()
        forms.alert("Profil supprimé avec succès.")
        return True
    except Exception as ex:
        # Annulation en cas d'erreur
        if t.HasStarted():
            t.RollBack()
        forms.alert("Erreur lors de la suppression : {}\n{}".format(ex, traceback.format_exc()))
        return False


def main():
    family_doc = None
    try:
        # 1. Sélectionner un panneau dans le projet
        panel = select_panel()
        if not panel:
            return

        # 1.1 Obtenir la longueur du panneau (pour l'affichage des positions relatives)
        panel_length = get_panel_length_from_project(panel)


        # 2. Ouvrir la famille du panneau dans l'éditeur
        family_doc = open_family_in_editor(panel)
        if not family_doc:
            return

        # 3. Choisir le type de profil à supprimer (PLN ou STR)
        profile_type = select_profile_type()
        if not profile_type:
            if family_doc:
                family_doc.Close(False)
            return

        # 4. Lister et sélectionner un profil à supprimer
        profile_instance = list_all_profile_instances(family_doc, profile_type, panel_length)
        if not profile_instance:
            # Si aucun profil n'est sélectionné, fermer la famille sans sauvegarder
            if family_doc:
                family_doc.Close(False)
            return

        # 5. Supprimer le profil sélectionné
        success = delete_profile(family_doc, profile_instance)
        if not success:
            if family_doc:
                family_doc.Close(False)
            return

        # 6. Charger la famille modifiée dans le projet principal
        load_family_back_to_project(family_doc)
        family_doc = None  # Pour éviter double fermeture si une exception est levée plus tard

    except Exception as e:
        forms.alert("Erreur lors de l'exécution : {}\n{}".format(e, traceback.format_exc()))
        # Tenter de fermer la famille en cas d'erreur
        try:
            if family_doc:
                family_doc.Close(False)
        except:
            pass


if __name__ == "__main__":
    main()
