from __future__ import unicode_literals
from __future__ import absolute_import

# QGIS modules
from qgis.core import *
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import *
from qgis.PyQt import uic
from qgis.gui import QgsMessageBar

# promaides modules
from .interpolate import RasterInterpolator
from .environment import get_ui_path

#general
from datetime import datetime
from .version import *

UI_PATH = get_ui_path('ui_cin_2promaides_connector.ui')

# This plugin exports the observations point file for the HYD-module of ProMaIdes from a point shape file;
# A name field (string) is required within the point layer
class PluginDialog(QDialog):

    def __init__(self, iface, parent=None, flags=Qt.WindowFlags()):
        QDialog.__init__(self, parent, flags)
        uic.loadUi(UI_PATH, self)
        self.iface = iface
        self.input_layer = None

        self.iface.currentLayerChanged.connect(self.setInputLayer)
        #  self.listWidget.currentRowChanged.connect(self.updateRasterPropertiesGroup)
        self.addButton_2source.clicked.connect(self.add2sourcelist)
        self.addButton_2sink.clicked.connect(self.add2sinklist)
        self.addButton_2source_sink_pair.clicked.connect(self.merge2pair)
        self.removeButton.clicked.connect(self.remove_pair)

        self.browse_button.clicked.connect(self.onBrowseButtonClicked)
        self.button_box.rejected.connect(self.reject)

        self.comboBox_conTypes.addItem('physical')
        self.comboBox_conTypes.addItem('cyber')
        self.comboBox_conTypes.addItem('geographic')
        self.comboBox_conTypes.addItem('logical')

        self.setInputLayer(self.iface.activeLayer())

        self.list_of_pairs = []  # multi-dimensional List for the source sink pairs
        
        self.HelpButton.clicked.connect(self.Help)

    def __del__(self):
        self.iface.currentLayerChanged.disconnect(self.setInputLayer)

    def onBrowseButtonClicked(self):
        current_filename = self.filename_edit.text()
        new_filename, __ = QFileDialog.getSaveFileName(self.iface.mainWindow(), 'CIN Connector Export', current_filename)
        if new_filename != '':
            self.filename_edit.setText(new_filename)
            self.filename_edit.editingFinished.emit()
            
    def Help(self):
        webbrowser.open("https://promaides.myjetbrains.com/youtrack/articles/PMDP-A-64/DAM-CIN---Connector-Export---Manual")

    def add2sourcelist(self):
        for item in self.listWidget_input.selectedItems():
            if self.comboBox_source.findText(item.text(), Qt.MatchExactly | Qt.MatchRecursive) == -1:
                self.comboBox_source.addItem(item.text())

    def add2sinklist(self):
        for item in self.listWidget_input.selectedItems():
            if self.comboBox_sink.findText(item.text(), Qt.MatchExactly | Qt.MatchRecursive) == -1:
                self.comboBox_sink.addItem(item.text())

    def merge2pair(self):
        pair_index = self.listWidget_pairs.count()
        str_source = self.comboBox_source.currentText()
        str_sink = self.comboBox_sink.currentText()
        str_con_type = self.comboBox_conTypes.currentText()

        if str_source != str_sink:
            verification = True
        else:
            verification = False
            self.iface.messageBar().pushMessage("Info", "The incoming (first) CI-structure is the same as the outgoing CI-structure (second)")
        
        #Check if there is already a connection            
        if verification:
            mergeItems = "Source: "+ self.comboBox_source.currentText() + "; Sink: " + self.comboBox_sink.currentText() + ";"
            
            if not self.listWidget_pairs.findItems(mergeItems, Qt.MatchExactly | Qt.MatchRecursive):
                self.list_of_pairs.append([str_source, str_sink, pair_index, str_con_type])
                self.listWidget_pairs.addItem(mergeItems) 
            else:
                self.iface.messageBar().pushMessage("Info", "Connection already exists")

    def remove_pair(self):
        del self.list_of_pairs[self.listWidget_pairs.currentRow()]
        self.listWidget_pairs.takeItem(self.listWidget_pairs.currentRow())

    def setInputLayer(self, layer):
        self.list_of_input = []
        if not layer:
            self.input_layer = None
            self.input_label.setText('<i>No layer selected.<br>'
                                     'Please select a merged CI point layer.</i>')
        else:
            layer_name = layer.name()

            if layer.type() == QgsMapLayer.VectorLayer:

                if layer.geometryType() == QgsWkbTypes.PointGeometry:
                    self.input_layer = layer
                    field_names = ["point_name", "point_id", "sec_level", "sec_id", "final_flag",
                                         "boundary_value"]
                    for field_name in field_names:

                        field_index = layer.fields().indexFromName(field_name)

                        if field_index == -1:
                            self.input_label.setText('<i>Selected layer "{}" is missing attributes.<br>'
                                                     'Please add the field {} or rename an existing field.</i>'
                                                     .format(layer_name, field_name))

                    for feature in layer.getFeatures():
                        self.listWidget_input.addItem(feature["point_name"])
                        self.list_of_input.append([feature["point_name"], feature["point_id"]])

                        if layer.featureCount():
                            self.input_label.setText('<i>Input layer is "{}" with {} feature(s). </i>'
                                                     .format(layer_name, layer.featureCount()))

                else:
                    self.input_layer = None
                    self.input_label.setText('<i>Selected layer "{}" is not a point layer.<br>'
                                             'Please select a polypoint layer.</i>'
                                             .format(layer_name))
            else:
                self.input_layer = None
                self.input_label.setText('<i>Selected layer "{}" is not a vector layer.<br>'
                                         'Please select a polypoint layer.</i>'
                                         .format(layer_name))
        #  Critical Infrastructure Objects in Input Layers
        #  self.listWidget_input.currentRowChanged.connect(self.updateRasterPropertiesGroup) #  listWidget_input
        self.addButton_2source.setEnabled(True)#  addButton_2source
        self.addButton_2sink.setEnabled(True)  # addButton_2sink
        self.addButton_2source_sink_pair.setEnabled(True)

        self.updateButtonBox()

    def updateButtonBox(self):
        if self.input_layer: #and self.raster_layer:
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

