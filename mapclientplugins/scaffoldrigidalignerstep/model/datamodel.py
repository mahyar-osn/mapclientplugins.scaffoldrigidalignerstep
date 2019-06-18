from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.status import OK as ZINC_OK
from opencmiss.zinc.scenecoordinatesystem import SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_TOP

from ..utils import maths


class DataModel(object):

    def __init__(self, context, region, material_module):

        self._context = context
        self._region = region
        self._material_module = material_module

        self._initialise_scene()
        self._data_coordinate_field = None

    def _initialise_scene(self):
        self._scene = self._region.getScene()

    def get_scene(self):
        if self._scene is not None:
            return self._scene
        else:
            raise ValueError('Scaffold scene is not initialised.')

    def _create_axis_graphics(self):
        fm = self._region.getFieldmodule()
        components_count = self._data_coordinate_field.getNumberOfComponents()
        axes_scale = 1.0
        min_x, max_x = self._get_data_range()
        if components_count == 1:
            max_range = max_x - min_x
        else:
            max_range = max_x[0] - min_x[0]
            for c in range(1, components_count):
                max_range = max(max_range, max_x[c] - min_x[c])
        if max_range > 0.0:
            while axes_scale*10.0 < max_range:
                axes_scale *= 10.0
            while axes_scale*0.1 > max_range:
                axes_scale *= 0.1
        mesh1d = fm.findMeshByDimension(1)
        line_count = mesh1d.getSize()
        glyph_width = None
        if line_count > 0:
            one = fm.createFieldConstant(1.0)
            sum_line_length = fm.createFieldMeshIntegral(one, self._data_coordinate_field, mesh1d)
            cache = fm.createFieldcache()
            result, total_line_length = sum_line_length.evaluateReal(cache, 1)
            glyph_width = 0.1*total_line_length/line_count
            del cache
            del sum_line_length
            del one
        if (line_count == 0) or (glyph_width == 0.0):
            max_scale = None
            if components_count == 1:
                max_scale = max_x - min_x
            else:
                first = True
                for c in range(components_count):
                    scale = max_x[c] - min_x[c]
                    if first or (scale > max_scale):
                        max_scale = scale
                        first = False
            if max_scale == 0.0:
                max_scale = 1.0
            glyph_width = 0.01*max_scale

        axes = self._scene.createGraphicsPoints()
        pointattr = axes.getGraphicspointattributes()
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_XYZ)
        pointattr.setBaseSize([axes_scale, axes_scale, axes_scale])
        pointattr.setBaseSize(axes_scale)
        axes.setMaterial(self._material_module.findMaterialByName('red'))
        axes.setName('display_axes')

    def _create_data_point_graphics(self):
        points = self._scene.createGraphicsPoints()
        points.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        points.setCoordinateField(self._data_coordinate_field)
        point_attr = points.getGraphicspointattributes()
        point_attr.setGlyphShapeType(Glyph.SHAPE_TYPE_CROSS)
        point_size = self._get_auto_point_size()
        point_attr.setBaseSize(point_size)
        points.setMaterial(self._material_module.findMaterialByName('silver'))

    def create_data_graphics(self):
        self._create_data_point_graphics()
        self._create_axis_graphics()
        self._set_window_name()

    def _get_data_coordinate_field(self):
        fm = self._region.getFieldmodule()
        data_point_set = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        data_point = data_point_set.createNodeiterator().next()
        if not data_point.isValid():
            raise ValueError('Data cloud is empty')
        cache = fm.createFieldcache()
        cache.setNode(data_point)
        field_iter = fm.createFielditerator()
        field = field_iter.next()
        while field.isValid():
            if field.isTypeCoordinate() and (field.getNumberOfComponents() <= 3):
                if field.isDefinedAtLocation(cache):
                    return field
            field = field_iter.next()
        raise ValueError('Could not determine data coordinate field')

    def get_coordinate_field(self):
        field = self._get_data_coordinate_field()
        self._data_coordinate_field = field
        return field

    def _get_data_range(self):
        fm = self._region.getFieldmodule()
        data_points = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        minimums, maximums = self._get_nodeset_minimum_maximum(data_points, self._data_coordinate_field)
        return minimums, maximums

    def _get_auto_point_size(self):
        minimums, maximums = self._get_data_range()
        data_size = maths.magnitude(maths.sub(maximums, minimums))
        return 0.005 * data_size

    @staticmethod
    def _get_nodeset_minimum_maximum(nodeset, field):
        fm = field.getFieldmodule()
        count = field.getNumberOfComponents()
        minimums_field = fm.createFieldNodesetMinimum(field, nodeset)
        maximums_field = fm.createFieldNodesetMaximum(field, nodeset)
        cache = fm.createFieldcache()
        result, minimums = minimums_field.evaluateReal(cache, count)
        if result != ZINC_OK:
            minimums = None
        result, maximums = maximums_field.evaluateReal(cache, count)
        if result != ZINC_OK:
            maximums = None
        del minimums_field
        del maximums_field
        return minimums, maximums

    def _set_window_name(self):
        fm = self._region.getFieldmodule()
        window_label = self._scene.createGraphicsPoints()
        window_label.setName('data_window_label')
        window_label.setScenecoordinatesystem(SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_TOP)
        pointattr = window_label.getGraphicspointattributes()
        pointattr.setBaseSize([1.0, 1.0, 1.0])
        pointattr.setGlyphOffset([-0.9, 0.8, 0.8])
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
        pointattr.setLabelText(1, 'Data cloud viewer')
        tmp = fm.createFieldStringConstant(' ')
        pointattr.setLabelField(tmp)
        window_label.setMaterial(self._material_module.findMaterialByName('yellow'))
