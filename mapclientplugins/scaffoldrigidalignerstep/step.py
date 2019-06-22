
"""
MAP Client Plugin Step
"""
import os
import json

from PySide import QtGui

from mapclient.mountpoints.workflowstep import WorkflowStepMountPoint
from mapclientplugins.scaffoldrigidalignerstep.configuredialog import ConfigureDialog
from mapclientplugins.scaffoldrigidalignerstep.model.mastermodel import MasterModel
from mapclientplugins.scaffoldrigidalignerstep.view.scaffoldrigidalignerwidget import ScaffoldRigidAlignerWidget

EX_FILE_FORMATS = ['.exf', '.exdata', '.ex2', 'exnode', '.ex']

class ScaffoldRigidAlignerStep(WorkflowStepMountPoint):
    """
    Skeleton step which is intended to be a helpful starting point
    for new steps.
    """

    def __init__(self, location):
        super(ScaffoldRigidAlignerStep, self).__init__('Scaffold Rigid Aligner', location)
        self._configured = False # A step cannot be executed until it has been configured.
        self._category = 'Registration'
        # Add any other initialisation code here:
        self._icon =  QtGui.QImage(':/scaffoldrigidalignerstep/images/registration.png')
        # Ports:
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#uses',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#file_location'))
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#uses',
                      'generator_model'))
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#provides',
                      'model_description'))
        # Port data:
        self._pointCloudData = None  # file_location: point cloud data
        self._modelDescription = None  # scaffold
        self._portData2 = None  # model_description
        # Config:
        self._config = {}
        self._config['identifier'] = ''
        self._model = None
        self._view = None

    def execute(self):
        """
        Add your code here that will kick off the execution of the step.
        Make sure you call the _doneExecution() method when finished.  This method
        may be connected up to a button in a widget for example.
        """
        # Put your execute step code here before calling the '_doneExecution' method.
        if self._view is None:
            context = 'ScaffoldRigidAlignerContext'

            modelDescription = self._modelDescription.get_scaffold_description()
            self._model = MasterModel(context, modelDescription)
            sir = self._model.get_stream()
            self._model.initialise_scaffold(sir)

            _, file_extension = os.path.splitext(self._pointCloudData)
            if file_extension in EX_FILE_FORMATS:
                self._model.initialise_ex_data(self._pointCloudData)
            elif file_extension == '.json':
                self._model.initialise_json_data(self._pointCloudData)
            else:
                raise TypeError('Data file with {} format is not supported.'
                                'Use EX or JSON.'.format(file_extension))

            self._model.set_location(os.path.join(self._location, self._config['identifier']))
            self._view = ScaffoldRigidAlignerWidget(self._model)
            self._view.register_done_execution(self._myDoneExecution)

        self._setCurrentWidget(self._view)

    def _myDoneExecution(self):
        scaffoldDescription = self._view.get_model_description()
        modelDescription = self._modelDescription
        fullDescription = [scaffoldDescription, modelDescription]
        self._portData2 = fullDescription
        self._model = None
        self._view = None
        self._doneExecution()

    def setPortData(self, index, dataIn):
        """
        Add your code here that will set the appropriate objects for this step.
        The index is the index of the port in the port list.  If there is only one
        uses port for this step then the index can be ignored.

        :param index: Index of the port to return.
        :param dataIn: The data to set for the port at the given index.
        """
        if index == 0:
            self._pointCloudData = dataIn  # file_location: point cloud data
        elif index == 1:
            self._modelDescription = dataIn  # scaffold

    def getPortData(self, index):
        """
        Add your code here that will return the appropriate objects for this step.
        The index is the index of the port in the port list.  If there is only one
        provides port for this step then the index can be ignored.

        :param index: Index of the port to return.
        """
        return self._portData2  # model_description

    def configure(self):
        """
        This function will be called when the configure icon on the step is
        clicked.  It is appropriate to display a configuration dialog at this
        time.  If the conditions for the configuration of this step are complete
        then set:
            self._configured = True
        """
        dlg = ConfigureDialog(self._main_window)
        dlg.identifierOccursCount = self._identifierOccursCount
        dlg.setConfig(self._config)
        dlg.validate()
        dlg.setModal(True)

        if dlg.exec_():
            self._config = dlg.getConfig()

        self._configured = dlg.validate()
        self._configuredObserver()

    def getIdentifier(self):
        """
        The identifier is a string that must be unique within a workflow.
        """
        return self._config['identifier']

    def setIdentifier(self, identifier):
        """
        The framework will set the identifier for this step when it is loaded.
        """
        self._config['identifier'] = identifier

    def serialize(self):
        """
        Add code to serialize this step to string.  This method should
        implement the opposite of 'deserialize'.
        """
        return json.dumps(self._config, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def deserialize(self, string):
        """
        Add code to deserialize this step from string.  This method should
        implement the opposite of 'serialize'.

        :param string: JSON representation of the configuration in a string.
        """
        self._config.update(json.loads(string))

        d = ConfigureDialog()
        d.identifierOccursCount = self._identifierOccursCount
        d.setConfig(self._config)
        self._configured = d.validate()