class CINConnectorExport(object):

    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self.cancel = False
        self.act = QAction('CIN Connector Export', iface.mainWindow())
        self.act.triggered.connect(self.execDialog)

    def initGui(self, menu=None):
        if menu is not None:
            menu.addAction(self.act)
        else:
            self.iface.addToolBarIcon(self.act)

    def unload(self, menu=None):
        if menu is None:
            menu.removeAction(self.act)
        else:
            self.iface.removeToolBarIcon(self.act)

    def execDialog(self): #  add tooltips
        """
        """
        self.dialog = PluginDialog(self.iface, self.iface.mainWindow())
        self.dialog.button_box.accepted.connect(self.execTool)
        self.dialog.accepted.connect(self.execTool)
        self.dialog.rejected.connect(self.quitDialog)
        self.dialog.setModal(False)
        self.act.setEnabled(False)
        self.dialog.show()

    def scheduleAbort(self):
        self.cancel = True

    def quitDialog(self):
        # self.dialog = None
        # self.act.setEnabled(True)
        # self.cancel = True

        self.act.setEnabled(True)
        self.cancel = False
        self.dialog.close()

    def execTool(self):
        source_name_write = []
        sink_name_write = []
        source_id_write = []
        sink_id_write = []

        filename = self.dialog.filename_edit.text()

        if not filename:
            self.iface.messageBar().pushCritical(
                'CIN Connector Export',
                'No output filename given!'
            )
            self.quitDialog()
            return

        progress = QProgressDialog('Exporting connectors ...', 'Abort', 0, len(self.dialog.list_of_pairs), self.iface.mainWindow())
        progress.setWindowTitle('CIN Connector Export')
        progress.canceled.connect(self.scheduleAbort)
        progress.show()

        # iterate over polyline features
        with open(filename, 'w+') as connector_file:

            connector_file.write('########################################################################\n')
            connector_file.write('# This file was automatically generated by "Connector Export for ProMaiDes CIN module'
                                        'Export-QGIS-Plugin Version {version_1} \n'.format(version_1=VERSION))
            #date and time output
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            connector_file.write('# Generated at {dt_string_1} '.format(dt_string_1=dt_string))
            connector_file.write('from layer {filename_1} \n'.format(filename_1=self.dialog.input_layer.sourceName()))
            connector_file.write('# Comments are marked with #\n')
            connector_file.write('# There are three CI-elements:\n')
            connector_file.write('# 1. Points; as in this file)\n')
            connector_file.write('# 2. Connectors; linking Points with each other, multiple connectors in '
                                        'several directions are possible) \n')
            connector_file.write('# 3. Polygons; mostly final elements\n')
            connector_file.write('#\n')
            connector_file.write('# Explanation of data:\n')
            connector_file.write('#  Start the CI-connectors with !BEGIN and end it with !END; in between are:\n')
            connector_file.write('#  NumberOfPoints\n')
            connector_file.write('#  id(unique) id_from_CI_element type(point_polygon)  id_to_CI_element type(point_polygon)')
            connector_file.write('#\n')
            connector_file.write('########################################################################\n')
            connector_file.write('!BEGIN\n')
            connector_file.write('{number} #Number of CI Connectors \n'.format(number=len(self.dialog.list_of_pairs)))

            for x1 in range(len(self.dialog.list_of_pairs)):
                pair_index = x1
                for x2 in range(len(self.dialog.list_of_input)):

                    if self.dialog.list_of_pairs[x1][0] == self.dialog.list_of_input[x2][0]:
                        source_name_write = self.dialog.list_of_input[x2][0]
                        source_id_write = self.dialog.list_of_input[x2][1]
                    if self.dialog.list_of_pairs[x1][1] == self.dialog.list_of_input[x2][0]:
                        sink_name_write = self.dialog.list_of_input[x2][0]
                        sink_id_write = self.dialog.list_of_input[x2][1]

                connector_file.write('  {a} {b} point {c} point # Source: {d}; Sink: {e}\n'.format
                                         (a=pair_index, b=source_id_write, c=sink_id_write, d=str(source_name_write),
                                          e=str(sink_name_write), ))

                if self.cancel:
                    break
            connector_file.write('!END\n\n')
            connector_file.close()

        #if not self.cancel:
        self.iface.messageBar().pushInfo(
            'CIN Connector Export',
            'Export finished successfully!'
           )

        progress.close()
        self.quitDialog()
        return

