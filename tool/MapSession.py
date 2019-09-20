# --------------------------------
# Purpose: session object that holds stuff like workspace, feature layers, config, etc
#
# Author: Colin Dyck (colin.dyck@harterra.com)
#
# ArcGIS Version: 10.4.1
# Python Version: 2.7
#
# Created: December 22, 2017
# Copyright: (c) HARTerra 2017
# --------------------------------

import os
import sys
import arcpy
import json
import time
import pandas as pd
import math
from collections import OrderedDict

__version__ = "0.2"
__author__ = "Colin Dyck, HARTerra Spatial Solutions Ltd."


class MapSession(object):
    '''
    this class provides easy access to map layers, elements, etc in the mxd
    '''

    def __init__(self, config):
        # open config
        self.dir_name = os.path.dirname(__file__)

        self.config = config
        mxd_path = os.path.join(self.dir_name, self.config['mxd_template'])

        # keep field to index mappings.  need to have ordereddict, insert in index order
        self.fields = {}
        if 'fields' in self.config:
            for layer, fields in self.config['fields'].items():
                self.fields[layer] = OrderedDict()
                for (k, v) in zip(fields, range(len(fields))):
                    self.fields[layer][k] = v

        arcpy.AddMessage('Looking for MXD in {0}'.format(mxd_path))
        self.mxd = arcpy.mapping.MapDocument(mxd_path)

        # the layers are from the mxd
        self.data_frames = {df.name: df for df in arcpy.mapping.ListDataFrames(self.mxd)}

        # keep reference to layers in the map
        self.layers = {}

        for df_name, df in self.data_frames.items():
            self.layers[df_name] = {}
            for lyr in arcpy.mapping.ListLayers(self.mxd, data_frame=df):
                self.layers[df_name][lyr.longName] = lyr

            for tbl in arcpy.mapping.ListTableViews(self.mxd, data_frame=df):
                self.layers[df_name][tbl.name] = tbl

        self.elements = {}
        for element in arcpy.mapping.ListLayoutElements(self.mxd, "TEXT_ELEMENT"):
            self.elements[element.name] = element

    def get_map_scale(self, current_scale):
        """
        returns a proper mapscale that is rounded appropriately to the nearest
        25000, 2500, 250, 25, 10 depending on the size of the scale
        """
        scaleround = {9: 1000000, 8: 250000, 7: 100000, 6: 5000, 5: 2500, 4: 250, 3: 25, 2: 5, 1: 1}
        clen = len(str(int(current_scale)))
        mapscale = int(math.ceil(float(current_scale) / float(scaleround[clen]))) * scaleround[clen]

        return mapscale

    def set_attrs(self, obj, properties):
        """

        :param obj: object to set properties
        :param properties: dict of element properties
        :return: None
        """
        for k, v in properties.items():
            setattr(obj, k, v)

    def update_report_elements(self, element_props):
        """
        update elements in an mxd

        :param mxd: template mxd
        :param element_props: dictionary of element properties (key = element name)
        :return: None
        """
        # load up the text elements
        mxd_elements = [elm for (element_name, elm) in self.elements.items() if element_name in element_props]

        # based on the dictionary of element properties, update the mxd elements
        for element in mxd_elements:
            # print (element.name, element_props[element.name])
            self.set_attrs(element, element_props[element.name])

