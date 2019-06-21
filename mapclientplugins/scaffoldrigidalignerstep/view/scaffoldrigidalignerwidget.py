from PySide import QtGui

from .ui_scaffoldrigidalignerwidget import Ui_ScaffoldRigidAlignerWidget

from opencmiss.zinchandlers.scenemanipulation import SceneManipulation
from opencmiss.zincwidgets.basesceneviewerwidget import BaseSceneviewerWidget


class ScaffoldRigidAlignerWidget(QtGui.QWidget):

    def __init__(self, master_model, parent=None):
        super(ScaffoldRigidAlignerWidget, self).__init__(parent)

        self._model = master_model

        self._ui = Ui_ScaffoldRigidAlignerWidget()
        self._ui.setupUi(self, self._get_shareable_open_gl_widget())
        self._setup_handlers()

        self._ui.sceneviewerWidget.set_context(self._model.get_context())
        self._ui.overlaySceneviewerWidget.set_context(self._model.get_context())

        self._done_callback = None
        self._settings = {'view-parameters': {}}
        self._partial_data = dict()
        self._model.set_settings_change_callback(self._setting_display)
        self._temporal_data_flag = False
        self._model_description = None
        self._make_connections()

    def _make_connections(self):
        self._ui.sceneviewerWidget.graphics_initialized.connect(self._graphics_initialized)
        self._ui.overlaySceneviewerWidget.graphics_initialized.connect(self._graphics_initialized)
        self._ui.doneButton.clicked.connect(self._done_clicked)
        self._ui.viewAllButton.clicked.connect(self._view_all)
        self._ui.timeYes_radioButton.clicked.connect(self._data_is_temporal)
        self._ui.timeNo_radioButton.clicked.connect(self._data_is_static)
        self._ui.timeSkip_pushButton.clicked.connect(self._confirm_and_load)
        self._ui.timePoint_spinBox.valueChanged.connect(self._time_changed)
        self._ui.partialData_checkBox.clicked.connect(self._data_is_partial)
        self._ui.scaffoldZ_radioButton.clicked.connect(self._scaffold_z_up)
        self._ui.scaffoldY_radioButton.clicked.connect(self._scaffold_y_up)
        self._ui.scaffoldX_radioButton.clicked.connect(self._scaffold_x_up)
        self._ui.dataZ_radioButton.clicked.connect(self._data_z_up)
        self._ui.datadY_radioButton.clicked.connect(self._data_y_up)
        self._ui.dataX_radioButton.clicked.connect(self._data_x_up)
        self._ui.upsideDown_checkBox.clicked.connect(self._data_upside_down)
        self._ui.axisDone_pushButton.clicked.connect(self._apply_axis_orientation)
        self._ui.yaw_doubleSpinBox.valueChanged.connect(self._yaw_clicked)
        self._ui.pitch_doubleSpinBox.valueChanged.connect(self._pitch_clicked)
        self._ui.roll_doubleSpinBox.valueChanged.connect(self._roll_clicked)
        self._ui.scaleRatio_pushButton.clicked.connect(self._calculate_scale_clicked)
        self._ui.saveSettingsButton.clicked.connect(self._save_settings)
        self._ui.loadSettingsButton.clicked.connect(self._load_settings)
        self._ui.alignResetButton.clicked.connect(self._reset)

    def _setting_display(self):
        self._display_real(self._ui.yaw_doubleSpinBox, self._model.get_yaw_value())
        self._display_real(self._ui.pitch_doubleSpinBox, self._model.get_pitch_value())
        self._display_real(self._ui.roll_doubleSpinBox, self._model.get_roll_value())
        self._set_scaffold_checkbox(self._model.get_scaffold_up())
        self._set_data_checkbox(self._model.get_data_up())
        self._set_flip(self._model.get_flip())

    def _create_graphics(self):
        self._model.create_graphics()

    def _get_shareable_open_gl_widget(self):
        context = self._model.get_context()
        self._shareable_widget = BaseSceneviewerWidget()
        self._shareable_widget.set_context(context)
        return self._shareable_widget

    def _graphics_initialized(self):
        scaffold_scene_viewer = self._ui.sceneviewerWidget.get_zinc_sceneviewer()
        data_scene_viewer = self._ui.overlaySceneviewerWidget.get_zinc_sceneviewer()

        if scaffold_scene_viewer is not None and data_scene_viewer is not None:
            scaffold_scene = self._model.get_scaffold_scene()
            self._ui.sceneviewerWidget.set_scene(scaffold_scene)

            data_scene = self._model.get_data_scene()
            self._ui.overlaySceneviewerWidget.set_scene(data_scene)

            if len(self._settings['view-parameters']) == 0:
                self._view_all()
            else:
                eye = self._settings['view-parameters']['eye']
                look_at = self._settings['view-parameters']['look_at']
                up = self._settings['view-parameters']['up']
                angle = self._settings['view-parameters']['angle']
                self._ui.sceneviewerWidget.set_view_parameters(eye, look_at, up, angle)
                self._ui.overlaySceneviewerWidget.set_view_parameters(eye, look_at, up, angle)
                self._view_all()

    def register_done_execution(self, done_callback):
        self._done_callback = done_callback

    def _refresh_options(self):
        pass

    def _setup_handlers(self):
        basic_handler = SceneManipulation()
        self._ui.sceneviewerWidget.register_handler(basic_handler)
        basic_handler_overlay = SceneManipulation()
        self._ui.overlaySceneviewerWidget.register_handler(basic_handler_overlay)

    def _view_all(self):
        if self._ui.sceneviewerWidget.get_zinc_sceneviewer() is not None:
            self._ui.sceneviewerWidget.view_all()
        if self._ui.overlaySceneviewerWidget.get_zinc_sceneviewer() is not None:
            self._ui.overlaySceneviewerWidget.view_all()

    def _done_clicked(self):
        self._done_callback()

    def get_model_description(self):
        self._model_description = self._model.done(self._temporal_data_flag)
        return self._model_description

    def _set_scaffold_checkbox(self, value):
        if value == 'Z':
            self._ui.scaffoldZ_radioButton.setChecked(True)
        elif value == 'Y':
            self._ui.scaffoldY_radioButton.setChecked(True)
        elif value == 'X':
            self._ui.scaffoldX_radioButton.setChecked(True)

    def _set_data_checkbox(self, value):
        if value == 'Z':
            self._ui.dataZ_radioButton.setChecked(True)
        elif value == 'Y':
            self._ui.datadY_radioButton.setChecked(True)
        elif value == 'X':
            self._ui.dataX_radioButton.setChecked(True)

    def _set_flip(self, value):
        if value is not None:
            self._ui.upsideDown_checkBox.setChecked(value)

    @staticmethod
    def _display_real(widget, value):
        new_text = '{:.4g}'.format(value)
        if isinstance(widget, QtGui.QDoubleSpinBox):
            widget.setValue(value)
        else:
            widget.setText(new_text)

    def _scaffold_z_up(self):
        self._model.set_scaffold_axis('Z')

    def _scaffold_y_up(self):
        self._model.set_scaffold_axis('Y')

    def _scaffold_x_up(self):
        self._model.set_scaffold_axis('X')

    def _data_z_up(self):
        self._model.set_data_axis('Z')

    def _data_y_up(self):
        self._model.set_data_axis('Y')

    def _data_x_up(self):
        self._model.set_data_axis('X')

    def _data_upside_down(self):
        pass

    def _data_is_partial(self):
        if self._ui.partialData_checkBox.isChecked():
            self._ui.partialZ_lineEdit.setEnabled(True)
            self._ui.partialY_lineEdit.setEnabled(True)
            self._ui.partialXlineEdit.setEnabled(True)
        else:
            self._ui.partialZ_lineEdit.setEnabled(False)
            self._ui.partialY_lineEdit.setEnabled(False)
            self._ui.partialXlineEdit.setEnabled(False)

    def _check_if_data_is_partial(self):
        # Partial X:
        if self._ui.partialXlineEdit.text() is not '':
            self._partial_data['X'] = float(self._ui.partialXlineEdit.text())
            self._ui.partialY_lineEdit.setEnabled(False)
            self._ui.partialZ_lineEdit.setEnabled(False)

        # Partial Y
        if self._ui.partialY_lineEdit.text() is not '':
            self._partial_data['Y'] = float(self._ui.partialY_lineEdit.text())
            self._ui.partialXlineEdit.setEnabled(False)
            self._ui.partialZ_lineEdit.setEnabled(False)

        # Partial Z
        if self._ui.partialZ_lineEdit.text() is not '':
            self._partial_data['Z'] = float(self._ui.partialZ_lineEdit.text())
            self._ui.partialXlineEdit.setEnabled(False)
            self._ui.partialY_lineEdit.setEnabled(False)

    def _apply_axis_orientation(self):
        self._check_if_data_is_partial()
        # Apply orientation
        self._model.apply_orientation()
        self._ui.axisDone_pushButton.setEnabled(False)
        self._ui.scaleRatio_pushButton.setEnabled(True)

    def _calculate_scale_clicked(self):
        self._check_if_data_is_partial()
        self._scale_ratio_display(self._partial_data)

    def _scale_ratio_display(self, partial=None):
        self._display_real(self._ui.scaleRatio_lineEdit, self._model.get_scaffold_to_data_ratio(partial=partial))

    def _yaw_clicked(self):
        value = self._ui.yaw_doubleSpinBox.value()
        self._model.rotate_scaffold('yaw', value)

    def _pitch_clicked(self):
        value = self._ui.pitch_doubleSpinBox.value()
        self._model.rotate_scaffold('pitch', value)

    def _roll_clicked(self):
        value = self._ui.roll_doubleSpinBox.value()
        self._model.rotate_scaffold('roll', value)

    def _save_settings(self):
        self._model.save_settings()

    def _load_settings(self):
        self._model.load_settings()
        self._ui.axisDone_pushButton.setEnabled(True)

    def _data_is_temporal(self):
        self._temporal_data_flag = True
        self._ui.timeSkip_pushButton.setEnabled(True)

    def _confirm_and_load(self):
        if self._temporal_data_flag:
            self._ui.timePoint_spinBox.setEnabled(True)
            self._ui.timePoint_label.setEnabled(True)
            self._model.load_json_data()
        else:
            self._model.load_ex_data()
        self._create_graphics()
        self._model.set_time_value(0.0)
        self._model.initialise_time_graphics(0.0)
        self._view_all()
        self._ui.timePoint_spinBox.setMaximum(self._model.get_maximum_time_from_data())

    def _time_changed(self):
        time_value = self._ui.timePoint_spinBox.value()
        self._model.set_time_value(time_value)

    def _skip_value_changed(self):
        self._ui.timeSkip_pushButton.setEnabled(True)

    def _data_is_static(self):
        self._temporal_data_flag = False
        self._ui.timePoint_spinBox.setEnabled(False)
        self._ui.timePoint_label.setEnabled(False)
        self._ui.timeSkip_pushButton.setEnabled(True)

    def _reset(self):
        self._model.reset_settings()
        self._ui.scaffoldZ_radioButton.setAutoExclusive(False)
        self._ui.scaffoldY_radioButton.setAutoExclusive(False)
        self._ui.scaffoldX_radioButton.setAutoExclusive(False)
        self._ui.scaffoldZ_radioButton.setChecked(False)
        self._ui.scaffoldY_radioButton.setChecked(False)
        self._ui.scaffoldX_radioButton.setChecked(False)
        self._ui.dataZ_radioButton.setAutoExclusive(False)
        self._ui.datadY_radioButton.setAutoExclusive(False)
        self._ui.dataX_radioButton.setAutoExclusive(False)
        self._ui.dataZ_radioButton.setChecked(False)
        self._ui.datadY_radioButton.setChecked(False)
        self._ui.dataX_radioButton.setChecked(False)
        self._ui.axisDone_pushButton.setEnabled(True)
        self._ui.upsideDown_checkBox.setChecked(False)
        self._ui.scaleRatio_lineEdit.clear()
