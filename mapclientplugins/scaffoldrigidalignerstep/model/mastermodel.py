import json
import platform

import math

from opencmiss.zinc.context import Context
from opencmiss.zinc.field import Field
from opencmiss.zinc.status import OK as ZINC_OK
from opencmiss.zinc.streamregion import StreaminformationRegion

from .scaffoldmodel import ScaffoldModel
from .datamodel import DataModel
from ..utils import maths
from ..utils import zincutils

if platform.system() == 'Windows':
    WINDOWS_OS_FLAG = True
else:
    LINUX_OS_FLAG = True


class MasterModel(object):

    def __init__(self, context, description):

        self._context = Context(context)
        self._material_module = self._context.getMaterialmodule()
        self._scaffold_region = self._context.createRegion()
        self._data_region = self._context.createRegion()
        self._scaffold_region.setName('scaffold_region')
        self._data_region.setName('data_region')

        stream_information = self._scaffold_region.createStreaminformationRegion()
        memory_resource = stream_information.createStreamresourceMemoryBuffer(description['elements3D'])
        stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH3D)
        memory_resource = stream_information.createStreamresourceMemoryBuffer(description['elements2D'])
        stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH2D)
        memory_resource = stream_information.createStreamresourceMemoryBuffer(description['elements1D'])
        stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH1D)
        memory_resource = stream_information.createStreamresourceMemoryBuffer(description['nodes'])
        stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_NODES)

        self._stream_information = stream_information
        self._data_file_name = None
        self._data_sir = None

        self._scaffold_model = ScaffoldModel(self._context, self._scaffold_region, self._material_module)
        self._data_model = DataModel(self._context, self._data_region, self._material_module)

        self._timekeeper = self._context.getTimekeepermodule().getDefaultTimekeeper()
        self._current_time = None

        self._initialise_glyph_material()
        self._initialise_tessellation(12)

        self._settings = dict(partial_z=None, partial_y=None, partial_x=None,
                              yaw=0.0, pitch=0.0, roll=0.0,
                              scaffold_up=None, data_up=None,
                              flip=None)

        self._os_specific_sep = '\\' if WINDOWS_OS_FLAG else '/'

        self._current_angle_value = [0., 0., 0.]
        self._data_coordinate_field = None
        self._scaffold_coordinate_field = None
        self._transformed_scaffold_field = None
        self._settings_change_callback = None
        self._location = None
        self._aligned_scaffold_filename = None
        self._scaffold_data_scale_ratio = None

    def get_stream(self):
        return self._stream_information

    def _initialise_glyph_material(self):
        self._glyph_module = self._context.getGlyphmodule()
        self._glyph_module.defineStandardGlyphs()

    def _initialise_tessellation(self, res):
        self._tessellationmodule = self._context.getTessellationmodule()
        self._tessellationmodule = self._tessellationmodule.getDefaultTessellation()
        self._tessellationmodule.setRefinementFactors([res])

    def initialise_time_graphics(self, time):
        self._timekeeper.setTime(time)
        # data_positions = self._get_data_positions_at_time(time)
        # for position in data_positions:
        #     print(position)

    def _get_data_positions_at_time(self, time_index):
        field_module = self._data_region.getFieldmodule()
        field_module.beginChange()
        cache = field_module.createFieldcache()
        cache.setTime(time_index)
        coordinates = field_module.findFieldByName('data_coordinates')
        node_set = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        node_iterator = node_set.createNodeiterator()
        node = node_iterator.next()
        node_positions = []
        while node.isValid():
            cache.setNode(node)
            _, position = coordinates.evaluateReal(cache, 3)
            node_positions.append(position)
            node = node_iterator.next()
        field_module.endChange()
        return node_positions

    def reset_settings(self):
        self._settings = dict(partial_z=None, partial_y=None, partial_x=None,
                              yaw=0.0, pitch=0.0, roll=0.0,
                              scaffold_up=None, data_up=None,
                              flip=None)
        self._apply_callback()
        self.initialise_scaffold(self._stream_information)

    def get_context(self):
        return self._context

    def get_scaffold_region(self):
        return self._scaffold_region

    def get_scaffold_scene(self):
        return self._scaffold_model.get_scene()

    def get_scaffold_model(self):
        return self._scaffold_model

    def get_data_region(self):
        return self._data_region

    def get_data_scene(self):
        return self._data_model.get_scene()

    def get_data_model(self):
        return self._data_model

    def get_yaw_value(self):
        return self._settings['yaw']

    def get_pitch_value(self):
        return self._settings['pitch']

    def get_roll_value(self):
        return self._settings['roll']

    def get_scaffold_up(self):
        return self._settings['scaffold_up']

    def get_data_up(self):
        return self._settings['data_up']

    def get_flip(self):
        return self._settings['flip']

    def _get_time_sequence(self):
        return self._data_model.get_time_sequence()

    def get_scaffold_to_data_ratio(self, partial=None):
        if partial:
            correction_factors = [1.0, 1.0, 1.0]
            for key in partial.keys():
                if key == 'X':
                    correction_factors[0] = partial[key]
                elif key == 'Y':
                    correction_factors[1] = partial[key]
                elif key == 'Z':
                    correction_factors[2] = partial[key]

            for factor_index in range(len(correction_factors)):
                if correction_factors[factor_index] == 0.0:
                    correction_factors[factor_index] = 1.0

            data_range_temp = self._data_model.get_scale()

            for range_index in range(len(data_range_temp)):
                if data_range_temp[range_index] == 0.0:
                    data_range_temp[range_index] = 1.0

            data_range = maths.eldiv(data_range_temp, correction_factors)
            scaffold_scale = self._scaffold_model.get_scale()
            diff = maths.eldiv(scaffold_scale, data_range)

            for temp_index in range(len(diff)):
                if diff[temp_index] == scaffold_scale[temp_index]:
                    diff[temp_index] = 1.0

        else:
            data_scale = self._data_model.get_scale()
            scaffold_scale = self._scaffold_model.get_scale()
            diff = maths.eldiv(scaffold_scale, data_scale)

        self._scaffold_data_scale_ratio = diff
        return sum(diff) / len(diff)

    def initialise_scaffold(self, stream):
        if self._scaffold_coordinate_field is not None:
            self._scaffold_coordinate_field = None
        result = self._scaffold_region.read(stream)
        if result != ZINC_OK:
            raise ValueError('Failed to read and initialise scaffold.')
        self._scaffold_coordinate_field = self._scaffold_model.get_coordinate_field()

    def initialise_ex_data(self, file_name):
        self._data_sir = self._data_region.createStreaminformationRegion()
        self._data_file_name = file_name

    def _initialise_ex_data(self):
        data_point_resource = self._data_sir.createStreamresourceFile(self._data_file_name)
        self._data_sir.setResourceDomainTypes(data_point_resource, Field.DOMAIN_TYPE_DATAPOINTS)
        result = self._data_region.read(self._data_sir)
        if result != ZINC_OK:
            raise ValueError('Failed to read point cloud')
        self._data_coordinate_field = self._data_model.get_coordinate_field()

    def load_ex_data(self):
        self._initialise_ex_data()

    def initialise_json_data(self, file_name):
        self._data_file_name = file_name

    def _initialise_jason_data(self):
        with open(self._data_file_name, 'r') as f:
            json_dict = json.loads(f.read())
        self._data_coordinate_field = self._data_model.set_data_coordinate_field_from_json_file(json_dict)

    def load_json_data(self):
        self._initialise_jason_data()

    def create_graphics(self):
        self._scaffold_model.create_scaffold_graphics()
        self._data_model.create_data_graphics()

    def set_scaffold_axis(self, axis):
        self._settings['scaffold_up'] = axis

    def set_data_axis(self, axis):
        self._settings['data_up'] = axis

    def set_time_value(self, time):
        self._current_time = time
        self._timekeeper.setTime(time)
        self._data_model.set_time(time)
        # self._data_model.change_graphics()

    def get_maximum_time_from_data(self):
        return self._data_model.get_maximum_time()

    def set_location(self, location):
        self._location = location
        path = self._os_specific_sep.join(self._location.split(self._os_specific_sep)[:-1])
        file_name = path + self._os_specific_sep + 'aligned_mesh.exf'
        self._aligned_scaffold_filename = file_name

    def load_settings(self):
        path = self._os_specific_sep.join(self._location.split(self._os_specific_sep)[:-1])
        file_name = path + self._os_specific_sep + 'rigid-settings.json'
        with open(file_name, 'r') as f:
            self._settings.update(json.loads(f.read()))

    def apply_after_load_settings(self):
        self.apply_orientation()
        self._apply_callback()

    def save_settings(self):
        path = self._os_specific_sep.join(self._location.split(self._os_specific_sep)[:-1])
        file_name = path + self._os_specific_sep + 'rigid-settings.json'
        with open(file_name, 'w') as f:
            f.write(json.dumps(self._settings, default=lambda o: o.__dict__, sort_keys=True, indent=4))

    def apply_orientation(self):
        zincutils.swap_axes(self._scaffold_coordinate_field, self._settings)
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)
        self._apply_callback()

    def rotate_scaffold(self, angle, value):
        self._update_scaffold_coordinate_field()
        next_angle_value = value
        if angle == 'yaw':
            if next_angle_value > self._current_angle_value[0]:
                angle_value = next_angle_value - self._current_angle_value[0]
            else:
                angle_value = -(self._current_angle_value[0] - next_angle_value)
            euler_angles = [angle_value, 0., 0.]
            self._current_angle_value[0] = next_angle_value
            self._settings['yaw'] = next_angle_value
        elif angle == 'pitch':
            if next_angle_value > self._current_angle_value[1]:
                angle_value = next_angle_value - self._current_angle_value[1]
            else:
                angle_value = -(self._current_angle_value[1] - next_angle_value)
            euler_angles = [0., angle_value, 0.]
            self._current_angle_value[1] = next_angle_value
            self._settings['pitch'] = next_angle_value
        else:
            if next_angle_value > self._current_angle_value[2]:
                angle_value = next_angle_value - self._current_angle_value[2]
            else:
                angle_value = -(self._current_angle_value[2] - next_angle_value)
            euler_angles = [0., 0., angle_value]
            self._current_angle_value[2] = next_angle_value
            self._settings['roll'] = next_angle_value
        angles = euler_angles
        angles = [math.radians(x) for x in angles]
        rotation = maths.eulerToRotationMatrix3(angles)
        zincutils.transform_coordinates(self._scaffold_coordinate_field, rotation)
        # self._scaffold_model.set_scaffold_graphics_post_rotate(self._transformed_scaffold_field)
        self._apply_callback()

    def _apply_callback(self):
        self._settings_change_callback()

    def set_settings_change_callback(self, settings_change_callback):
        self._settings_change_callback = settings_change_callback

    def _align_scaffold_on_data(self):
        data_minimums, data_maximums = self._data_model.get_range()
        data_centre = maths.mult(maths.add(data_minimums, data_maximums), 0.5)
        model_minimums, model_maximums = self._scaffold_model.get_range()
        model_centre = maths.mult(maths.add(model_minimums, model_maximums), 0.5)
        offset = maths.sub(data_centre, model_centre)
        zincutils.offset_scaffold(self._scaffold_coordinate_field, offset)
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)

    def _scale_scaffold_to_data(self):
        if self._scaffold_data_scale_ratio is None:
            self.get_scaffold_to_data_ratio()
        self._apply_scale()

    def _apply_scale(self):
        scale = self._scaffold_data_scale_ratio
        if scale[0] == 1.0:
            scale[0] = (scale[1] + scale[2]) / 2
        elif scale[1] == 1.0:
            scale[1] = (scale[0] + scale[2]) / 2
        elif scale[2] == 1.0:
            scale[2] = (scale[0] + scale[1]) / 2
        scale_scaffold = [1.0 / x for x in scale]
        zincutils.scale_coordinates(self._scaffold_coordinate_field, scale_scaffold)

    def _update_scaffold_coordinate_field(self):
        self._scaffold_coordinate_field = self._scaffold_model.get_coordinate_field()

    def done(self, time=False):
        self._scale_scaffold_to_data()
        self._align_scaffold_on_data()
        self.save_settings()
        self._scaffold_model.write_model(self._aligned_scaffold_filename)
        model_description = self._get_model_description(time)
        return model_description

    def _write_scaffold(self):
        resources = {}

        stream_information = self._scaffold_region.createStreaminformationRegion()
        memory_resource = stream_information.createStreamresourceMemory()
        resources['elements3D'] = memory_resource
        stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH3D)

        memory_resource = stream_information.createStreamresourceMemory()
        resources['elements2D'] = memory_resource
        stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH2D)

        memory_resource = stream_information.createStreamresourceMemory()
        resources['elements1D'] = memory_resource
        stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH1D)

        memory_resource = stream_information.createStreamresourceMemory()
        stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_NODES)
        resources['nodes'] = memory_resource
        self._scaffold_region.write(stream_information)

        buffer_contents = {}
        for key in resources:
            buffer_contents[key] = resources[key].getBuffer()[1]

        return buffer_contents

    def _write_data(self, time_series=False):
        resources = {}
        stream_information = self._data_region.createStreaminformationRegion()
        if time_series:
            time_values = self._get_time_sequence()
            for time_value in time_values:
                memory_resource = stream_information.createStreamresourceMemory()
                stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_DATAPOINTS)
                stream_information.setResourceAttributeReal(memory_resource, StreaminformationRegion.ATTRIBUTE_TIME,
                                                            time_value)
                resources[str(time_value)] = memory_resource
            self._data_region.write(stream_information)

            buffer_contents = {}
            for key in resources:
                buffer_contents[key] = resources[key].getBuffer()[1]

            return buffer_contents, time_values
        else:
            memory_resource = stream_information.createStreamresourceMemory()
            stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_DATAPOINTS)
            resources['datapoints'] = memory_resource
            self._data_region.write(stream_information)

            buffer_contents = {}
            for key in resources:
                buffer_contents[key] = resources[key].getBuffer()[1]

            return buffer_contents

    def _get_model_description(self, time=False):
        scaffold_region_description = self._write_scaffold()
        if time:
            data_region_description, time_sequence = self._write_data(time)
        else:
            time_sequence = None
            data_region_description = self._write_data()
        model_description = ModelDescription(scaffold_region_description, data_region_description, time_sequence)

        return model_description


class ModelDescription(object):

    def __init__(self, scaffold_region_description, data_region_description, time=None):
        self._scaffold_region_description = scaffold_region_description
        self._data_region_description = data_region_description
        if time:
            self._time = time
            self.data_is_temporal = True
        else:
            self._time = []
            self.data_is_temporal = False

    def get_scaffold_region_description(self):
        return self._scaffold_region_description

    def get_data_region_description(self):
        return self._data_region_description

    def get_start_time(self):
        return self._time[0]

    def get_end_time(self):
        return self._time[-1]

    def get_time_count(self):
        return len(self._time)
