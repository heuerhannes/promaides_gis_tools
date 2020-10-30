"""

"""
from __future__ import absolute_import

# system modules
import math

# 3rd party modules
import numpy as np

# QGIS modules
from qgis.core import QgsPointXY

# promaides modules
from .utils import deprecated
from .version import *

#general
from datetime import datetime



class RasterWriter(object):

    def __init__(self, xll, yll, dc, dr, nc, nr, angle=0.0, nodata=None):
        self.xll = xll
        self.yll = yll
        self.dc = dc
        self.dr = dr
        self.nc = nc
        self.nr = nr
        self.angle = angle
        self.cosa = math.cos(angle)
        self.sina = math.sin(angle)
        self.prm = None
        self.index = 0

        self.nodata = Raster.NODATA_VALUES.copy()
        if nodata:
            self.nodata.update(nodata)

    def num_cells(self):
        return self.nc * self.nr

    def cell_center(self, idx):

        r_idx, c_idx = self.cell(idx)

        dc = (0.5 + c_idx) * self.dc
        dr = (0.5 + r_idx) * self.dr

        return QgsPointXY(self.xll + (dc * self.cosa - dr * self.sina),
                          self.yll + (dr * self.cosa + dc * self.sina))

    def cell(self, idx):

        r_idx = int(math.floor(idx / self.nc))
        c_idx = int(idx % self.nc)

        if r_idx < 0 or r_idx >= self.nr:
            raise IndexError('raster row index out of range: %d, num. rows = %d' % (r_idx, self.nr))
        if c_idx < 0 or c_idx >= self.nc:
            raise IndexError('raster column index out of range: %d, num. columns = %d' % (c_idx, self.nc))

        return r_idx, c_idx

    def idx(self, cell):
        return cell[0] * self.nc + cell[1]

    def open(self, filename, input_layers):
        if self.prm is not None:
            raise OSError('raster file already open')

        angle = self.angle / math.pi * 180.0

        self.prm = open(filename, 'w+')

        self.prm.write('########################################################################\n')
        self.prm.write('# This file was automatically generated by ProMaiDes 2D-Floodplain '
                             'Export-QGIS-Plugin Version {version_1} \n'.format(version_1=VERSION))
        # date and time output
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        self.prm.write('# Generated at {dt_string_1} '.format(dt_string_1=dt_string))
        self.prm.write('from a temporary layer\n')
        self.prm.write('#  based on height raster (DEM) {}  \n'.format(input_layers['elev']['layer'].name()))
        if input_layers['roughn']['layer'] != None:
            self.prm.write('#  based on roughness raster {}  \n'.format(input_layers['roughn']['layer'].name()))
        if input_layers['init']['layer'] != None:
            self.prm.write('#  based on initial condition raster {}  \n'.format(input_layers['init']['layer'].name()))


        self.prm.write('# Comments are marked with #\n')
        self.prm.write('#\n')
        self.prm.write('# Explanation of data (in one line):\n')
        self.prm.write('#  Element-nr. [-]\n')
        self.prm.write('#  Geodetic height [m]\n')
        self.prm.write('#  Material id [-] (must match one of the ids in the materials file)\n')
        self.prm.write('#  Initial water depth [m]\n')
        self.prm.write('#  Boundary condition flag [bool] (true: bc is applied; false no bc is applied)\n')
        self.prm.write('#  Stationary boundary condition [bool] (true: bc is stationary; false: bc is instationary)\n')
        self.prm.write('#  Boundary condition value [-] (if stationary, unit is according to "boundary type", '
                       'otherwise id of hydrograph)\n')
        self.prm.write('#  Boundary type [-] (whether the boundary condition value unit is "point" [m3/s], '
                       '"area" [m3/(s m2)])\n')
        self.prm.write('#\n')
        self.prm.write('# Use in .ilm-file (just copy, delete the leading "#", set file(s)):\n')

        self.prm.write('#  Set a floodplain model between !$BEGINDESCRIPTION and !$ENDDESCRIPTION\n')
        self.prm.write('#  In global section add 1 to !NOFFP = x+1 # Number of floodplain models\n')
        self.prm.write('#   !$BEGINFPMODEL =  Index_(starts by 0) "NAME" \n')
        self.prm.write('#    !GENERAL = <SET>\n')
        self.prm.write('#   \t$NX          = %d\n' % self.nc)
        self.prm.write('#   \t$NY          = %d\n' % self.nr)
        self.prm.write('#   \t$LOWLEFTX    = %f\n' % self.xll)
        self.prm.write('#   \t$LOWLEFTY    = %f\n' % self.yll)
        self.prm.write('#   \t$ELEMWIDTH_X = %f\n' % self.dc)
        self.prm.write('#   \t$ELEMWIDTH_Y = %f\n' % self.dr)
        self.prm.write('#   \t$NOINFOVALUE = %f\n' % self.nodata['elev'])
        self.prm.write('#   \t$ANGLE       = %f\n' % -angle)  # positive rotation is defined opposite in ProMaIDEs
        self.prm.write('#    </SET>\n')
        self.prm.write('#    !FLOODPLAINFILE = "./PATH2FILE/FILE_NAME.txt"\n')
        self.prm.write('#    !LIMITS = <SET>	\n')
        self.prm.write('#       $RTOL = 1e-9 '
                           '#$RTOL = Defines relative tolerances [optional, standard value = 1.0e-9]\n')
        self.prm.write('#       $ATOL = 1e-5 # $ATOL = defines absolute tolerances '
                           '[optional, standard value = 1.0e-5\n')
        self.prm.write('#       $WET  = 0.001   #wet and dry parameter [optional, standard value = 1e-2] \n')
        self.prm.write('#     </SET>	\n')

        self.prm.write('#  !$ENDFPMODEL  \n')
        self.prm.write('########################################################################\n')
        self.prm.write('\n')
        self.prm.write('!BEGIN\n')

    def write_cell(self, data, cellproperties):
        # fill empty slots with NaN values
        for key, value in list(self.nodata.items()):
            if key not in data:
                data[key] = value

        data['bc'] = str(data['bc']).lower()
        bc_stat = data['bc_stat']
        data['bc_stat'] = str(bc_stat).lower()
        data['roughn'] = int(data['roughn'])

        boundaryenabled = cellproperties[0]
        boundarystationary = cellproperties[1]
        boundaryvalue = cellproperties[2]
        boundarytype = cellproperties[3]

        self.prm.write('{i:d}\t{elev:f}\t{roughn:d}\t{init:f}\t{bcstatus}\t{bcstatus2}\t{BCdata}\t{bcstatus3}\n'
                       .format(i=self.index, bcstatus=boundaryenabled, bcstatus2=boundarystationary,BCdata=boundaryvalue,bcstatus3=boundarytype, **data))

        self.index += 1

    def close(self):
        if self.prm is None:
            raise OSError('raster file not open')

        self.prm.write('!END\n')
        self.prm.close()
        self.prm = None
        self.index = 0

