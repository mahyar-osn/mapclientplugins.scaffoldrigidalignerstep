from opencmiss.zinc.field import Field
from opencmiss.zinc.graphics import Graphics
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.material import Material
from opencmiss.zinc.scenecoordinatesystem import SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_TOP

from ..utils import maths


class ScaffoldModel(object):

    def __init__(self, context, region, material_module):

        self._context = context
        self._region = region
        self._material_module = material_module

        self._initialise_scene()
        self._scaffold_coordinate_field = None
        self._initialise_surface_material()

    def _create_axis_graphics(self):
        fm = self._region.getFieldmodule()
        components_count = self._scaffold_coordinate_field.getNumberOfComponents()
        axes_scale = 1.0
        min_x, max_x = self._get_node_coordinates_range()
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
            sum_line_length = fm.createFieldMeshIntegral(one, self._scaffold_coordinate_field, mesh1d)
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
        pointattr.setGlyphOffset([-5.0, 1.0, 0.])
        pointattr.setBaseSize(axes_scale)
        axes.setMaterial(self._material_module.findMaterialByName('red'))
        axes.setName('display_axes')

    def _create_surface_graphics(self):
        surface = self._scene.createGraphicsSurfaces()
        surface.setCoordinateField(self._scaffold_coordinate_field)
        surface.setRenderPolygonMode(Graphics.RENDER_POLYGON_MODE_SHADED)
        surface_material = self._material_module.findMaterialByName('trans_blue')
        surface.setMaterial(surface_material)
        surface.setName('display_surfaces')
        return surface

    def _create_line_graphics(self):
        lines = self._scene.createGraphicsLines()
        fieldmodule = self._context.getMaterialmodule()
        lines.setCoordinateField(self._scaffold_coordinate_field)
        lines.setName('display_lines')
        black = fieldmodule.findMaterialByName('white')
        lines.setMaterial(black)
        return lines

    def create_scaffold_graphics(self):
        self._create_line_graphics()
        self._create_surface_graphics()
        self._create_axis_graphics()
        self._set_window_name()

    def _get_node_coordinates_range(self):
        fm = self._scaffold_coordinate_field.getFieldmodule()
        fm.beginChange()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        min_coordinates = fm.createFieldNodesetMinimum(self._scaffold_coordinate_field, nodes)
        max_coordinates = fm.createFieldNodesetMaximum(self._scaffold_coordinate_field, nodes)
        components_count = self._scaffold_coordinate_field.getNumberOfComponents()
        cache = fm.createFieldcache()
        result, min_x = min_coordinates.evaluateReal(cache, components_count)
        result, max_x = max_coordinates.evaluateReal(cache, components_count)
        fm.endChange()
        return min_x, max_x

    def _initialise_surface_material(self):
        self._material_module = self._context.getMaterialmodule()
        self._material_module.beginChange()

        solid_blue = self._material_module.createMaterial()
        solid_blue.setName('solid_blue')
        solid_blue.setManaged(True)
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.0, 0.2, 0.6])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [0.0, 0.7, 1.0])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [0.0, 0.0, 0.0])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [0.1, 0.1, 0.1])
        solid_blue.setAttributeReal(Material.ATTRIBUTE_SHININESS, 0.2)
        trans_blue = self._material_module.createMaterial()

        trans_blue.setName('trans_blue')
        trans_blue.setManaged(True)
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.0, 0.2, 0.6])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [0.0, 0.7, 1.0])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [0.0, 0.0, 0.0])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [0.1, 0.1, 0.1])
        trans_blue.setAttributeReal(Material.ATTRIBUTE_ALPHA, 0.3)
        trans_blue.setAttributeReal(Material.ATTRIBUTE_SHININESS, 0.2)
        glyph_module = self._context.getGlyphmodule()
        glyph_module.defineStandardGlyphs()

        self._material_module.defineStandardMaterials()
        solid_tissue = self._material_module.createMaterial()
        solid_tissue.setName('heart_tissue')
        solid_tissue.setManaged(True)
        solid_tissue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.913, 0.541, 0.33])
        solid_tissue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [0.0, 0.0, 0.0])
        solid_tissue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [0.2, 0.2, 0.3])
        solid_tissue.setAttributeReal(Material.ATTRIBUTE_ALPHA, 1.0)
        solid_tissue.setAttributeReal(Material.ATTRIBUTE_SHININESS, 0.6)

        self._material_module.endChange()

    def _initialise_scene(self):
        self._scene = self._region.getScene()

    def get_scene(self):
        if self._scene is not None:
            return self._scene
        else:
            raise ValueError('Scaffold scene is not initialised.')

    def get_scale(self):
        minimums, maximums = self._get_node_coordinates_range()
        return maths.sub(minimums, maximums)

    def _getMesh(self):
        fm = self._region.getFieldmodule()
        for dimension in range(3, 0, -1):
            mesh = fm.findMeshByDimension(dimension)
            if mesh.getSize() > 0:
                return mesh
        raise ValueError('Model contains no mesh')

    def _get_model_coordinate_field(self):
        mesh = self._getMesh()
        element = mesh.createElementiterator().next()
        if not element.isValid():
            raise ValueError('Model contains no elements')
        fm = self._region.getFieldmodule()
        cache = fm.createFieldcache()
        cache.setElement(element)
        field_iter = fm.createFielditerator()
        field = field_iter.next()
        while field.isValid():
            if field.isTypeCoordinate() and (field.getNumberOfComponents() <= 3):
                if field.isDefinedAtLocation(cache):
                    return field
            field = field_iter.next()
        raise ValueError('Could not determine model coordinate field')

    def get_coordinate_field(self):
        field = self._get_model_coordinate_field()
        self._scaffold_coordinate_field = field
        return field

    def set_coordinate_field(self, field):
        if self._scaffold_coordinate_field is not None:
            self._scaffold_coordinate_field = None
        self._scaffold_coordinate_field = field

    def _set_window_name(self):
        fm = self._region.getFieldmodule()
        window_label = self._scene.createGraphicsPoints()
        window_label.setName('scaffold_window_label')
        window_label.setScenecoordinatesystem(SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_TOP)
        pointattr = window_label.getGraphicspointattributes()
        pointattr.setBaseSize([1.0, 1.0, 1.0])
        pointattr.setGlyphOffset([-0.9, 0.8, 0.0])
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
        pointattr.setLabelText(1, 'Scaffold viewer')
        tmp = fm.createFieldStringConstant(' ')
        pointattr.setLabelField(tmp)
        window_label.setMaterial(self._material_module.findMaterialByName('yellow'))

    def set_scaffold_graphics_post_rotate(self, field):
        self._scene.beginChange()
        for name in ['display_lines', 'display_surfaces']:
            graphics = self._scene.findGraphicsByName(name)
            graphics.setCoordinateField(field)
        self._scene.endChange()
        self.set_coordinate_field(field)
