# -*- coding: utf-8 -*-
"""
Title: Curtain Wall Creation
Description:
This script creates curtain walls in Revit by following a series of guided steps.
It allows you to choose the panel type, level, creation mode, height, and vertical and horizontal spacing. Then, it transforms the selected curves into straight lines if necessary and creates curtain walls according to the given specifications.

How to use:
1. Choose the panel type for the curtain walls.
2. Select the level where the curtain walls will be created.
3. Choose the creation mode (the entire edge of the floor or a single edge of the side face).
4. Specify the height of the curtain walls.
5. Specify the vertical and horizontal spacing of the grids.
6. Select the edges where you want to create the curtain walls.


Version: v1
Author: Wiem Ben Araar, Amira Dridi
"""

__title__ = 'Create the Wall(s)'

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
import clr

clr.AddReference('System')

from pyrevit import forms

# Initialisation
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

def get_curtain_wall_types():
    """Obtenir une liste de tous les types de murs rideaux disponibles."""
    collector = FilteredElementCollector(doc).OfClass(WallType).ToElements()
    curtain_wall_types = {}
    for wt in collector:
        if wt.Kind == WallKind.Curtain:
            try:
                name = wt.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
                curtain_wall_types[name] = wt.Id
            except Exception as e:
                curtain_wall_types["Nom Inconnu"] = wt.Id
                print("Error getting type name : {}".format(e))

    return curtain_wall_types

def get_floor_edges(floor):
    """Obtenir les courbes représentant les bords d'un sol."""
    options = Options()
    geometry_element = floor.get_Geometry(options)
    edges = []
    for geom_obj in geometry_element:
        if isinstance(geom_obj, Solid):
            for face in geom_obj.Faces:
                for edge_loop in face.EdgeLoops:
                    for edge in edge_loop:
                        curve = edge.AsCurve()
                        if curve:
                            edges.append(curve)
    return edges

def convert_curve_to_line(curve):
    """Convertir une courbe en ligne droite si possible."""
    if isinstance(curve, Arc):
        return Line.CreateBound(curve.GetEndPoint(0), curve.GetEndPoint(1))
    elif isinstance(curve, Line):
        return curve
    return None

def process_edge(curve, curtain_wall_type_id, level_id, height_meters, vertical_spacing_meters, horizontal_spacing_meters):
    """Créer un mur rideau sur une courbe donnée."""
    try:
        base_curve = convert_curve_to_line(curve)
        if base_curve:
            if isinstance(base_curve, Line):
                if base_curve.Length >= 0.01:  # Vérifier que la longueur de la ligne est suffisante
                    Wall.Create(doc, base_curve, curtain_wall_type_id, level_id, height_meters, 0, False, True)
                    # Appliquer l'espacement vertical et horizontal ici si nécessaire
                else:
                    print("The line length is too short to create a wall. Ignore this line.")
            else:
                print("The converted curve is not a valid line.")
        else:
            print("The curve is invalid or cannot be converted to a line.")
    except Exception as e:
        print("Error while processing edge : {}".format(e))

class VerticalFaceSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return isinstance(element, Floor)  # Limiter la sélection aux éléments de type Floor

    def AllowReference(self, refer, point):
        face = doc.GetElement(refer).GetGeometryObjectFromReference(refer)
        normal = face.ComputeNormal(UV(0.5, 0.5))
        return abs(normal.Z) < 0.0001  # Filtrer pour ne sélectionner que les faces verticales

def select_vertical_face(uidoc, floor):
    """Permettre à l'utilisateur de sélectionner une face latérale spécifique d'un sol."""
    try:
        face_filter = VerticalFaceSelectionFilter()
        picked_ref = uidoc.Selection.PickObject(ObjectType.Face, face_filter,
                                                "Select a side face of the floor")
        face = doc.GetElement(picked_ref).GetGeometryObjectFromReference(picked_ref)
        return face
    except Exception as e:
        TaskDialog.Show("Error", "Error selecting side face : {}".format(str(e)))
        return None

def get_edges_from_face(face):
    """Obtenir les bordures de la face, qui sont supposées être rectangulaires."""
    edges = []
    if isinstance(face, PlanarFace):
        edge_loops = face.EdgeLoops
        for edge_loop in edge_loops:
            for edge in edge_loop:
                curve = edge.AsCurve()
                if curve:
                    edges.append(curve)
    return edges

def get_level():
    """Obtenir une liste des niveaux disponibles et en sélectionner un."""
    levels = FilteredElementCollector(doc).OfClass(Level).ToElements()
    level_dict = {level.Name: level.Id for level in levels}
    if not level_dict:
        raise Exception("No levels available in this project.")

    selected_level_name = forms.ask_for_one_item(
        list(level_dict.keys()),
        default=next(iter(level_dict.keys())),
        prompt="Select a level:",
        title="Basic level"
    )

    if not selected_level_name:
        raise Exception("No level has been selected.")

    return doc.GetElement(level_dict[selected_level_name])

