from opencmiss.zinc.node import Node
from opencmiss.zinc.field import Field
from opencmiss.zinc.status import OK as ZINC_OK

from .maths import elmult, add, matrixvectormult


def remove_zero_valued_nodes(source_field, time=0.0):
    ncomp = source_field.getNumberOfComponents()
    source_fe_field = source_field.castFiniteElement()
    if not (source_fe_field.isValid()):
        print('zinc.copy_nonzero_parameters: fields must be finite element type')
        return False
    success = True
    fm = source_fe_field.getFieldmodule()
    fm.beginChange()
    cache = fm.createFieldcache()
    cache.setTime(time)
    nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
    node_template = nodes.createNodetemplate()
    node_iter = nodes.createNodeiterator()
    node = node_iter.next()
    while node.isValid():
        node_template.defineFieldFromNode(source_fe_field, node)
        cache.setNode(node)
        result, values = source_fe_field.getNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, ncomp)
        if result != ZINC_OK:
            success = False
        if values == [0., 0., 0.]:
            result = nodes.destroyNode(node)
            if result != ZINC_OK:
                success = False
            print("ZERO NODE VALUES DELETED")
        node = node_iter.next()
    fm.endChange()
    return success


def copy_nodal_parameters(source_field, target_field, time=0.0):
    ncomp = source_field.getNumberOfComponents()
    if target_field.getNumberOfComponents() != ncomp:
        print('zinc.copyNodalParameters: fields must have same number of components')
        return False
    source_fe_field = source_field.castFiniteElement()
    target_fe_field = target_field.castFiniteElement()
    if not (source_fe_field.isValid() and target_fe_field.isValid()):
        print('zinc.copyNodalParameters: fields must be finite element type')
        return False
    success = True
    fm = source_fe_field.getFieldmodule()
    fm.beginChange()
    cache = fm.createFieldcache()
    cache.setTime(time)
    nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    node_template = nodes.createNodetemplate()
    node_iter = nodes.createNodeiterator()
    node = node_iter.next()
    while node.isValid():
        node_template.defineFieldFromNode(source_fe_field, node)
        cache.setNode(node)
        for derivative in [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D2_DS1DS2,
                           Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3, Node.VALUE_LABEL_D2_DS2DS3, Node.VALUE_LABEL_D3_DS1DS2DS3]:
            versions = node_template.getValueNumberOfVersions(source_fe_field, -1, derivative)
            for v in range(1, versions + 1):
                result, values = source_fe_field.getNodeParameters(cache, -1, derivative, v, ncomp)
                if result != ZINC_OK:
                    success = False
                else:
                    result = target_fe_field.setNodeParameters(cache, -1, derivative, v, values)
                    if result != ZINC_OK:
                        success = False
        node = node_iter.next()
    fm.endChange()
    if not success:
        print('zinc.copyNodalParameters: failed to get/set some values')
    return success


def swap_axes(source_field, axes=None):
    axis_x = 0
    axis_y = 1
    axis_z = 2
    number_of_components = source_field.getNumberOfComponents()
    field = source_field.castFiniteElement()
    if not (field.isValid()):
        print('field must be finite element type')
        return False
    success = True
    fm = field.getFieldmodule()
    fm.beginChange()
    cache = fm.createFieldcache()
    nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    node_template = nodes.createNodetemplate()
    node_iter = nodes.createNodeiterator()
    node = node_iter.next()
    while node.isValid():
        node_template.defineFieldFromNode(field, node)
        cache.setNode(node)
        for derivative in [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2,
                           Node.VALUE_LABEL_D2_DS1DS2,
                           Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3, Node.VALUE_LABEL_D2_DS2DS3,
                           Node.VALUE_LABEL_D3_DS1DS2DS3]:
            versions = node_template.getValueNumberOfVersions(field, -1, derivative)
            for v in range(1, versions + 1):
                result, values = field.getNodeParameters(cache, -1, derivative, v, number_of_components)
                if result != ZINC_OK:
                    success = False
                else:
                    if axes['scaffold_up'] == 'Z' and axes['data_up'] == 'Y':
                        new_values = [values[axis_x], values[axis_z], values[axis_y]]
                        _ = field.setNodeParameters(cache, -1, derivative, v, new_values)
                        new_values = [new_values[0], new_values[1], -new_values[2]]
                        result = field.setNodeParameters(cache, -1, derivative, v, new_values)
                    elif axes['scaffold_up'] == 'Z' and axes['data_up'] == 'X':
                        new_values = [values[axis_z], values[axis_y], values[axis_x]]
                        _ = field.setNodeParameters(cache, -1, derivative, v, new_values)
                        new_values = [new_values[0], new_values[1], -new_values[2]]
                        result = field.setNodeParameters(cache, -1, derivative, v, new_values)
                    elif axes['scaffold_up'] == 'Z' and axes['data_up'] == 'Z':
                        pass
                    elif axes['scaffold_up'] == 'Y' and axes['data_up'] == 'Y':
                        pass
                    elif axes['scaffold_up'] == 'X' and axes['data_up'] == 'X':
                        pass
                    else:
                        Warning('The scaffold {} up and data {} up axes combination is not yet implemented.'.format(
                            axes['scaffold_up'], axes['data_up']))
                        success = False
                    if result != ZINC_OK:
                        success = False
        node = node_iter.next()
    fm.endChange()
    if not success:
        print('failed to get/set some values')
    return success


