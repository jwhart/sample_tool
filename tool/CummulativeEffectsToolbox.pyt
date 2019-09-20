#-------------------------------------------------------------------------------
# Name:         Sample Cummulative Effects Tools
# Purpose:      This is a sample python toolbox created to provide an example of
#               HARTerra's abilities for the purposed of the Elk Valley
#               Cummulative Effects Analysist project
#
# Author:       J. Hart & C. Langhorn - HARTerra Spatial Solutions Ltd.
#
# Created:      18-09-2019
# Copyright:    (c) HARTerra Spatial Solutions Ltd.
# Licence:
#-------------------------------------------------------------------------------

import imp
import os
import arcpy
import roaddensity
import MapSession


class Toolbox(object):
    """ Standard ArcGIS arcpy toolbox """

    def __init__(self):
        self.label = "Sample Cumulative Effects Tools"
        self.alias = "Sample Cumulative Effects Tools"

        self.tools = [CalculateRoadDensityNearStreams]

class CalculateRoadDensityNearStreams(object):
    def __init__(self):
        self.label = "Calculate Road Density"
        self.description = """ Sample road density calculation for FLNRO
                               Cumulative effects calculations"""
        self.canRunInBackground = False
        self.parameter_feature_types = {}

    def getParameterInfo(self):

        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Watershed Boundaries",
            name="in_watershed",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param0.filter.list = ["Polygon"]

        param1 = arcpy.Parameter(
            displayName="Watershed Unique ID Field",
            name="in_watershed_id",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Existing Streams",
            name="in_streams",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param2.filter.list = ["Polyline"]

        param3 = arcpy.Parameter(
            displayName="Existing Roads",
            name="in_roads",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param3.filter.list = ["Polyline"]

        param4 = arcpy.Parameter(
            displayName="Stream to Road Distance",
            name="in_distance",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input")

        # set a default value for the stream to Road distance
        param4.value = "100 meters"

        param5 = arcpy.Parameter(
            displayName="Proposed Roads",
            name="in_proposed_roads",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param5.filter.list = ["Polyline"]

        param6 = arcpy.Parameter(
            displayName="Output Folder",
            name="out_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        # set sample default values if the sample folder remains
        sample_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../sampledata/sample_input_data.gdb'))
        if os.path.exists(sample_data_dir):
            param0.value = os.path.join(sample_data_dir, "watersheds")
            param1.value = "NEW_WATERSHED_CODE"
            param2.value = os.path.join(sample_data_dir, "existing_streams")
            param3.value = os.path.join(sample_data_dir, "existing_roads")
            param5.value = os.path.join(sample_data_dir, "proposed_roads")

        params = [param0, param1, param2, param3, param4, param5, param6]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # TODO:  update the pick list for the in_watershed_id with the field names in the watershed layer after added
        if parameters[0].valueAsText:
            field_names = [i.name for i in arcpy.ListFields(parameters[0].value)]
            if field_names:
                parameters[1].filter.type = "ValueList"
                parameters[1].filter.list = field_names

        return(None)

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return(None)

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # force reloading of libraries to deal with esri caching problems
        imp.reload(roaddensity)
        imp.reload(MapSession)
        tool = roaddensity.CalculateRoadDensityNearStreamsTool(parameters, messages)
        tool.run()
        return(None)
