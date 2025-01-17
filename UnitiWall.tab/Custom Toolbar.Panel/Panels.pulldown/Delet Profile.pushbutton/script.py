import os
import clr
import traceback
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType

# --- Utility Functions ---
def select_panel():
    """Select a curtain wall panel in the project."""
    try:
        selection = revit.uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Select the curtain wall panel with profiles to delete")
        selected_element = revit.doc.GetElement(picked_ref.ElementId)

        if isinstance(selected_element, FamilyInstance):
            return selected_element
        else:
            TaskDialog.Show("Error", "The selected item is not a curtain wall panel.")
            return None
    except Exception as e:
        TaskDialog.Show("Error", "An error occurred while selecting the panel: {}".format(e))
        return None

def open_family_in_editor(panel):
    """Open the selected panel family in the Family Editor."""
    try:
        family = panel.Symbol.Family
        return revit.doc.EditFamily(family)
    except Exception as e:
        TaskDialog.Show("Error", "Error opening family in editor: {}".format(e))
        return None

def collect_profiles(family_doc, profile_symbol_name="PROFILE"):
    """Collect all profiles inside the panel (exclude side profiles)."""
    try:
        collector = FilteredElementCollector(family_doc).OfClass(FamilyInstance)
        profiles = []

        for el in collector:
            if profile_symbol_name in el.Symbol.Family.Name.upper():
                location = el.Location
                if isinstance(location, LocationPoint) and is_inside_panel(location.Point):
                    profiles.append(el)

        return profiles
    except Exception as e:
        TaskDialog.Show("Error", "Error collecting profiles: {}".format(e))
        return []

def is_inside_panel(point):
    """Determine if a profile is inside the panel."""
    # Example filter: Replace with actual logic to determine if the profile is in the panel.
    if 0.1 < point.X < 10.0 and 0.1 < point.Y < 10.0:
        return True
    return False

def delete_profiles(family_doc, profiles_to_delete):
    """Delete the selected profiles from the family document."""
    try:
        with Transaction(family_doc, "Delete Profiles") as t:
            t.Start()
            for profile in profiles_to_delete:
                family_doc.Delete(profile.Id)
            t.Commit()

        forms.alert("{} profiles deleted successfully.".format(len(profiles_to_delete)))
    except Exception as e:
        error_message = "Error while deleting profiles: {}\nTraceback:\n{}".format(str(e), traceback.format_exc())
        forms.alert(error_message, exitscript=True)

class FamilyLoadOptions(IFamilyLoadOptions):
    """Custom load options for loading the family back into the project."""
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

def save_and_load_family(family_doc):
    """Save the edited family and load it back into the main project."""
    try:
        temp_folder = os.path.expanduser("~\\AppData\\Local\\Temp")
        family_name = family_doc.Title + ".rfa"
        family_path = os.path.join(temp_folder, family_name)

        family_doc.SaveAs(family_path)
        family_doc.Close(False)

        familyLoadOptions = FamilyLoadOptions()
        with revit.Transaction("Load Family into Project"):
            loaded = revit.doc.LoadFamily(family_path, familyLoadOptions)
            if loaded:
                forms.alert("The family was successfully loaded into the main project.")
            else:
                forms.alert("Failed to load the family into the main project.")

        if os.path.exists(family_path):
            os.remove(family_path)
    except Exception as e:
        forms.alert("Error loading family into project: {}\nTraceback:\n{}".format(e, traceback.format_exc()), exitscript=True)

# --- Main Entry Point ---
def main():
    """Main script entry point."""
    panel = select_panel()
    if not panel:
        return

    family_doc = open_family_in_editor(panel)
    if not family_doc:
        return

    profiles = collect_profiles(family_doc)
    if not profiles:
        forms.alert("No profiles found in the selected panel family.")
        return

    action = forms.alert("Do you want to delete all profiles or select specific ones?", options=["Delete All", "Select Profiles"])

    if action == "Delete All":
        delete_profiles(family_doc, profiles)
    elif action == "Select Profiles":
        profile_names = ["{} (ID: {})".format(profile.Symbol.Family.Name, profile.Id) for profile in profiles]
        selected_names = forms.SelectFromList.show(profile_names, title="Select Profiles to Delete", multiselect=True)

        if not selected_names:
            forms.alert("No profiles selected for deletion.")
            return

        selected_profiles = [profile for profile in profiles if "{} (ID: {})".format(profile.Symbol.Family.Name, profile.Id) in selected_names]
        delete_profiles(family_doc, selected_profiles)

    save_and_load_family(family_doc)

# Execute script
if __name__ == "__main__":
    main()
