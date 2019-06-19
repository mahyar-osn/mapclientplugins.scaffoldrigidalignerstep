import json
import platform

from opencmiss.zinc.context import Context
from opencmiss.zinc.field import Field
from opencmiss.zinc.status import OK as ZINC_OK

from .scaffoldmodel import ScaffoldModel
from .datamodel import DataModel
from ..utils import maths
from ..utils import zincutils


class MasterModel(object):
    def __init__(self, context, scaffold_path):

        self._context = Context(context)
        self._material_module = self._context.getMaterialmodule()
        self._scaffold_region = self._context.createRegion()
        self._data_region = self._context.createRegion()
        self._scaffold_region.setName('scaffold_region')
        self._data_region.setName('data_region')
        self._scaffold_path = scaffold_path

        self._scaffold_model = ScaffoldModel(self._context, self._scaffold_region, self._material_module)
        self._data_model = DataModel(self._context, self._data_region, self._material_module)

        self._initialise_glyph_material()
        self._initialise_tessellation(12)

        self._settings = dict(yaw=0.0, pitch=0.0, roll=0.0, scaffold_up=None, data_up=None, flip=None)

        self._data_coordinate_field = None
        self._scaffold_coordinate_field = None
        self._transformed_scaffold_field = None
        self._settings_change_callback = None
        self._location = None
        self._aligned_scaffold_filename = None

    def _initialise_glyph_material(self):
        self._glyph_module = self._context.getGlyphmodule()
        self._glyph_module.defineStandardGlyphs()

    def _initialise_tessellation(self, res):
        self._tessellationmodule = self._context.getTessellationmodule()
        self._tessellationmodule = self._tessellationmodule.getDefaultTessellation()
        self._tessellationmodule.setRefinementFactors([res])

    def reset_settings(self):
        self._settings = dict(yaw=0.0, pitch=0.0, roll=0.0, scaffold_up=None, data_up=None, flip=None)
        self._apply_callback()
        self.initialise_scaffold(self._scaffold_path)

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

    def get_scaffold_to_data_ratio(self):
        diff = maths.eldiv(self._scaffold_model.get_scale(), self._data_model.get_scale())
        return sum(diff) / len(diff)

    def initialise_scaffold(self, file_name):
        if self._scaffold_coordinate_field is not None:
            self._scaffold_coordinate_field = None
        result = self._scaffold_region.readFile(file_name)
        if result != ZINC_OK:
            raise ValueError('Failed to read and initialise scaffold.')
        self._scaffold_coordinate_field = self._scaffold_model.get_coordinate_field()

    def initialise_data(self, file_name):
        sir = self._data_region.createStreaminformationRegion()
        data_point_resource = sir.createStreamresourceFile(file_name)
        sir.setResourceDomainTypes(data_point_resource, Field.DOMAIN_TYPE_DATAPOINTS)
        result = self._data_region.read(sir)
        if result != ZINC_OK:
            raise ValueError('Failed to read point cloud')
        self._data_coordinate_field = self._data_model.get_coordinate_field()

    def create_graphics(self):
        self._scaffold_model.create_scaffold_graphics()
        self._data_model.create_data_graphics()

    def set_scaffold_axis(self, axis):
        self._settings['scaffold_up'] = axis

    def set_data_axis(self, axis):
        self._settings['data_up'] = axis

    def set_location(self, location):
        self._location = location
        if platform.system() == 'Windows':
            path = '\\'.join(self._location.split('\\')[:-1])
            file_name = path + '\\aligned_mesh.exf'
        else:
            path = '/'.join(self._location.split('/')[:-1])
            file_name = path + '/aligned_mesh.exf'
        self._aligned_scaffold_filename = file_name

    def load_settings(self):
        if platform.system() == 'Windows':
            path = '\\'.join(self._location.split('\\')[:-1])
            file_name = path + '\\rigid-settings.json'
        else:
            path = '/'.join(self._location.split('/')[:-1])
            file_name = path + '/rigid-settings.json'
        with open(file_name, 'r') as f:
            self._settings.update(json.loads(f.read()))
        self.apply_orientation()
        self._apply_callback()

    def save_settings(self):
        if platform.system() == 'Windows':
            path = '\\'.join(self._location.split('\\')[:-1])
            file_name = path + '\\rigid-settings.json'
        else:
            path = '/'.join(self._location.split('/')[:-1])
            file_name = path + '/rigid-settings.json'
        with open(file_name, 'w') as f:
            f.write(json.dumps(self._settings, default=lambda o: o.__dict__, sort_keys=True, indent=4))

    def apply_orientation(self):
        zincutils.swap_axes(self._scaffold_coordinate_field, self._settings)
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)

    def rotate_scaffold(self, angle, value):
        self._update_scaffold_coordinate_field()

        self._settings[angle] = value
        euler_angles = [self._settings['yaw'], self._settings['pitch'], self._settings['roll']]
        angles = [x * 0.1 for x in euler_angles]
        rotation_matrix = maths.eulerToRotationMatrix3(angles)
        rotation_matrix_flattened = [columns for rows in rotation_matrix for columns in rows]
        fm = self._scaffold_region.getFieldmodule()
        fm.beginChange()
        rotation_field = fm.createFieldConstant(rotation_matrix_flattened)
        if self._transformed_scaffold_field is None:
            self._transformed_scaffold_field = fm.createFieldMatrixMultiply(3, rotation_field,
                                                                            self._scaffold_coordinate_field)
        else:
            self._transformed_scaffold_field = None
            self._transformed_scaffold_field = fm.createFieldMatrixMultiply(3, rotation_field,
                                                                            self._scaffold_coordinate_field)
        fm.endChange()
        self._scaffold_model.set_scaffold_graphics_post_rotate(self._transformed_scaffold_field)
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

    def _update_scaffold_coordinate_field(self):
        self._scaffold_coordinate_field = self._scaffold_model.get_coordinate_field()

    def done(self):
        self._align_scaffold_on_data()
        self.save_settings()
        self._scaffold_model.write_model(self._aligned_scaffold_filename)