# simpleWriter was written for the export of raster files for the DAM module
class SimpleRasterWriter(object):

    def __init__(self, xll, yll, nr, nc, drc, item, nodata=None):
        self.xll = xll
        self.yll = yll
        self.nr = nr
        self.nc = nc
        self.drc = drc
        self.item = item
        self.nodata = nodata


        self.prm = None
        self.index = 0

    def num_cells(self):
        return self.nr * self.nc

    def cell_values(self, idx, data_names=('ecn',)):
        if set(data_names) - Raster.DATA_NAMES:
            raise ValueError('Unexpected data name. Supported names are: ' + ', '.join(Raster.DATA_NAMES))

        if idx >= self.num_cells():
            raise IndexError('given cell index {} is out of bounds'.format(idx))

        if isinstance(idx, int):
            r_idx, c_idx = self.cell(idx)
        else:
            r_idx, c_idx = idx

        return tuple(self.data[list(data_names)][r_idx, c_idx])

    def set_cell_value(self, idx, value, data_name='ecn'):
        """

        :param idx:
        :param value:
        :param data_name:
        :return:

        Examples
        --------

        >>> raster = Raster(0.0, 0.0, 1.0, 1.0, 100, 100)
        >>> raster.set_cell_value(720, 10.0, data_name='elev')
        >>> elev, = raster.cell_values(720, data_names=('elev',))
        >>> elev
        10.0
        """
        if data_name not in Raster.DATA_NAMES:
            raise ValueError(
                'Unexpected data name "{}". Supported names are: '.format(data_name) + ', '.join(Raster.DATA_NAMES))

        if idx >= self.num_cells():
            raise IndexError('given cell index {} is out of bounds'.format(idx))

        r_idx, c_idx = self.cell(idx)

        self.data[data_name][r_idx, c_idx] = value

