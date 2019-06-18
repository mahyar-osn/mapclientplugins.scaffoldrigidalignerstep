from PySide import QtGui, QtCore

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
        self._make_connections()

    def _make_connections(self):
        self._ui.sceneviewerWidget.graphics_initialized.connect(self._graphics_initialized)
        self._ui.overlaySceneviewerWidget.graphics_initialized.connect(self._graphics_initialized)
        self._ui.doneButton.clicked.connect(self._done_clicked)
        self._ui.viewAllButton.clicked.connect(self._view_all)

    def create_graphics(self):
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
