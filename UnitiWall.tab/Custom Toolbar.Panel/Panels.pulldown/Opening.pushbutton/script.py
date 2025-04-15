#' -*- coding: utf-8 -*-
"""
Description:
This script is designed to facilitate the addition of profiles, including a plenum profile, to a curtain wall panel in Autodesk Revit. It provides a user-friendly interface for selecting panels, specifying the number of profiles, and defining the distance between them. The script also allows for the modification of panel parameters and the duplication of families before applying changes.

Key Features:
- **Panel Selection**: Users can select a curtain wall panel from the project.
- **Profile Addition**: Users can specify the number of profiles to add, and define the distance between them.
- **Parameter Modification**: Users can modify existing parameters of the opening.
- **Family Duplication**: The script offers the option to duplicate the panel's family before making modifications, ensuring the original family remains unchanged.

How to Use:
1. **Select a Panel**: The user selects a curtain wall panel from the project.
2. **Choose Action**: The user can choose to either modify the panel's parameters or insert profiles.
3. **Modify Position & Dimensions**: If modifying parameters, the user can adjust values such as L_WINDOW, LEFT, SILL, and H_WINDOW, with values displayed in millimeters.
4. **Insert Profiles**: If inserting profiles, the user specifies the number of profiles and the distance between them. The script ensures that the profiles fit within the panel's dimensions.
5. **Family Duplication**: Optionally, the user can duplicate the panel's family before making changes, preserving the original family.
6. **Apply Changes**: The script applies the changes and reloads the modified family into the project.

Version: v3
Author: Wiem Ben Araar, Amira Dridi
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


def get_existing_parameters(panel):
    """Retrieves the existing parameters of a curtain wall panel and converts them to millimeters."""
    try:
        # Dictionary to store the parameters
        parameters = {}
        panel_type = revit.doc.GetElement(panel.GetTypeId())
        # Retrieve specific parameters
        parameters['L_WINDOW'] = panel.LookupParameter("L_WINDOW")
        parameters['LEFT'] = panel.LookupParameter("LEFT")
        parameters['SILL'] = panel.LookupParameter("SILL")
        parameters['H_WINDOW'] = panel.LookupParameter("H_WINDOW")

        # Check if the parameters exist
        for param_name, param in parameters.items():
            if param is None:
                TaskDialog.Show("Error", "The parameter '{}' does not exist in the selected element.".format(param_name))
                return None

        # Convert the values to millimeters
        parameters_mm = {}
        for param_name, param in parameters.items():
            if param.StorageType == StorageType.Double:
                value_feet = param.AsDouble()  # Value in feet
                value_mm = value_feet * 304.8  # Conversion to millimeters
                parameters_mm[param_name] = value_mm
            else:
                parameters_mm[param_name] = param.AsValueString()  # Keep other types of parameters (string, etc.)

        return parameters, parameters_mm

    except Exception as e:
        TaskDialog.Show("Error", "Error retrieving parameters: {}".format(str(e)))
        return None, None

def modify_parameters_ui(parameters_mm):
    """Displays a user interface to modify the parameters (in millimeters)."""
    try:
        # Create a dictionary to store the new values
        new_values = {}

        # Display a dialog box for each parameter
        for param_name, current_value in parameters_mm.items():
            new_value = forms.ask_for_string(
                prompt="Modify the value of '{}' (current: {} mm):".format(param_name, current_value),
                title="Modify {}".format(param_name),
                default=str(current_value)
            )

            if new_value:
                new_values[param_name] = new_value

        return new_values

    except Exception as e:
        forms.alert("Error modifying parameters: {}".format(str(e)))
        return None

def apply_parameter_changes(panel, parameters, new_values):
    """Applies the new values to the element's parameters (in millimeters)."""
    try:
        with Transaction(revit.doc, "Modify Position & Dimensions") as t:
            t.Start()

            for param_name, new_value in new_values.items():
                param = parameters[param_name]  # Access the Parameter object

                # Convert the new value based on the parameter type
                if param.StorageType == StorageType.String:
                    param.Set(new_value)
                elif param.StorageType == StorageType.Double:
                    # Convert the value from millimeters to feet
                    value_mm = float(new_value)
                    value_feet = value_mm / 304.8  # Conversion to feet
                    param.Set(value_feet)
                elif param.StorageType == StorageType.Integer:
                    param.Set(int(new_value))

            t.Commit()

        TaskDialog.Show("Success", "The parameters have been successfully modified.")

    except Exception as e:
        TaskDialog.Show("Error", "Error modifying parameters: {}".format(str(e)))