# RS: Definition of cell centre for every cell in x and y coordinates
    def cell_center(self, idx):

        from qgis.core import QgsPoint

        r_idx, c_idx = self.cell(idx)

        dx = (0.5 + c_idx) * self.drc  # RS: this dx is including half a cell size to account for the centre location
        dy = (0.5 + r_idx) * self.drc  # RS: this dx is including half a cell size to account for the centre location

        return QgsPoint(self.xll + dx, self.yll + dy)

    def cell(self, idx):

        r_idx = int(math.floor(idx / self.nc))
        c_idx = int(idx % self.nc)

        if r_idx < 0 or r_idx >= self.nr:
            raise IndexError('raster row index out of range: %d, num. rows = %d' % (r_idx, self.nr))
        if c_idx < 0 or c_idx >= self.nc:
            raise IndexError('raster column index out of range: %d, num. columns = %d' % (c_idx, self.nc))

        return r_idx, c_idx

    def idx(self, cell):
        return cell[0] * self.nc + cell[1]

    def open(self, filename, input_layers, data_name):
        if self.prm is not None:
            raise OSError('raster file already open')

        filename_typeref = filename + '.' + data_name
        typeref_short = data_name[0:3]
        print(typeref_short, 'typeref_short')
        self.prm = open(filename_typeref, 'w+')
        self.prm.write('########################################################################\n')
        self.prm.write('# This file was generated by ProMaiDes QGIS Plugin - DAM Raster Export'
                             'Export-QGIS-Plugin Version {version_1} \n'.format(version_1=VERSION))
        # date and time output
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        self.prm.write('# Generated at {dt_string_1} '.format(dt_string_1=dt_string))
        self.prm.write('from a temporary layer\n')
        self.prm.write('#  based on DAM Exposure data raster {}  \n'.format(input_layers[typeref_short]['layer'].name()))

        self.prm.write('# Comments are marked with #\n')
        self.prm.write('#\n')
        self.prm.write('# Explanation of data (in one line):\n')
        self.prm.write('#  !name           : Name of this file\n')
        self.prm.write('#  !type           : Type of land use (e.g. pop_density, agriculture, etc.)\n')
        self.prm.write('#  !ncols          : Number of columns in raster (X-axis)\n')
        self.prm.write('#  !nrows          : Number of rows in raster (Y-axis)\n')
        self.prm.write('#  !xllcorner      : x-value of lower left corner of raster\n')
        self.prm.write('#  !yllcorner      : y-value of lower left corner of raster\n')
        self.prm.write('#  !cellsize       : Squared edge side length [m]\n')
        self.prm.write('#  !NODATA_value   : Value for an element with no information \n')
        self.prm.write('#\n')
        self.prm.write('#_____________________________\n')

        self.prm.write('   !$BEGIN_RASTERINFO\n')
        self.prm.write('   \t!name        = %s\n' % self.item.text())
        self.prm.write('   \t!type        = %s\n' % data_name)
        self.prm.write('   \t!ncols       = %d\n' % self.nc)
        self.prm.write('   \t!nrows       = %d\n' % self.nr)
        self.prm.write('   \t!xllcorner   = %f\n' % self.xll)
        self.prm.write('   \t!yllcorner   = %f\n' % self.yll)
        self.prm.write('   \t!cellsize    = %f\n' % self.drc)
        self.prm.write('   \t!NODATA_value= %f\n' % self.nodata['ecn'])
        self.prm.write('  !$END_RASTERINFO\n')

        self.prm.write('\n')
        self.prm.write('!BEGIN_CHARAC\n')


    #write element with integers
    def write_cell(self, data, raster_type):
        # The raster is written beginning with the lower left corner
        # fill empty slots with NaN values
        for key, value in list(self.nodata.items()):
            if key == raster_type:
                if key not in data:
                    data[key] = value
                if (self.index+1) % self.nc == 0:  # jump to next row once every value per column is written
                    self.prm.write(('{' + raster_type + ':.0f}\n').format(**data))
                else:
                    self.prm.write(('{' + raster_type + ':.0f}\t').format(**data))
        self.index += 1
    #write element data with float
    def write_cell_float(self, data, raster_type):
        # The raster is written beginning with the lower left corner
        # fill empty slots with NaN values
        for key, value in list(self.nodata.items()):
            if key == raster_type:
                if key not in data:
                    data[key] = value
                if (self.index+1) % self.nc == 0:  # jump to next row once every value per column is written
                    self.prm.write(('{' + raster_type + ':.f}\n').format(**data))
                else:
                    self.prm.write(('{' + raster_type + ':.f}\t').format(**data))
        self.index += 1

    def close(self):
        if self.prm is None:
            raise OSError('raster file not open')

        self.prm.write('!END\n')
        self.prm.close()
        self.prm = None
        self.index = 0

if __name__ == '__main__':
    import doctest
    doctest.testmod()
