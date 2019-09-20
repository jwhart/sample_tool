#-------------------------------------------------------------------------------
# Name:         roaddensity
# Purpose:      This provides tools that perform the analysis for road density
#               in an area based unit such as a watershed that are in close
#               proximity to streams
#
# Author:       J. Hart & C. Langhorn - HARTerra Spatial Solutions Ltd.
#
# Created:      18-09-2019
# Copyright:    (c) HARTerra Spatial Solutions Ltd.
# Licence:
#-------------------------------------------------------------------------------

import os
import json
import arcpy
import pandas as pd
import MapSession

class CalculateRoadDensityNearStreamsTool(object):
    """
    A tool to perform the analysis for calculating the road density within close proximity to streams in a watershed
    prior to a proposed development and after taking into account roads that would be created through the development.
    """

    def __init__(self, parameters, messages):

        arcpy.env.overwriteOutput = True
        self.enabled = True
        self.checked = False
        self.dir = os.path.dirname(__file__)
        self.parameters = parameters
        self.messages = messages

        # load the configuration file
        config_path = os.path.join(self.dir, 'config.json')

        with open(config_path) as fp:
            self.config = json.load(fp)
            self.config = self.config['road_density']

        self.map_session = MapSession.MapSession(self.config)


    def get_param_by_name(self, name):
        """
        gets a parameter based on its name.  This will always return the first parameter it finds
        :param name: name of the parameter
        :return: Parameter or None
        """
        param = [i for i in self.parameters if i.name == name]

        if param:
            param = param[0]
        else:
            param = None

        return param

    def add_constant_field(self, table_name, field_name, field_value):
        """
        Adds a constant value to a field
        :param table_name: name of the table to add the value
        :param field_name:  field to add the constant value to.  It can not already exist
        :param field_value: the value to calculate into the field
        :return: None
        """

        arcpy.AddField_management(in_table=table_name,
                                  field_name=field_name,
                                  field_type="TEXT",
                                  field_length=len(field_value)+2)

        with arcpy.da.UpdateCursor(in_table=table_name, field_names=[field_name]) as rows:
            for row in rows:
                row[0] = field_value
                rows.updateRow(row)

    def table_to_dataframe(self, table, field_names=None, where_clause=None):
        """
        converts a table into a Pandas DataFrame object
                :param table: table
        :param field_names: specific fields to be included if None specified all will be converted
        :param where_clause:  where clause to limit the record included in the DataFrame
        :return: Panadas DataFrame object
        """

        if not field_names:
            field_names = [i.name for i in arcpy.ListFields(dataset=table)]

        values = [i for i in arcpy.da.SearchCursor(in_table=table,
                                                   field_names=field_names,
                                                   where_clause=where_clause)]

        df = pd.DataFrame(values, columns=field_names)

        return(df)

    def create_result_table(self, workspace, table_name, key_field_def):
        """
        Creates a table with the correct schema to export the results of analysis into
        :param workspace: workspace where the new table is to be created
        :param table_name: name of the table to create
        :param key_field_def: a dictionary for the field field with the properties require to create the field
        :return: returns the table
        """

        fields = [key_field_def,
                  {'field_name': 'watershed_area', 'field_type': 'DOUBLE', 'field_alias': 'Watershed Area Sqr KM'},
                  {'field_name': 'proposed_road_length', 'field_type': 'DOUBLE',
                   'field_alias': 'Proposed Road Length Near Streams KM'},
                  {'field_name': 'existing_road_length', 'field_type': 'DOUBLE',
                   'field_alias': 'Existing Road Length Near Streams KM'},
                  {'field_name': 'total_road_length', 'field_type': 'DOUBLE',
                   'field_alias': 'Total (proposed and existing) Road Length Near Streams KM'},
                  {'field_name': 'original_road_density', 'field_type': 'DOUBLE',
                   'field_alias': 'Existing Road Density Near Streams KM/KM2'},
                  {'field_name': 'future_road_density', 'field_type': 'DOUBLE',
                   'field_alias': 'Future Road Density Near Streams KM/KM2'}
                  ]

        arcpy.CreateTable_management(out_path=workspace, out_name=table_name)

        for fld in fields:
            arcpy.AddField_management(in_table=os.path.join(workspace, table_name), **fld)

        return(os.path.join(workspace, table_name))


    def get_field_definition(self, table, field_name):
        """
        creates a dictionary obejct that can be used to create a field using arcpy.AddField_management based on a field
        in an existing table

        :param table:  table that contains the field definition to use
        :param field_name: name of the field in the table
        :return: dictionary that can be used in arcpy.AddField_management
        """

        field = [i for i in arcpy.ListFields(dataset=table) if i.name == field_name]

        if field:
            field_def = {'field_name': field[0].name,
                        'field_type': field[0].type,
                        'field_alias': field[0].aliasName,
                        'field_length': field[0].length,
                        'field_precision': field[0].precision,
                        'field_scale': field[0].scale
                        }
        else:
            field_def = None

        return field_def

    def dataframe_to_table(self, result_df, table, fields):
        """
        exports a dataframe into an existing table.  Column names in the dataframe must match the table the data
        is to be exported into.

        :param result_df: Pandas dataframe with the data to export
        :param table: table to export into (must already exist)
        :param fields: fields in the order they are to be exported
        :return: None
        """

        results = result_df[fields].values

        with arcpy.da.InsertCursor(table, fields) as rows:
            for row in results:
                rows.insertRow(row)

    def run_spatial_analysis(self):
        """
        Preforms the necessary spatial analysis on the datasets to derive a spatial result to analyze and summarize.
        All spatial analysis is done using ArcGIS functionality
        :return: feature class of the roads (both existing and proposed) with watershed info within stream buffers
        """

        # get the location where the intermediary analysis results should be kept
        # this can be changed in the config file if the results are required for debugging
        workspace = self.config["workspace"]

        # find only the streams that overlap the watersheds and buffer the streams
        streams_layer = arcpy.MakeFeatureLayer_management(in_features=self.get_param_by_name("in_streams").value,
                                                          out_layer="streams_layer")

        arcpy.SelectLayerByLocation_management(in_layer=streams_layer,
                                               overlap_type="INTERSECT",
                                               select_features=self.get_param_by_name("in_watershed").value,
                                               selection_type="NEW_SELECTION",
                                               invert_spatial_relationship="FALSE")

        arcpy.Buffer_analysis(in_features=streams_layer,
                              out_feature_class=os.path.join(workspace, "stream_buffer"),
                              buffer_distance_or_field=self.get_param_by_name("in_distance").value,
                              line_side="FULL",
                              line_end_type="ROUND",
                              dissolve_option="ALL")

        # Create a roads layer that combines the existing and new roads and creates a field to distinguish the two
        # TODO:  filter the roads to those that overlap watersheds for performance if a large dataset is used
        arcpy.CopyFeatures_management(in_features=self.get_param_by_name("in_roads").value,
                                      out_feature_class=os.path.join(workspace, "original_roads"))

        self.add_constant_field(table_name=os.path.join(workspace, "original_roads"),
                                field_name="ROAD_TYPE",
                                field_value="Pre-Development")

        arcpy.CopyFeatures_management(in_features=self.get_param_by_name("in_proposed_roads").value,
                                      out_feature_class=os.path.join(workspace, "proposed_roads"))

        self.add_constant_field(table_name=os.path.join(workspace, "proposed_roads"),
                                field_name="ROAD_TYPE",
                                field_value="Proposed")

        arcpy.Merge_management(inputs=[os.path.join(workspace, "original_roads"),
                                       os.path.join(workspace, "proposed_roads")],
                               output=os.path.join(workspace, "roads_combined"))

        # intersect the watersheds, roads and stream buffer
        arcpy.Intersect_analysis(in_features=[os.path.join(workspace, "roads_combined"),
                                              os.path.join(workspace, "stream_buffer")],
                                 out_feature_class=os.path.join(workspace, "intersected_streams_roads"),
                                 join_attributes="ALL",
                                 cluster_tolerance="0.1")

        arcpy.Intersect_analysis(in_features=[os.path.join(workspace, "intersected_streams_roads"),
                                              self.get_param_by_name("in_watershed").value],
                                 out_feature_class=os.path.join(workspace, "intersected_roads_watershed"),
                                 join_attributes="ALL",
                                 cluster_tolerance="0.1")

        return(os.path.join(workspace, "intersected_roads_watershed"))

    def run_summary_analysis(self, spatial_result):
        """
        performs summaries, joins and calculations on the attribute data for each watershed
        :param spatial_result:
        :return: Pandas DataFrame with the results for exporting
        """

        key_field = self.get_param_by_name("in_watershed_id").value

        # determine the length of road in each watershed for proposed and non-proposed, and inside and outside of buffer
        roads_df = self.table_to_dataframe(table=spatial_result,
                                           field_names=[key_field, "ROAD_TYPE", "SHAPE@LENGTH"])

        road_watershed_df = roads_df.pivot_table(index=key_field,
                                                 columns="ROAD_TYPE",
                                                 values="SHAPE@LENGTH",
                                                 aggfunc="sum").fillna(0)
        road_watershed_df = road_watershed_df.reset_index()

        watersheds_df = self.table_to_dataframe(table=self.get_param_by_name("in_watershed").value,
                                                field_names=[key_field, "SHAPE@AREA"])

        watershed_areas_df = watersheds_df.groupby([key_field]).sum()
        watershed_areas_df = watershed_areas_df.reset_index()

        # merge the watershed road lengths with the areas information
        newdf = pd.merge(watershed_areas_df,
                         road_watershed_df,
                         on=key_field,
                         how='outer').fillna(0)

        # calculate all the areas, lengths and densities
        # TODO this assumes units are in meters for area and length but should be verified in the source data
        newdf['total-road-km'] = (newdf['Pre-Development'] + newdf['Proposed']) / 1000
        newdf['proposed_road_length'] = newdf['Proposed'] / 1000
        newdf['existing_road_length'] = newdf['Pre-Development'] / 1000
        newdf['total_road_length'] = newdf['existing_road_length'] + newdf['proposed_road_length']
        newdf['watershed_area'] = newdf['SHAPE@AREA'] / 1000000
        newdf['future_road_density'] = newdf['total_road_length'] / newdf['watershed_area']
        newdf['original_road_density'] = newdf['existing_road_length'] / newdf['watershed_area']

        return(newdf)

    def export_results_table(self, dataframe, output_gdb):
        """
        Exports the resulting data to a table in a workspace
        :param dataframe: dataframe to be exported
        :param output_gdb: output geodatabse location
        :return: exported table
        """

        key_field = self.get_param_by_name("in_watershed_id").value

        # export data to table to join
        key_field_definition = self.get_field_definition(table=self.get_param_by_name("in_watershed").value,
                                                         field_name=key_field)

        self.create_result_table(workspace=output_gdb,
                                 table_name="Results",
                                 key_field_def=key_field_definition)

        fields = [key_field, 'watershed_area', 'existing_road_length', 'proposed_road_length',
                  'total_road_length', 'original_road_density', 'future_road_density']

        self.dataframe_to_table(result_df=dataframe, table=os.path.join(output_gdb, "Results"), fields=fields)

        return(os.path.join(output_gdb, "Results"))

    def simple_report(self, result_df):
        """
        finds the areas with the biggest differences between existing and future road densities and adds to
        a table on the map in descending order
        """

        # find the items with the biggest difference from exiting to proposed and add to map as report
        result_df['change_in_density'] = abs(result_df['original_road_density'] - result_df['future_road_density'])
        result_df = result_df.sort(['change_in_density'], ascending=False)


        key_field = str(self.get_param_by_name("in_watershed_id").value)

        values = [tuple(x) for x in result_df[[key_field, 'original_road_density',
                                               'future_road_density', 'change_in_density']].values][:20]

        if len(values) > 0:
            items = [('<BOL>{:<27s} {:8s} {:8s} {:8s}</BOL>'.format(key_field, "Exiting", "Future", "Change"))]
            for row in values:
                items.append('{:.27} {:.6f} {:.6f} {:.6f}'.format(row[0], row[1], row[2], row[3]))
            output_table = "\n".join(items)
        else:
            output_table = "Unable to find assessment data"

        return(output_table)


    def generate_pdf_mxd(self, result_layer, result_df):
        """
        generates a mxd and pdf showing the results
        :param result_layer: the layer showing results data
        :return: None
        """

        # replace the datasources on the newly analyzed layers
        workspace, dataset = os.path.split(result_layer)
        self.map_session.layers["Existing"]["Road Density"].replaceDataSource(workspace_path=workspace,
                                                                              workspace_type="FILEGDB_WORKSPACE",
                                                                              dataset_name=dataset)

        self.map_session.layers["Proposed"]["Road Density"].replaceDataSource(workspace_path=workspace,
                                                                              workspace_type="FILEGDB_WORKSPACE",
                                                                              dataset_name=dataset)

        workspace, dataset = os.path.split(str(self.get_param_by_name("in_proposed_roads").value))

        self.map_session.layers["Proposed"]["Proposed Roads"].replaceDataSource(workspace_path=workspace,
                                                                                workspace_type="FILEGDB_WORKSPACE",
                                                                                dataset_name=dataset)

        # set extents on dataframes to the result_layer
        ext = self.map_session.layers["Existing"]["Road Density"].getExtent()
        self.map_session.data_frames['Existing'].extent = ext
        self.map_session.data_frames['Proposed'].extent = ext

        # set scale on dataframes to a proper scale
        scale = self.map_session.get_map_scale(self.map_session.data_frames['Existing'].scale)
        self.map_session.data_frames['Existing'].scale = scale
        self.map_session.data_frames['Proposed'].scale = scale

        # update map elements with
        distance = self.get_param_by_name("in_distance").value
        stmt = """Density is based on roads within {0} of a stream centerline""".format(distance)
        self.map_session.elements['subTitleText'].text = stmt

        # create and update report into mxd and pdf
        output_table = self.simple_report(result_df=result_df)
        self.map_session.elements['tableTextArea'].text = output_table

        # save pdf and mxd
        out_path = os.path.join(str(self.get_param_by_name("out_folder").value), 'result.pdf')
        arcpy.mapping.ExportToPDF(self.map_session.mxd, out_path, image_quality=self.config['image_quality'])
        self.map_session.mxd.saveACopy(os.path.join(str(self.get_param_by_name("out_folder").value), 'result.mxd'))

    def run(self):
        """
        Runs the tool
        :return: None
        """

        #TODO refactor so the key_field is part of the object to reduce redunancy
        key_field = self.get_param_by_name("in_watershed_id").value

        # create output gdb if it doesn't exist...
        output_gdb = os.path.join(str(self.get_param_by_name("out_folder").value), "results.gdb")

        if not arcpy.Exists(output_gdb):
            arcpy.CreateFileGDB_management(self.get_param_by_name("out_folder").value, "results.gdb")

        # perform the spatial analysis
        spatial_result = self.run_spatial_analysis()

        # summarize the data by watershed
        result = self.run_summary_analysis(spatial_result)

        # export the result table
        result_table = self.export_results_table(dataframe=result, output_gdb=output_gdb)

        # join the results to the watersheds
        arcpy.CopyFeatures_management(in_features=self.get_param_by_name("in_watershed").value,
                                      out_feature_class=os.path.join(output_gdb, "result_polygons"))

        arcpy.JoinField_management(in_data=os.path.join(output_gdb, "result_polygons"),
                                   in_field=key_field,
                                   join_table=result_table,
                                   join_field=key_field)

        # create the mxd and pdf file
        self.generate_pdf_mxd(result_layer=os.path.join(output_gdb, "result_polygons"), result_df=result)