try:
    curtain_wall_types = get_curtain_wall_types()

    if not curtain_wall_types:
        raise Exception("No type of curtain wall is available in this project.")

    selected_name = forms.ask_for_one_item(
        list(curtain_wall_types.keys()),
        default=next(iter(curtain_wall_types.keys())),
        prompt="Select a curtain wall type:",
        title="Curtain Wall Type"
    )

    if not selected_name:
        raise Exception("No curtain wall type has been selected.")

    curtain_wall_type_id = curtain_wall_types[selected_name]
    curtain_wall_type = doc.GetElement(curtain_wall_type_id)

    # Sélection dynamique du niveau
    level = get_level()
    level_id = level.Id

    # Démarrer une transaction avant de commencer les modifications
    t = Transaction(doc, "Create Curtain Wall")
    t.Start()

    # Demander le mode de création
    mode = forms.ask_for_one_item(
        ["All edge of the floor", "Only one edge of the side face"],
        prompt="Choose the mode of creation of curtain walls:",
        title="Creation Mode"
    )

    if mode not in ["All edge of the floor", "Only one edge of the side face"]:
        raise Exception("Invalid creation mode.")

    # Facteur de conversion de pieds en mètres
    FEET_TO_METERS = 3.28084

    # Demander la hauteur à l'utilisateur (en mètres)
    user_input_height = forms.ask_for_string(
        prompt="Please enter the height of the curtain walls (in meters):",
        title="Curtain Wall Height"
    )

    if not user_input_height:
        raise Exception("No height was specified.")

    try:
        height_meters = float(user_input_height)
        if height_meters <= 0:
            raise ValueError("Height must be a positive number.")
        # Convertir la hauteur de metres en pieds (1 metre = 3.28084 pieds)
        height_feet = height_meters * 3.28084
    except ValueError:
        raise Exception("The specified height is invalid.")

    # Demander l'espacement vertical à l'utilisateur (en mètres)
    user_input_vertical_spacing = forms.ask_for_string(
        prompt="Please enter the vertical grid spacing (in meters):",
        title="Vertical Grid Spacing"
    )

    if not user_input_vertical_spacing:
        raise Exception("No vertical spacing was specified.")

    try:
        vertical_spacing_feet = float(user_input_vertical_spacing)
        if vertical_spacing_feet <= 0:
            raise ValueError("Spacing must be a positive number.")
        if vertical_spacing_feet >7.3152:
            raise ValueError("Vertical spacing must not exceed 7.3152 meters.")
        # Convertir l'espacement vertical de pieds en mètres
        vertical_spacing_meters = vertical_spacing_feet * FEET_TO_METERS
    except ValueError as e:
        raise Exception("The specified vertical spacing is invalid or exceeds the limit: 7.3152 meters.")

    # Demander l'espacement horizontal à l'utilisateur (en mètres)
    user_input_horizontal_spacing = forms.ask_for_string(
        prompt="Please enter the horizontal grid spacing (in meters):",
        title="Horizontal Grid Spacing"
    )

    if not user_input_horizontal_spacing:
        raise Exception("No horizontal spacing was specified.")

    try:
        horizontal_spacing_feet = float(user_input_horizontal_spacing)
        if horizontal_spacing_feet <= 0:
            raise ValueError("Spacing must be a positive number.")
        if horizontal_spacing_feet > 4.2672:
            raise ValueError("Horizontal spacing must not exceed 4.2672 meters.")
        # Convertir l'espacement horizontal de pieds en mètres
        horizontal_spacing_meters = horizontal_spacing_feet * FEET_TO_METERS
    except ValueError as e:
        raise Exception("The specified horizontal spacing is invalid or exceeds the limit: 4.2672 meters.")

    if mode == "The entire edge of the ground":
        selection = uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Select a floor to create a curtain wall around the entire edge")
        floor = doc.GetElement(picked_ref.ElementId)

        edges = get_floor_edges(floor)
        for curve in edges:
            process_edge(curve, curtain_wall_type_id, level_id, height_meters, vertical_spacing_meters, horizontal_spacing_meters)

    elif mode == "Only one edge of the side face":
        selection = uidoc.Selection
        picked_ref = selection.PickObject(ObjectType.Element, "Select a floor to create a curtain wall on a single edge")
        floor = doc.GetElement(picked_ref.ElementId)
        face = select_vertical_face(uidoc, floor)

        if face:
            edge_curves = get_edges_from_face(face)

            if edge_curves:
                selected_edge_curve = edge_curves[0]  # Sélectionner directement la première courbe disponible

                # Créer le mur rideau ici
                wall = Wall.Create(doc, selected_edge_curve, curtain_wall_type_id, level_id, height_feet, 0, False,
                                   True)

                # Modifier les parametres d'espacement du mur rideau
                curtain_wall_type = wall.WallType
                parameters = curtain_wall_type.Parameters
                vertical_spacing_param = None
                horizontal_spacing_param = None

                for param in parameters:
                    if param.Definition.Name == "Espacement" and vertical_spacing_param is None:
                        vertical_spacing_param = param
                    elif param.Definition.Name == "Espacement" and horizontal_spacing_param is None:
                        horizontal_spacing_param = param

                if vertical_spacing_param is None or horizontal_spacing_param is None:
                    raise Exception("Specific grid settings not found.")

                vertical_spacing_param.Set(vertical_spacing_meters)
                horizontal_spacing_param.Set(horizontal_spacing_meters)

            else:
                raise Exception("No valid curve found on the selected face.")

    t.Commit()

except Exception as e:
    t.RollBack()
    TaskDialog.Show("Error", "An error has occurred : {}".format(str(e)))