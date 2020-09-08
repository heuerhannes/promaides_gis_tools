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

    def __init__(self, xll, yll, dc, dr, nc, nr,boundarytype, angle=0.0, nodata=None):
        self.xll = xll
        self.yll = yll
        self.dc = dc
        self.dr = dr
        self.nc = nc
        self.nr = nr
        self.boundarytype = boundarytype
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
        if input_layers['BCdata']['layer'] != None:
            self.prm.write('#  based on boundary condition raster {}  \n'.format(input_layers['BCdata']['layer'].name()))

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

    def write_cell(self, data):
        # fill empty slots with NaN values
        for key, value in list(self.nodata.items()):
            if key not in data:
                data[key] = value

        data['bc'] = str(data['bc']).lower()
        bc_stat = data['bc_stat']
        data['bc_stat'] = str(bc_stat).lower()
        data['BCdata'] = float(data['BCdata'])
        data['roughn'] = int(data['roughn'])

        if data['BCdata']:
            boundaryenabled = "true"
            boundarystationary = "true"
        else:
            boundaryenabled= "false"
            boundarystationary = "true"

        self.prm.write('{i:d}\t{elev:f}\t{roughn:d}\t{init:f}\t{bcstatus}\t{bcstatus2}\t{BCdata}\t{j}\n'
                       .format(i=self.index,j=self.boundarytype, bcstatus=boundaryenabled, bcstatus2=boundarystationary, **data))

        self.index += 1

    def close(self):
        if self.prm is None:
            raise OSError('raster file not open')

        self.prm.write('!END\n')
        self.prm.close()
        self.prm = None
        self.index = 0


@deprecated('Use RasterWriter instead!')
class Raster(object):

    DATA_NAMES = {'elev', 'roughn', 'init', 'bc', 'bc_stat', 'BCdata'}
    NODATA_VALUES = dict(elev=-9999.0, roughn=1, init=0.0, bc=False , bc_stat=True, bc_val=0)

    def __init__(self, xll, yll, dc, dr, nc, nr, angle=0.0, nodata=None):

        self.xll = xll
        self.yll = yll
        self.dc = dc
        self.dr = dr
        self.nc = nc
        self.nr = nr
        self.angle = angle
        self._cosa = math.cos(angle)
        self._sina = math.sin(angle)

        self.data = np.zeros(
            (nr, nc),
            dtype=[('elev', 'f4'), ('roughn', 'i4'), ('init', 'f4'), ('bc', bool), ('bc_stat', bool), ('BCdata', 'f4')]
        )

        self.nodata = Raster.NODATA_VALUES.copy()
        if nodata:
            self.nodata.update(nodata)

        # set default values to no data values
        for key, value in list(self.nodata.items()):
            self.data[key] = value

    def num_cells(self):
        return self.nc * self.nr

    def cell_values(self, idx, data_names=('elev',)):
        if set(data_names) - Raster.DATA_NAMES:
            raise ValueError('Unexpected data name. Supported names are: ' + ', '.join(Raster.DATA_NAMES))

        if idx >= self.num_cells():
            raise IndexError('given cell index {} is out of bounds'.format(idx))

        if isinstance(idx, int):
            r_idx, c_idx = self.cell(idx)
        else:
            r_idx, c_idx = idx

        return tuple(self.data[list(data_names)][r_idx, c_idx])

    def set_cell_value(self, idx, value, data_name='elev'):
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

    def cell_center(self, idx):

        from qgis.core import QgsPoint

        r_idx, c_idx = self.cell(idx)

        dc = (0.5 + c_idx) * self.dc
        dr = (0.5 + r_idx) * self.dr

        return QgsPoint(self.xll + (dc * self._cosa - dr * self._sina),
                        self.yll + (dr * self._cosa + dc * self._sina))

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

    def save_as_prm(self, filename):

        prm = open(filename, 'w+')

        prm.write('# This file was automatically generated by ProMaiDes DEM Export QGIS Plugin\n\n')
        prm.write('# The following metadata can be copied to a Promaides .ilm\n')
        prm.write('# file to use this raster with Promaides.\n')

        prm.write('#!GENERAL = <SET>\n')
        prm.write('#\t$NX          = %d\n' % self.nc)
        prm.write('#\t$NY          = %d\n' % self.nr)
        prm.write('#\t$LOWLEFTX    = %f\n' % self.xll)
        prm.write('#\t$LOWLEFTY    = %f\n' % self.yll)
        prm.write('#\t$ELEMWIDTH_X = %f\n' % self.dc)
        prm.write('#\t$ELEMWIDTH_Y = %f\n' % self.dr)
        prm.write('#\t$NOINFOVALUE = %f\n' % self.nodata['elev'])

        # CAUTION! The positive rotation direction is defined opposite in ProMaIDEs
        angle = self.angle / math.pi * 180.0
        prm.write('#\t$ANGLE       = %f\n' % -angle)

        prm.write('#</SET>\n\n')

        prm.write('# --- Value description --- #\n')
        prm.write('# element-nr. [-]\n')
        prm.write('# geod. height [m]\n')
        prm.write('# material id [-] (must match one of the ids in the materials file)\n')
        prm.write('# initial waterlevel [m]\n')
        prm.write('# boundary condition [bool] (whether the cell is a boundary)\n')
        prm.write('# stationary boundary condition [bool] (whether the boundary is stationary or instationary)\n')
        prm.write(
            '# boundary condition value [-] (if stationary, unit is according to "boundary type", otherwise hydrograph id)\n')
        prm.write(
            '# boundary type [-] (whether the boundary condition value unit is "point" [m3/s], "area" [m3/(s m2)], "length" [m], or "waterlevel" [m])\n\n')

        prm.write('!BEGIN\n')
        for i in range(self.num_cells()):
            values = dict(list(zip(Raster.DATA_NAMES, self.cell_values(i, Raster.DATA_NAMES))))

            if data['BCdata']:
                boundaryenabled = "true"
                boundarystationary = "true"
            else:
                boundaryenabled = "false"
                boundarystationary = "true"

            values['bc'] = str(values['bc']).lower()
            bc_stat = values['bc_stat']
            values['bc_stat'] = str(bc_stat).lower()
            data['BCdata'] = float(data['BCdata'])
            prm.write('{i:d}\t{elev:f}\t{roughn:d}\t{init:f}\t{bcstatus}\t{bcstatus2}\t{BCdata}\t{j}\n'
                           .format(i=self.index, j=self.boundarytype, bcstatus=boundaryenabled,
                                   bcstatus2=boundarystationary, **data))
        prm.write('!END\n')
        prm.close()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