def transform_coordinates(field, rotation):
    number_of_components = field.getNumberOfComponents()
    if (number_of_components != 2) and (number_of_components != 3):
        print('zincutils.transformCoordinates: field has invalid number of components')
        return False
    if len(rotation) != number_of_components:
        print('zincutils.transformCoordinates: invalid matrix number of columns or offset size')
        return False
    if field.getCoordinateSystemType() != Field.COORDINATE_SYSTEM_TYPE_RECTANGULAR_CARTESIAN:
        print('zincutils.transformCoordinates: field is not rectangular cartesian')
        return False
    fe_field = field.castFiniteElement()
    if not fe_field.isValid():
        print('zincutils.transformCoordinates: field is not finite element field type')
        return False
    success = True
    fm = field.getFieldmodule()
    fm.beginChange()
    cache = fm.createFieldcache()
    nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    node_template = nodes.createNodetemplate()
    node_iter = nodes.createNodeiterator()
    node = node_iter.next()
    while node.isValid():
        node_template.defineFieldFromNode(fe_field, node)
        cache.setNode(node)
        for derivative in [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2,
                           Node.VALUE_LABEL_D2_DS1DS2, Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3,
                           Node.VALUE_LABEL_D2_DS2DS3, Node.VALUE_LABEL_D3_DS1DS2DS3]:
            versions = node_template.getValueNumberOfVersions(fe_field, -1, derivative)
            for v in range(1, versions + 1):
                result, values = fe_field.getNodeParameters(cache, -1, derivative, v, number_of_components)
                if result != ZINC_OK:
                    success = False
                else:
                    new_values = matrixvectormult(rotation, values)
                    result = fe_field.setNodeParameters(cache, -1, derivative, v, new_values)
                    if result != ZINC_OK:
                        success = False
        node = node_iter.next()
    fm.endChange()
    if not success:
        print('zincutils.transformCoordinates: failed to get/set some values')
    return success


def scale_coordinates(field, scale):
    number_of_components = field.getNumberOfComponents()
    if (number_of_components != 2) and (number_of_components != 3):
        print('zincutils.scale_coordinates: field has invalid number of components')
        return False
    if len(scale) != number_of_components:
        print('zincutils.scale_coordinates: invalid matrix number of columns or offset size')
        return False
    if field.getCoordinateSystemType() != Field.COORDINATE_SYSTEM_TYPE_RECTANGULAR_CARTESIAN:
        print('zincutils.transformCoordinates: field is not rectangular cartesian')
        return False
    fe_field = field.castFiniteElement()
    if not fe_field.isValid():
        print('zincutils.scale_coordinates: field is not finite element field type')
        return False
    success = True
    fm = field.getFieldmodule()
    fm.beginChange()
    cache = fm.createFieldcache()
    nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    node_template = nodes.createNodetemplate()
    node_iter = nodes.createNodeiterator()
    node = node_iter.next()
    while node.isValid():
        node_template.defineFieldFromNode(fe_field, node)
        cache.setNode(node)
        for derivative in [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2,
                           Node.VALUE_LABEL_D2_DS1DS2, Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3,
                           Node.VALUE_LABEL_D2_DS2DS3, Node.VALUE_LABEL_D3_DS1DS2DS3]:
            versions = node_template.getValueNumberOfVersions(fe_field, -1, derivative)
            for v in range(1, versions + 1):
                result, values = fe_field.getNodeParameters(cache, -1, derivative, v, number_of_components)
                if result != ZINC_OK:
                    success = False
                else:
                    new_values = elmult(scale, values)
                    result = fe_field.setNodeParameters(cache, -1, derivative, v, new_values)
                    if result != ZINC_OK:
                        success = False
        node = node_iter.next()
    fm.endChange()
    if not success:
        print('zincutils.transformCoordinates: failed to get/set some values')
    return success


def offset_scaffold(field, offset):
    number_of_components = field.getNumberOfComponents()
    if (number_of_components != 2) and (number_of_components != 3):
        print('zincutils.offset_scaffold: field has invalid number of components')
        return False
    if len(offset) != number_of_components:
        print('zincutils.offset_scaffold: invalid matrix number of columns or offset size')
        return False
    if field.getCoordinateSystemType() != Field.COORDINATE_SYSTEM_TYPE_RECTANGULAR_CARTESIAN:
        print('zincutils.offset_scaffold: field is not rectangular cartesian')
        return False
    fe_field = field.castFiniteElement()
    if not fe_field.isValid():
        print('zincutils.transformCoordinates: field is not finite element field type')
        return False
    success = True
    fm = field.getFieldmodule()
    fm.beginChange()
    cache = fm.createFieldcache()
    nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    node_template = nodes.createNodetemplate()
    node_iter = nodes.createNodeiterator()
    node = node_iter.next()
    while node.isValid():
        node_template.defineFieldFromNode(fe_field, node)
        cache.setNode(node)
        for derivative in [Node.VALUE_LABEL_VALUE, Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2,
                           Node.VALUE_LABEL_D2_DS1DS2, Node.VALUE_LABEL_D_DS3, Node.VALUE_LABEL_D2_DS1DS3,
                           Node.VALUE_LABEL_D2_DS2DS3, Node.VALUE_LABEL_D3_DS1DS2DS3]:
            versions = node_template.getValueNumberOfVersions(fe_field, -1, derivative)
            for v in range(1, versions + 1):
                result, values = fe_field.getNodeParameters(cache, -1, derivative, v, number_of_components)
                if result != ZINC_OK:
                    success = False
                else:
                    if derivative == Node.VALUE_LABEL_VALUE:
                        new_values = add(values, offset)
                    else:
                        new_values = values
                    result = fe_field.setNodeParameters(cache, -1, derivative, v, new_values)
                    if result != ZINC_OK:
                        success = False
        node = node_iter.next()
    fm.endChange()
    if not success:
        print('zincutils.offset_scaffold: failed to get/set some values')
    return success
