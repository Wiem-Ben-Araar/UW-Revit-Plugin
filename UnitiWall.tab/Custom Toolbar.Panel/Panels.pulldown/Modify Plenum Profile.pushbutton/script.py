# -*- coding: utf-8 -*-
"""
This script enables users to select and modify the position of plenum profiles in Revit.

Usage Instructions:

1. Select the desired plenum profile within Revit.
2. Input a new X-coordinate value (in millimeters) when prompted; the Y and Z coordinates will remain unchanged.
3. The script will update the profile's position accordingly.

Version: v1

Authors: Wiem Ben Araar, Amira Dridi
"""
import clr
import traceback
from Autodesk.Revit.DB import *
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI import TaskDialog

def select_panel():
    """Allows the user to select a panel in the project."""
    try:
        panel = revit.pick_element(message="Select a panel")
        return panel
    except Exception as e:
        forms.alert("Error while selecting the panel:  {}".format(e))
        return None

def get_panel_length_from_project(panel):
    """Returns the panel length in millimeters directly from the project."""
    try:
        length_param = panel.LookupParameter("L_PANNEAU")
        if length_param:
            length_value = length_param.AsDouble()
            length_in_mm = length_value * 304.8
            return length_in_mm
        else:
            param_names = [param.Definition.Name for param in panel.Parameters]
            TaskDialog.Show("Error", "Parameter 'L_PANNEAU' not found.\nAvailable parameters: {}".format(
                ', '.join(param_names)))
            return None
    except Exception as e:
        TaskDialog.Show("Error", "An error occurred while retrieving the length: {}".format(e))
        return None

def open_family_in_editor(family_instance):
    """Opens the family of the selected panel in the family editor."""
    try:
        family = family_instance.Symbol.Family
        family_doc = revit.doc.EditFamily(family)
        if not family_doc:
            forms.alert("Unable to open the family in the editor.", exitscript=True)
        return family_doc
    except Exception as e:
        forms.alert("Error while opening the family: {}".format(e))
        return None

def list_all_profile_instances(family_doc, panel_length=None):
    """Lists all profile instances in the family, filtered by name and sorted by X."""
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilyInstance)
        profiles = [inst for inst in collector if inst.Symbol and "PLN" in inst.Symbol.Family.Name]
        if not profiles:
            forms.alert("No profiles found in the family.", exitscript=True)

        profile_data = []
        for inst in profiles:
            try:
                if hasattr(inst, 'Location') and inst.Location and hasattr(inst.Location, 'Point'):
                    absolute_x_mm = inst.Location.Point.X * 304.8
                    if panel_length:
                        half_panel_length = panel_length / 2
                        relative_x_mm = absolute_x_mm + half_panel_length
                        display_text = "{} - Rel X: {:.1f}mm - ID: {}".format(
                            inst.Symbol.Family.Name, relative_x_mm, inst.Id)
                    else:
                        display_text = "{} - X: {:.1f}mm - ID: {}".format(
                            inst.Symbol.Family.Name, absolute_x_mm, inst.Id)
                    profile_data.append((inst, absolute_x_mm, display_text))
                else:
                    display_text = "{} - X: N/A - ID: {}".format(inst.Symbol.Family.Name, inst.Id)
                    profile_data.append((inst, float('inf'), display_text))
            except Exception as ex:
                display_text = "{} - ID: {}".format(inst.Symbol.Family.Name, inst.Id)
                profile_data.append((inst, float('inf'), display_text))

        profile_data.sort(key=lambda x: x[1])
        profile_list = [data[2] for data in profile_data]

        selected_pln = forms.SelectFromList.show(
            profile_list,
            title="Select a profile to modify its distance (profiles with Z=0 will be ignored)",
            multiselect=False
        )
        if not selected_pln:
            forms.alert("No profile selected.", exitscript=True)

        try:
            selected_id = int(selected_pln.split("ID: ")[1])
        except Exception as ex:
            forms.alert("Error extracting the ID: {}".format(ex), exitscript=True)
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
    """Loads the edited family back into the project."""
    if not family_doc:
        forms.alert("Invalid family document to load.", exitscript=True)
        return False
    try:
        family_doc.Save()
        family_path = family_doc.PathName
        family_doc.Close(False)

        familyLoadOptions = FamilyLoadOptions()
        t = Transaction(revit.doc, "Load family into project")
        t.Start()
        try:
            success = revit.doc.LoadFamily(family_path, familyLoadOptions)
            t.Commit()
            if success:
                forms.alert("The family was successfully loaded into the project.")
                return True
            else:
                forms.alert("Failed to load the family into the project.")
                return False
        except Exception as ex:
            t.RollBack()
            forms.alert("Error during loading: {}\n{}".format(ex, traceback.format_exc()))
            return False
    except Exception as e:
        forms.alert("Error loading the family into the project: {}\n{}".format(e, traceback.format_exc()), exitscript=True)
        return False

