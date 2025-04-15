# -*- coding: utf-8 -*-
"""
Script pour modifier la position Z d’un profil structurel dans une famille Revit.
"""

import clr
import traceback
from Autodesk.Revit.DB import *
from pyrevit import revit, DB, forms


def select_panel():
    try:
        panel = revit.pick_element(message="Select a panel")
        return panel
    except Exception as e:
        forms.alert("Error while selecting the panel : {}".format(e))
        return None


def open_family_in_editor(family_instance):
    try:
        family = family_instance.Symbol.Family
        family_doc = revit.doc.EditFamily(family)
        if not family_doc:
            forms.alert("Unable to open the family in the editor.", exitscript=True)
        return family_doc
    except Exception as e:
        forms.alert("Error while opening the family: {}".format(e))
        return None


def list_all_profile_instances(family_doc):
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilyInstance)
        profiles = [inst for inst in collector
                    if inst.Symbol
                    and "STR" in inst.Symbol.Family.Name
                    and "WIN" not in inst.Symbol.Family.Name]

        if not profiles:
            forms.alert("No profile found in the family.", exitscript=True)

        profile_data = []
        for inst in profiles:
            try:
                if hasattr(inst, 'Location') and inst.Location and hasattr(inst.Location, 'Point'):
                    z_value = inst.Location.Point.Z * 304.8  # Conversion to mm
                    if abs(z_value) < 0.01:
                        continue
                    display_text = "{} - Z: {:.1f}mm - ID: {}".format(
                        inst.Symbol.Family.Name,
                        z_value,
                        inst.Id
                    )
                    profile_data.append((inst, z_value, display_text))
                else:
                    display_text = "{} - Z: N/A - ID: {}".format(
                        inst.Symbol.Family.Name,
                        inst.Id
                    )
                    profile_data.append((inst, float('inf'), display_text))
            except Exception as ex:
                display_text = "{} - ID: {}".format(inst.Symbol.Family.Name, inst.Id)
                profile_data.append((inst, float('inf'), display_text))

        if not profile_data:
            forms.alert("No profile with Z≠0 found in the family.", exitscript=True)
            return None

        profile_data.sort(key=lambda x: x[1])
        profile_list = [data[2] for data in profile_data]

        selected_str = forms.SelectFromList.show(
            profile_list,
            title="Select a profile to modify its distances (profiles with Z=0 excluded)",
            multiselect=False
        )
        if not selected_str:
            forms.alert("No profile selected.", exitscript=True)

        try:
            selected_id = int(selected_str.split("ID: ")[1])
        except Exception as ex:
            forms.alert("Error while extracting the ID: {}".format(ex), exitscript=True)
            return None

        selected_instance = next((inst for inst in profiles if inst.Id.IntegerValue == selected_id), None)
        return selected_instance

    except Exception as e:
        forms.alert("Error while listing profiles: {}\n{}".format(e, traceback.format_exc()), exitscript=True)
        return None


class FamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True


def load_family_back_to_project(family_doc):
    if not family_doc:
        forms.alert("Invalid family document to load.", exitscript=True)
        return False

    try:
        family_path = family_doc.PathName
        family_doc.Save()  # Sauvegarder les modifications
        family_doc.Close(False)

        familyLoadOptions = FamilyLoadOptions()

        t = Transaction(revit.doc, "Load family into project")
        t.Start()
        try:
            success = revit.doc.LoadFamily(family_path, familyLoadOptions)
            t.Commit()
            if success:
                forms.alert("The family has been successfully loaded into the main project.")
                return True
            else:
                forms.alert("Failed to load the family into the main project.")
                return False
        except Exception as ex:
            t.RollBack()
            forms.alert("Error while loading: {}\n{}".format(ex, traceback.format_exc()))
            return False
    except Exception as e:
        forms.alert("Error while loading the family into the project: {}\n{}".format(e, traceback.format_exc()),
                    exitscript=True)
        return False


def modify_profile_position(instance):
    try:
        if not hasattr(instance, 'Location') or not instance.Location:
            forms.alert("The selected profile does not have a location.", exitscript=True)
            return None
        if not hasattr(instance.Location, 'Point') or instance.Location.Point is None:
            forms.alert("The profile position is not defined.", exitscript=True)
            return None

        current_location = instance.Location.Point
        family_name = instance.Symbol.Family.Name

        current_x_mm = current_location.X * 304.8
        current_y_mm = current_location.Y * 304.8
        current_z_mm = current_location.Z * 304.8

        new_z_str = forms.ask_for_string(
            prompt="New Z distance (in mm)",
            default=str(current_z_mm)
        )
        if new_z_str:
            try:
                new_z = float(new_z_str)
            except ValueError:
                forms.alert("The entered value is not valid.", exitscript=True)
                return None

            new_location = XYZ(current_location.X, current_location.Y, new_z / 304.8)
            return new_location
        else:
            forms.alert("Modification cancelled by user.", exitscript=True)
            return None

    except Exception as e:
        forms.alert("Error during modification: {}".format(e), exitscript=True)
        return None


def update_profile_location(family_doc, profile_instance, new_location):
    if not family_doc or not profile_instance or not new_location:
        return False

    t = Transaction(family_doc, "Modify profile distance")
    t.Start()
    try:
        profile_instance.Location.Point = new_location
        t.Commit()
        return True
    except Exception as ex:
        if t.HasStarted():
            t.RollBack()
        forms.alert("Error during modification: {}\n{}".format(ex, traceback.format_exc()))
        return False


def main():
    family_doc = None
    try:
        panel = select_panel()
        if not panel:
            return

        family_doc = open_family_in_editor(panel)
        if not family_doc:
            return

        profile_instance = list_all_profile_instances(family_doc)
        if not profile_instance:
            if family_doc:
                family_doc.Close(False)
            return

        new_location = modify_profile_position(profile_instance)
        if not new_location:
            if family_doc:
                family_doc.Close(False)
            return

        success = update_profile_location(family_doc, profile_instance, new_location)
        if not success:
            if family_doc:
                family_doc.Close(False)
            return

        load_family_back_to_project(family_doc)
        family_doc = None

    except Exception as e:
        forms.alert("Error during execution: {}\n{}".format(e, traceback.format_exc()))
        try:
            if family_doc:
                family_doc.Close(False)
        except:
            pass


if __name__ == "__main__":
    main()
