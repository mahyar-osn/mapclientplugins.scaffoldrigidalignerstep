import random

from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.status import OK as ZINC_OK
from opencmiss.zinc.scenecoordinatesystem import SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_TOP
from opencmiss.utils.zinc import create_node, create_finite_element_field, AbstractNodeDataObject

from ..utils import maths


class DataCreator(AbstractNodeDataObject):

    def __init__(self, coordinates, time_sequence):
        super(DataCreator, self).__init__(['coordinates'], time_sequence, ['coordinates'])
        self._coordinates = coordinates

    def coordinates(self):
        return self._coordinates


class DataModel(object):

    def __init__(self, context, region, material_module):

        self._context = context
        self._region = region
        self._material_module = material_module
        self._data_coordinate_field = create_finite_element_field(self._region, field_name='coordinates')

        self._initialise_scene()
        self._timekeeper = self._scene.getTimekeepermodule().getDefaultTimekeeper()
        self._current_time = None
        self._maximum_time = None
        self._time_sequence = None

    def _initialise_scene(self):
        self._scene = self._region.getScene()

    def get_scene(self):
        if self._scene is not None:
            return self._scene
        else:
            raise ValueError('Scaffold scene is not initialised.')

    def set_time(self, time):
        self._current_time = time
        self._timekeeper.setTime(time)

    def _set_maximum_time(self):
        self._timekeeper.setMaximumTime(self._maximum_time)

    def get_maximum_time(self):
        return self._maximum_time

    def get_time_sequence(self):
        return self._time_sequence

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
        points.setName('display_points')

    def create_data_graphics(self):
        self._create_data_point_graphics()
        self._create_axis_graphics()
        self._set_window_name()

    def change_graphics(self):
        self._scene.beginChange()
        graphics = self._scene.findGraphicsByName('display_points')
        graphics.setCoordinateField(self._data_coordinate_field)
        self._scene.endChange()

    def set_data_coordinate_field_from_json_file(self, json_description):
        frames = json_description['AnnotatedFrames']
        number_of_frames = len(frames)
        self._maximum_time = number_of_frames
        self._set_maximum_time()
        self._time_sequence = [int(x) for x in range(number_of_frames)]

        sorted_len_frames = self._get_minimum_number_of_datapoints_from_jason_dict(frames)
        smallest_sample_length = len(frames[sorted_len_frames[0]])
        frame_numbers = list(frames.keys())

        all_positions = list()
        for time in range(len(self._time_sequence)):
            groups_and_positions = frames[frame_numbers[time]]
            positions = [x[1] for x in groups_and_positions]
            positions = random.sample(positions, smallest_sample_length)
            all_positions.append(positions)

        positions_timewise = list()
        for position in range(len(all_positions[0])):
            temp = list()
            for time in range(len(all_positions)):
                temp.append(all_positions[time][position])
            positions_timewise.append(temp)

        field_module = self._region.getFieldmodule()
        field_module.beginChange()
        node_set = field_module.findNodesetByName('datapoints')
        field_cache = field_module.createFieldcache()

        for index in range(len(positions_timewise)):
            locations = positions_timewise[index]
            location = locations[0]
            data_creator = DataCreator(location, self._time_sequence)
            identifier = create_node(field_module, data_creator, node_set_name='datapoints',
                                     time=self._time_sequence[0])
            node = node_set.findNodeByIdentifier(identifier)
            field_cache.setNode(node)
            assert len(self._time_sequence) == len(locations)
            for next_index in range(1, number_of_frames):
                location = locations[next_index]
                if location == [0., 0., 0.]:
                    print(next_index)
                time = self._time_sequence[next_index]
                field_cache.setTime(time)
                self._data_coordinate_field.assignReal(field_cache, location)

        field_module.endChange()
        self._data_coordinate_field.setName('data_coordinates')
        return self._data_coordinate_field

    @staticmethod
    def _get_minimum_number_of_datapoints_from_jason_dict(frames):
        return sorted(frames, key=lambda key: len(frames[key]))

    def _create_node_at_location(self, location, cache, domain_type=Field.DOMAIN_TYPE_DATAPOINTS, node_id=-1):
        fieldmodule = self._region.getFieldmodule()
        fieldmodule.beginChange()
        nodeset = fieldmodule.findNodesetByFieldDomainType(domain_type)
        template = nodeset.createNodetemplate()
        template.defineField(self._data_coordinate_field)
        node = nodeset.createNode(node_id, template)
        field_cache = cache
        field_cache.setNode(node)
        self._data_coordinate_field.assignReal(field_cache, location)
        fieldmodule.endChange()
        return node

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

    def get_range(self):
        return self._get_data_range()

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

    def get_scale(self):
        minimums, maximums = self._get_data_range()
        return maths.sub(minimums, maximums)

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