def add_profiles_to_family(family_doc, profile_symbol, num_profiles, distance_mm):
    """Adds multiple instances of the selected profile to the family at a specific position, taking into account the panel width."""
    try:
        # Initial position
        insertion_point_x_ft = 0
        insertion_point_y_ft = 0
        insertion_point_z_ft = 0

        # Retrieve the SILL and LINTEL values for the Z constraints
        panel = select_panel()
        if not panel:
            TaskDialog.Show("Error", "No panel selected.")
            return

        sill_param = panel.LookupParameter("SILL")
        right_param = panel.LookupParameter("RIGHT")
        lintel_param = panel.LookupParameter("LINTEL")
        left_param = panel.LookupParameter("LEFT")
        l_window_param = panel.LookupParameter("L_WINDOW")

        if not sill_param or not lintel_param or not left_param or not l_window_param:
            TaskDialog.Show("Error", "The parameters SILL, LINTEL, LEFT or L_WINDOW could not be found in the panel.")
            return

        sill_value_ft = sill_param.AsDouble()  # SILL value in feet
        right_value_ft = right_param.AsDouble()
        lintel_value_ft = lintel_param.AsDouble()  # LINTEL value in feet
        left_value_ft = left_param.AsDouble()  # LEFT value in feet
        l_window_value_ft = l_window_param.AsDouble()  # L_WINDOW value in feet

        # Convert LEFT and L_WINDOW to millimeters for display
        left_value_mm = left_value_ft * 304.8
        l_window_value_mm = l_window_value_ft * 304.8
        right_value_mm = right_value_ft * 304.8

        if profile_symbol.Family.Name == "PROFILE_PLN_124_V_WIN_UP":
            panel = select_panel()
            if panel:
                # Retrieve the LINTEL parameter for the height
                panel_height_param = panel.LookupParameter("LINTEL")
                if panel_height_param:
                    lintel_value_ft = panel_height_param.AsDouble()  # In feet
                    insertion_point_y_ft = 294 / 304.8
                    insertion_point_z_ft = lintel_value_ft

        elif profile_symbol.Family.Name == "PROFILE_STR_152_V_WIN_UP":
            # Select the panel
            panel = select_panel()

            if panel is None:
                TaskDialog.Show("Error", "No panel selected.")
            else:
                # Retrieve the LINTEL parameter value to set Z (ensure the panel is defined and the parameter exists)
                panel_height_param = panel.LookupParameter("LINTEL")
                if panel_height_param:
                    # Get the LINTEL value in feet (or internal units as needed)
                    lintel_value_ft = panel_height_param.AsDouble()

                    # Calculate the Z position in feet (using LINTEL directly)
                    insertion_point_z_ft = lintel_value_ft  # Using LINTEL for the Z position
                    insertion_point_y_ft = 126 / 304.8  # Y offset
                else:
                    TaskDialog.Show("Error", "The LINTEL parameter could not be retrieved.")

        elif profile_symbol.Family.Name == "PROFILE_PLN_124_V_WIN_DOWN":
            # Calculate the Y elevation in feet (convert 168 mm to feet)
            insertion_point_y_ft = 294 / 304.8  # 168 mm converted to feet

        elif profile_symbol.Family.Name == "PROFILE_STR_152_V_WIN_DOWN":
            height_param = profile_symbol.LookupParameter("H_STR_152")
            if height_param and not height_param.IsReadOnly:
                height_param.Set("SILL")
            insertion_point_y_ft = 126 / 304.8  # Y offset
        elif profile_symbol.Family.Name == "PROFILE_PLN_124_H_WIN_LEFT":
            panel = select_panel()

            # Retrieve the LEFT value to set the profile position
            left_param = panel.LookupParameter("LEFT")

            largeur_param = profile_symbol.LookupParameter("L_STR_152_WIN_LEFT")  # Width parameter to modify

            if left_param and left_param.HasValue:
                left_value = left_param.AsDouble()  # Get the current LEFT value in feet
            else:
                TaskDialog.Show("Error", "The LEFT parameter is not found or has no value.")

            # Retrieve the panel length (width) in millimeters
            panel_length_param = panel.LookupParameter("Largeur")
            if panel_length_param and panel_length_param.HasValue:
                panel_length_mm = panel_length_param.AsDouble() * 304.8  # Convert length from feet to millimeters

                # Calculate half the panel length and the position based on LEFT
                half_panel_length_mm = panel_length_mm / 2
                half_left_value_mm = left_value * 304.8 / 2  # Convert LEFT to millimeters and divide by 2

                # Calculate the X position for the profile starting from the center of the panel
                insertion_point_x_mm = half_panel_length_mm - half_left_value_mm
                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion to feet
                insertion_point_y_ft = 294 / 304.8  # Conversion from 168 mm to feet
            else:
                TaskDialog.Show("Error", "The 'Width' parameter is not found or has no value.")

        elif profile_symbol.Family.Name == "PROFILE_STR_152_H_WIN_LEFT":
            panel = select_panel()

            # Retrieve the LEFT value to set the profile position
            left_param = panel.LookupParameter("LEFT")
            largeur_param = profile_symbol.LookupParameter("L_STR_152_WIN_LEFT")  # Width parameter to modify

            if left_param and left_param.HasValue:
                left_value = left_param.AsDouble()  # Get the current LEFT value in feet
            else:
                TaskDialog.Show("Error", "The LEFT parameter is not found or has no value.")

            # Retrieve the panel length (width) in millimeters
            panel_length_param = panel.LookupParameter("Largeur")
            if panel_length_param and panel_length_param.HasValue:
                panel_length_mm = panel_length_param.AsDouble() * 304.8  # Convert length from feet to millimeters

                # Calculate half the panel length and the position based on LEFT
                half_panel_length_mm = panel_length_mm / 2
                half_left_value_mm = left_value * 304.8 / 2  # Convert LEFT to millimeters and divide by 2

                # Calculate the X position for the profile starting from the center of the panel
                insertion_point_x_mm = half_panel_length_mm - half_left_value_mm
                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion to feet
                insertion_point_y_ft = 126 / 304.8  # Conversion from 168 mm to feet
            else:
                TaskDialog.Show("Error", "The 'Width' parameter is not found or has no value.")

        elif profile_symbol.Family.Name == "PROFILE_PLN_124_H_WIN_RIGHT":
            panel = select_panel()

            # Retrieve the RIGHT parameter value from the panel
            right_value_param = panel.LookupParameter("RIGHT")
            if right_value_param and right_value_param.HasValue:
                # Convert the RIGHT value to feet
                right_value = right_value_param.AsDouble()
            else:
                TaskDialog.Show("Error", "The 'RIGHT' parameter is not found or has no value in the panel.")
                return  # Exit if RIGHT is missing to avoid errors

            # Open the family in the editor to modify the parameter 'L_STR_152_WIN_RIGHT'
            family_doc = open_family_in_editor(panel)
            if family_doc:
                # Access the family parameters
                parameters = family_doc.FamilyManager.Parameters

                # Search for the parameter 'L_STR_152_WIN_RIGHT'
                largeur_param = None
                for param in parameters:
                    if param.Definition.Name == "L_STR_152_WIN_RIGHT":
                        largeur_param = param
                        break
            else:
                TaskDialog.Show("Error", "Unable to open the family in the editor.")

            # Calculate the X position for insertion based on the center of the panel
            panel_length_param = panel.LookupParameter("Largeur")
            if panel_length_param and panel_length_param.HasValue:
                panel_length_mm = panel_length_param.AsDouble() * 304.8  # Convert length to millimeters

                # Calculate half the panel length and the position based on RIGHT
                half_panel_length_mm = panel_length_mm / 2
                half_right_value_mm = right_value * 304.8 / 2  # Convert RIGHT to millimeters and divide by 2

                # Calculate the X position for the profile
                insertion_point_x_mm = -half_panel_length_mm + half_right_value_mm
                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion to feet
                insertion_point_y_ft = 294 / 304.8  # Conversion from 168 mm to feet
            else:
                TaskDialog.Show("Error", "The 'Width' parameter is not found or has no value.")

        # Check if the profile corresponds to PROFILE_STR_152_H_WIN_RIGHT
        elif profile_symbol.Family.Name == "PROFILE_STR_152_H_WIN_RIGHT":
            panel = select_panel()
            if panel:
                # Retrieve the RIGHT parameter value from the panel
                right_value_param = panel.LookupParameter("RIGHT")
                if right_value_param and right_value_param.HasValue:
                    # Convert the RIGHT value to feet
                    right_value = right_value_param.AsDouble()
                else:
                    TaskDialog.Show("Error", "The 'RIGHT' parameter is not found or has no value in the panel.")
                    return  # Exit if RIGHT is missing to avoid errors

                # Open the family in the editor to modify the parameter 'L_STR_152_WIN_RIGHT'
                family_doc = open_family_in_editor(panel)
                if family_doc:
                    # Access the family parameters
                    parameters = family_doc.FamilyManager.Parameters

                    # Search for the parameter 'L_STR_152_WIN_RIGHT'
                    largeur_param = next((param for param in parameters if param.Definition.Name == "L_STR_152_WIN_RIGHT"), None)
                else:
                    TaskDialog.Show("Error", "Unable to open the family in the editor.")

                # Calculate the X position for insertion based on the center of the panel
                panel_length_param = panel.LookupParameter("Largeur")
                if panel_length_param and panel_length_param.HasValue:
                    panel_length_mm = panel_length_param.AsDouble() * 304.8  # Convert length to millimeters

                    # Calculate half the panel length and the position based on RIGHT
                    half_panel_length_mm = panel_length_mm / 2
                    half_right_value_mm = right_value * 304.8 / 2  # Convert RIGHT to millimeters and divide by 2

                    # Calculate the X position for the profile
                    insertion_point_x_mm = -half_panel_length_mm + half_right_value_mm
                    insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion to feet
                    insertion_point_y_ft = 126 / 304.8  # Conversion from 168 mm to feet
                else:
                    TaskDialog.Show("Error", "The 'Width' parameter is not found or has no value in the panel.")
            else:
                TaskDialog.Show("Error", "No panel was selected.")

        # Functionality to request the Z value (in mm) for certain profiles
        if profile_symbol.Family.Name in [
            "PROFILE_PLN_124_H_WIN_LEFT", "PROFILE_PLN_124_H_WIN_RIGHT"
        ]:
            while True:
                # Ensure that z_max_mm is greater than z_min_mm before proceeding
                z_max_mm = (lintel_value_ft * 304.8) - ((num_profiles - 1) * distance_mm) - 32
                z_min_mm = (sill_value_ft * 304.8) + 31.5

                if z_max_mm < z_min_mm:
                    forms.alert(
                        "Error: The available space is insufficient for {} profiles with a distance of {} mm between them.\n"
                        "Please reduce the number of profiles or the distance between them.".format(num_profiles, distance_mm)
                    )
                    # Allow the user to modify the values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new distance between profiles (in mm):",
                        title="Distance between profiles"
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
                        break  # Exit if the user does not wish to enter new values

                # Request the Z value
                while True:
                    user_input_z_mm = forms.ask_for_string(
                        prompt="Enter the Z value (in mm) for {} between [{:.2f} , {:.2f}]:".format(
                            profile_symbol.Family.Name, z_min_mm, z_max_mm
                        ),
                        title="Z Value"
                    )
                    if not user_input_z_mm:
                        forms.alert("No value was entered for Z. Please try again.")
                        continue  # Ask again

                    try:
                        insertion_point_z_mm = float(user_input_z_mm)
                        insertion_point_z_ft = insertion_point_z_mm / 304.8  # Convert to feet

                        if z_min_mm <= insertion_point_z_mm <= z_max_mm:
                            break  # Exit the loop if the value is correct
                        else:
                            forms.alert(
                                "The Z value must be between [{:.2f} and {:.2f}].".format(z_min_mm, z_max_mm)
                            )
                    except ValueError:
                        forms.alert("Error: The value entered for Z is not valid. Please enter a number.")

                break  # Everything is correct, exit the main loop

        if profile_symbol.Family.Name in [
            "PROFILE_STR_152_H_WIN_RIGHT", "PROFILE_STR_152_H_WIN_LEFT"
        ]:
            while True:
                # Ensure that z_max_mm is greater than z_min_mm before proceeding
                z_max_mm = (lintel_value_ft * 304.8) - ((num_profiles - 1) * distance_mm) - 32
                z_min_mm = (sill_value_ft * 304.8) + 32  # Correction

                if z_max_mm < z_min_mm:
                    forms.alert(
                        "Error: The available space is insufficient for {} profiles with a distance of {} mm between them.\n"
                        "Please reduce the number of profiles or the distance between them.".format(num_profiles, distance_mm)
                    )
                    # Allow the user to modify the values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new distance between profiles (in mm):",
                        title="Distance between profiles"
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
                        break  # Exit if the user does not wish to enter new values

                # Request the Z value
                while True:
                    user_input_z_mm = forms.ask_for_string(
                        prompt="Enter the Z value (in mm) for {} (between {:.2f} mm and {:.2f} mm):".format(
                            profile_symbol.Family.Name, z_min_mm, z_max_mm
                        ),
                        title="Z Value"
                    )

                    if not user_input_z_mm:
                        forms.alert("No value was entered for Z. Please try again.")
                        continue  # Ask again

                    try:
                        insertion_point_z_mm = float(user_input_z_mm)
                        insertion_point_z_ft = insertion_point_z_mm / 304.8  # Convert to feet

                        if z_min_mm <= insertion_point_z_mm <= z_max_mm:
                            break  # Exit the loop if the value is correct
                        else:
                            forms.alert(
                                "The Z value must be between {:.2f} mm and {:.2f} mm.".format(z_min_mm, z_max_mm)
                            )
                    except ValueError:
                        forms.alert("Error: The value entered for Z is not valid. Please enter a number.")

                break  # Everything is correct, exit the main loop

        # Retrieve the panel width before using it
        panel_length_param = panel.LookupParameter("Largeur")
        if panel_length_param and panel_length_param.HasValue:
            panel_length_mm = panel_length_param.AsDouble() * 304.8
        else:
            forms.alert("Error: Unable to retrieve the panel width.")
            return  # Stop execution if the panel width is not found

        # Check if panel_length_mm is properly defined
        if profile_symbol.Family.Name in ["PROFILE_STR_152_V_WIN_UP", "PROFILE_STR_152_V_WIN_DOWN"]:
            while True:
                # The minimum interval corresponds to the allowed minimum value
                intervalle_min_mm = right_value_mm + 32
                # The maximum interval takes into account the last profile and no space before the first
                intervalle_max_mm = right_value_mm + l_window_value_mm - ((num_profiles - 1) * distance_mm) - 32
                # Check if the available space is insufficient
                if intervalle_max_mm < intervalle_min_mm:
                    forms.alert(
                        "Error: The available space is insufficient for " + str(num_profiles) +
                        " profiles with a distance of " + str(distance_mm) + " mm between them.\n" +
                        "Please reduce the number of profiles or the distance between them."
                    )
                    # Allow the user to modify the values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new distance between profiles (in mm):",
                        title="Distance between profiles"
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
                        break  # Exit if the user does not wish to enter new values
                user_input_x_mm = forms.ask_for_string(
                    prompt="Enter the X value (in mm) for " + profile_symbol.Family.Name +
                           " between [" + str(round(intervalle_min_mm, 2)) + " , " +
                           str(round(intervalle_max_mm, 2)) + "]",
                    title="X Value"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Strict check to include the minimum and maximum value
                        if intervalle_min_mm - 1 <= position_x_mm <= intervalle_max_mm:
                            if panel_length_mm is not None:  # Explicit check
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion from mm to feet
                                break
                            else:
                                forms.alert("Error: panel_length_mm is not defined.")
                                return
                        else:
                            forms.alert(
                                "The X value must be between [" +
                                str(round(intervalle_min_mm, 2)) + " , " +
                                str(round(intervalle_max_mm, 2)) + "]"
                            )
                    except ValueError:
                        forms.alert("The value entered for X is not valid. Please enter a number.")
                else:
                    forms.alert("No value was entered for X.")
                    return

        if profile_symbol.Family.Name in ["PROFILE_PLN_124_V_WIN_UP", "PROFILE_PLN_124_V_WIN_DOWN"]:
            while True:
                # The minimum interval corresponds to the allowed minimum value
                intervalle_min_mm = right_value_mm + 31.5
                # The maximum interval takes into account the last profile and no space before the first
                intervalle_max_mm = right_value_mm + l_window_value_mm - ((num_profiles - 1) * distance_mm) - 32
                # Check if the available space is insufficient
                if intervalle_max_mm < intervalle_min_mm:
                    forms.alert(
                        "Error: The available space is insufficient for " + str(num_profiles) +
                        " profiles with a distance of " + str(distance_mm) + " mm between them.\n" +
                        "Please reduce the number of profiles or the distance between them."
                    )
                    # Allow the user to modify the values
                    user_input_num_profiles = forms.ask_for_string(
                        prompt="Enter a new number of profiles:",
                        title="Number of profiles"
                    )
                    user_input_distance_mm = forms.ask_for_string(
                        prompt="Enter a new distance between profiles (in mm):",
                        title="Distance between profiles"
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
                        break  # Exit if the user does not wish to enter new values
                user_input_x_mm = forms.ask_for_string(
                    prompt="Enter the X value (in mm) for " + profile_symbol.Family.Name +
                           " (between " + str(round(intervalle_min_mm, 2)) + " mm and " +
                           str(round(intervalle_max_mm, 2)) + " mm)",
                    title="X Value"
                )

                if user_input_x_mm:
                    try:
                        position_x_mm = float(user_input_x_mm)

                        # Strict check to include the minimum and maximum value
                        if intervalle_min_mm - 1 <= position_x_mm <= intervalle_max_mm:
                            if panel_length_mm is not None:  # Explicit check
                                half_panel_length_mm = panel_length_mm / 2
                                insertion_point_x_mm = position_x_mm - half_panel_length_mm
                                insertion_point_x_ft = insertion_point_x_mm / 304.8  # Conversion from mm to feet
                                break
                            else:
                                forms.alert("Error: panel_length_mm is not defined.")
                                return
                        else:
                            forms.alert(
                                "The X value must be between [" +
                                str(round(intervalle_min_mm, 2)) + " , " +
                                str(round(intervalle_max_mm, 2)) + "]"
                            )
                    except ValueError:
                        forms.alert("The value entered for X is not valid. Please enter a number.")
                else:
                    forms.alert("No value was entered for X.")
                    return

        if num_profiles == 1:
            with Transaction(family_doc, "Add profile to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)
                family_instance = family_doc.FamilyCreate.NewFamilyInstance(
                    insertion_point, profile_symbol, StructuralType.NonStructural
                )

                t.Commit()
        else:
            with Transaction(family_doc, "Add profiles to family") as t:
                t.Start()
                if not profile_symbol.IsActive:
                    profile_symbol.Activate()

                for i in range(num_profiles):
                    try:
                        if i > 0:
                            if profile_symbol and profile_symbol.Family.Name not in [
                                "PROFILE_PLN_124_H_WIN_LEFT",
                                "PROFILE_PLN_124_H_WIN_RIGHT",
                                "PROFILE_STR_152_H_WIN_LEFT",
                                "PROFILE_STR_152_H_WIN_RIGHT"
                            ]:
                                insertion_point_x_ft += distance_mm / 304.8
                            if profile_symbol.Family.Name in [
                                "PROFILE_PLN_124_H_WIN_LEFT",
                                "PROFILE_PLN_124_H_WIN_RIGHT",
                                "PROFILE_STR_152_H_WIN_LEFT",
                                "PROFILE_STR_152_H_WIN_RIGHT"
                            ]:
                                insertion_point_z_ft += distance_mm / 304.8

                        insertion_point = XYZ(insertion_point_x_ft, insertion_point_y_ft, insertion_point_z_ft)

                        if family_doc:
                            family_instance = family_doc.FamilyCreate.NewFamilyInstance(
                                insertion_point, profile_symbol, StructuralType.NonStructural
                            )
                        else:
                            TaskDialog.Show("Error", "Invalid family document.")
                    except Exception as e:
                        TaskDialog.Show("Error", "An error occurred: {}".format(str(e)))
                t.Commit()

        if num_profiles > 0:
            family_doc.Save()

    except Exception as e:
        forms.alert("Error adding profiles to family: {}\nTraceback: {}".format(e, traceback.format_exc()),
                    exitscript=True)

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
    """Opens the family associated with the panel in the family editor."""
    try:
        if not isinstance(panel, FamilyInstance):
            TaskDialog.Show("Error", "The selected element is not a family instance.")
            return None

        family = panel.Symbol.Family
        if not family:
            TaskDialog.Show("Error", "Unable to retrieve the family associated with the panel.")
            return None

        family_doc = revit.doc.EditFamily(family)
        return family_doc

    except Exception as e:
        TaskDialog.Show("Error", "Error opening the family: " + str(e))
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
    """Loads the edited family into the main project."""
    try:
        family_path = family_doc.PathName
        if not family_path:
            TaskDialog.Show("Error", "The family path is invalid.")
            return

        family_doc.Close(False)  # Make sure to close the document before loading it

        familyLoadOptions = FamilyLoadOptions()

        with Transaction(revit.doc, "Load Modified Family") as tx:
            tx.Start()
            if revit.doc.LoadFamily(family_path, familyLoadOptions):
                TaskDialog.Show("Success", "The family has been reloaded into the project.")
            else:
                TaskDialog.Show("Error", "Failed to load the family.")
            tx.Commit()
    except Exception as e:
        TaskDialog.Show("Error", "Error loading the family: " + str(e))


def generate_random_name(base_name):
    """Generates a new name with 4 random digits."""
    random_digits = random.randint(1000, 9999)
    return base_name + "_" + str(random_digits)


def duplicate_and_modify_family(panel):
    """Duplicates a family, applies modifications, and loads it into the project."""
    try:
        family = panel.Symbol.Family
        family_doc = revit.doc.EditFamily(family)

        original_path = family_doc.PathName
        if not original_path:
            TaskDialog.Show("Error", "The selected family does not have a valid path.")
            return None

        new_name = generate_random_name(family.Name)
        new_path = os.path.join(os.path.dirname(original_path), new_name + ".rfa")

        family_doc.SaveAs(new_path)

        modify_panel_family(family_doc)

        family_doc.Save()
        family_doc.Close(False)

        familyLoadOptions = FamilyLoadOptions()
        with Transaction(revit.doc, "Load Modified Family") as tx:
            tx.Start()
            if revit.doc.LoadFamily(new_path, familyLoadOptions):
                TaskDialog.Show("Success", "The family '" + new_name + "' has been modified and loaded successfully.")
                tx.Commit()
                return new_name
            else:
                TaskDialog.Show("Error", "Failed to load the modified family.")
                tx.RollBack()
                return None

    except Exception as e:
        TaskDialog.Show("Error", "An error occurred: " + str(e))
        return None


def update_panel_parameters(panel):
    """Met à jour les paramètres 'H_PANNEAU' et 'L_PANNEAU' en fonction de la hauteur et de la largeur du panneau."""
    try:
        # Récupérer la hauteur et la largeur
        height_param = panel.LookupParameter("Hauteur")
        width_param = panel.LookupParameter("Largeur")

        if height_param and width_param:
            height_value = height_param.AsDouble()  # La hauteur en pieds
            width_value = width_param.AsDouble()  # La largeur en pieds

            # Essayer de récupérer les paramètres "H_PANNEAU" et "L_PANNEAU"
            h_panneau_param = panel.LookupParameter("H_PANNEAU")
            l_panneau_param = panel.LookupParameter("L_PANNEAU")

            if h_panneau_param and l_panneau_param:
                # Commencer une transaction pour effectuer les modifications
                with Transaction(revit.doc, "Update H_PANNEAU and L_PANNEAU parameters") as tx:
                    tx.Start()
                    # Modifier les paramètres
                    h_panneau_param.Set(height_value)
                    l_panneau_param.Set(width_value)
                    tx.Commit()

                TaskDialog.Show("Success", "Panel parameters have been updated successfully.")
                return True
            else:
                TaskDialog.Show("Error", "The parameters 'H_PANNEAU' or 'L_PANNEAU' were not found.")
                return False
        else:
            TaskDialog.Show("Error", "The 'Height' or 'Width' parameters were not found.")
            return False

    except Exception as e:
        TaskDialog.Show("Error", "Error updating panel parameters: " + str(e))
        return False


def modify_panel_family(family_doc):
    """Applies the necessary modifications to a panel family."""
    try:
        family_manager = family_doc.FamilyManager

        # Add a custom parameter if needed
        with Transaction(family_doc, "Add or Modify Parameter") as tx:
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
                family_manager.Set(parameter, "New Value")
            tx.Commit()

    except Exception as e:
        TaskDialog.Show("Error", "Error modifying the family: " + str(e))


def update_panel_family(panel, new_family_name):
    """Updates the selected panel to use the new family."""
    try:
        new_family = next((f for f in FilteredElementCollector(revit.doc).OfClass(Family)
                           if f.Name == new_family_name), None)

        if not new_family:
            TaskDialog.Show("Error", "The new family was not found in the project.")
            return

        new_symbol = next((s for s in new_family.GetFamilySymbolIds()), None)

        with Transaction(revit.doc, "Update Panel to New Family") as tx:
            tx.Start()
            panel.Symbol = revit.doc.GetElement(new_symbol)
            tx.Commit()

        TaskDialog.Show("Success", "The panel has been updated with the new family.")

    except Exception as e:
        TaskDialog.Show("Error", "An error occurred while updating the panel: " + str(e))


def main():
    """Main entry point for adding profiles to a panel."""
    panel = select_panel()
    if not panel:
        return

    try:
        # Ask the user if they want to duplicate the family before modification
        duplicate = forms.alert("Do you want to duplicate the family before modification?", options=["Yes", "No"])

        # If the user chooses to duplicate the family, duplicate and modify it
        if duplicate == "Yes":
            new_family_name = duplicate_and_modify_family(panel)
            if new_family_name:
                # Update the panel to use the duplicated family
                update_panel_family(panel, new_family_name)
                # Mettre à jour les paramètres du panneau après la duplication
                update_panel_parameters(panel)
            else:
                forms.alert("Family duplication failed.")
                return

        # Ask the user what they want to do
        action = forms.alert(
            "What would you like to do?",
            options=["Modify Position & Dimensions", "Insert profiles"]
        )

        # Open the family in the family editor (necessary for both actions)
        family_doc = open_family_in_editor(panel)
        if family_doc is None:
            return

        if action == "Modify Position & Dimensions":
            # Retrieve existing parameters (Parameter objects and values in mm)
            result = get_existing_parameters(panel)
            if not result:
                return

            parameters, parameters_mm = result

            # Check if the dictionaries are valid
            if not parameters or not parameters_mm:
                TaskDialog.Show("Error", "Unable to retrieve parameters.")
                return

            # Display the user interface to modify the parameters
            new_values = modify_parameters_ui(parameters_mm)
            if not new_values:
                return

            # Apply the parameter changes
            apply_parameter_changes(panel, parameters, new_values)

        elif action == "Insert profiles":
            # Select the profile symbol
            profile_symbol = select_profile_symbol(family_doc)
            if profile_symbol is None:
                return

            # Ask the user how many profiles to add and the distance between them
            user_input_num_profiles = forms.ask_for_string(
                prompt="How many profiles do you want to add?",
                title="Number of Profiles",
                default="1"
            )
            num_profiles = int(user_input_num_profiles)

            if num_profiles < 1:
                forms.alert("The number of profiles must be at least 1.")
                return

            user_input_distance_mm = forms.ask_for_string(
                prompt="What is the distance between the profiles (in mm)?",
                title="Distance between Profiles",
                default="100"
            )
            distance_mm = int(user_input_distance_mm)

            if distance_mm < 0:
                forms.alert("The distance between profiles cannot be negative.")
                return

            # Call the function to add profiles
            add_profiles_to_family(family_doc, profile_symbol, num_profiles, distance_mm)

            # Load the modified family into the project
            load_family_back_to_project(family_doc)

    except ValueError:
        forms.alert("Input error: Please enter valid integers.")
    except Exception as e:
        TaskDialog.Show("Error", "Error entering values: {}".format(e))



if __name__ == "__main__":
    main()