def modify_profile_position(instance, panel_length=None):
    """Modifies the X position of the selected profile instance."""
    try:
        if not hasattr(instance, 'Location') or not instance.Location or not hasattr(instance.Location, 'Point'):
            forms.alert("The selected profile does not have a defined location.", exitscript=True)
            return None

        current_location = instance.Location.Point
        family_name = instance.Symbol.Family.Name
        absolute_x_mm = current_location.X * 304.8
        current_y_mm = current_location.Y * 304.8
        current_z_mm = current_location.Z * 304.8

        relative_x_mm = absolute_x_mm
        if panel_length:
            half_panel_length = panel_length / 2
            relative_x_mm = absolute_x_mm + half_panel_length

        prompt_text = "New X position "
        if panel_length:
            prompt_text += "relative to panel center (in mm)"
            default_value = str(relative_x_mm)
        else:
            prompt_text += "(in mm)"
            default_value = str(absolute_x_mm)

        if panel_length:
            prompt_text += "\n\nPanel length: {:.1f}mm\nCurrent X position (relative): {:.1f}mm".format(
                panel_length, relative_x_mm)

        user_input = forms.ask_for_string(prompt=prompt_text, default=default_value)

        if user_input:
            try:
                new_x_mm = float(user_input)
                if panel_length:
                    half_panel_length = panel_length / 2
                    absolute_new_x_mm = new_x_mm - half_panel_length
                    if new_x_mm < 0 or new_x_mm > panel_length:
                        warning_msg = "The relative X position ({:.1f}mm) is outside the panel bounds (0 to {:.1f}mm).".format(
                            new_x_mm, panel_length)
                        if not forms.alert_yes_no(warning_msg + "\n\nDo you want to continue anyway?"):
                            return None
                else:
                    absolute_new_x_mm = new_x_mm
                    if absolute_new_x_mm < 0:
                        forms.alert("X position cannot be negative.", exitscript=True)
                        return None

                new_location = XYZ(absolute_new_x_mm / 304.8, current_location.Y, current_location.Z)

                return new_location

            except ValueError:
                forms.alert("Invalid input value.", exitscript=True)
                return None
        else:
            forms.alert("Modification canceled by the user.", exitscript=True)
            return None

    except Exception as e:
        forms.alert("Error during modification: {}".format(e), exitscript=True)
        return None

def update_profile_location(family_doc, profile_instance, new_location):
    """Updates the profile position in a separate transaction."""
    if not family_doc or not profile_instance or not new_location:
        return False

    t = Transaction(family_doc, "Update profile position")
    t.Start()
    try:
        profile_instance.Location.Point = new_location
        t.Commit()
        forms.alert("Profile position successfully updated.")
        return True
    except Exception as ex:
        if t.HasStarted():
            t.RollBack()
        forms.alert("Error updating position: {}\n{}".format(ex, traceback.format_exc()))
        return False

def main():
    family_doc = None
    try:
        panel = select_panel()
        if not panel:
            return

        panel_length = get_panel_length_from_project(panel)


        family_doc = open_family_in_editor(panel)
        if not family_doc:
            return

        profile_instance = list_all_profile_instances(family_doc, panel_length)
        if not profile_instance:
            if family_doc:
                family_doc.Close(False)
            return

        new_location = modify_profile_position(profile_instance, panel_length)
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