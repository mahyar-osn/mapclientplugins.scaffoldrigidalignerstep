from opencmiss.zinc.context import Context
from opencmiss.zinc.field import Field
from opencmiss.zinc.status import OK as ZINC_OK

from .scaffoldmodel import ScaffoldModel
from .datamodel import DataModel


class MasterModel(object):
    def __init__(self, context):

        self._context = Context(context)
        self._material_module = self._context.getMaterialmodule()
        self._scaffold_region = self._context.createRegion()
        self._data_region = self._context.createRegion()
        self._scaffold_region.setName('scaffold_region')
        self._data_region.setName('data_region')

        self._scaffold_model = ScaffoldModel(self._context, self._scaffold_region, self._material_module)
        self._data_model = DataModel(self._context, self._data_region, self._material_module)

        self._initialise_glyph_material()
        self._initialise_tessellation(12)

        self._data_coordinate_field = None
        self._scaffold_coordinate_field = None

    def _initialise_glyph_material(self):
        self._glyph_module = self._context.getGlyphmodule()
        self._glyph_module.defineStandardGlyphs()

    def _initialise_tessellation(self, res):
        self._tessellationmodule = self._context.getTessellationmodule()
        self._tessellationmodule = self._tessellationmodule.getDefaultTessellation()
        self._tessellationmodule.setRefinementFactors([res])

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

    def initialise_scaffold(self, file_name):
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
