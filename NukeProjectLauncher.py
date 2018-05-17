# -*- coding: utf-8 -*-
# Adam Thompson 2018

import os
import sys
from collections import OrderedDict

try:
    # < Nuke 11
    import PySide.QtCore as QtCore
    import PySide.QtGui as QtGui
    import PySide.QtGui as QtGuiWidgets
    import PySide.QtUiTools as QtUiTools
except:
    # >= Nuke 11
    import PySide2.QtCore as QtCore
    import PySide2.QtGui as QtGui
    import PySide2.QtWidgets as QtGuiWidgets
    import PySide2.QtUiTools as QtUiTools

import nuke

import ConfigReader

DEFAULT_JOBS_DIR = "V:\\Jobs"
CONFIG_FILE_NAME = "config.yml"
TEMPLATE = "nuke_projects"
EXTENSION = ".nk"


def getDirList(directory, reverse=False):
    """Returns a sorted list of directories in a given directory with an optional flag to reverse the order."""
    try:
        dirs = [name for name in os.listdir(directory)
                if os.path.isdir(os.path.join(directory, name))]
    except:
        return None
    return sorted(dirs, reverse=reverse)


def getFileList(directory, extension, reverse=False):
    """Returns a sorted list of files with a given extension in a given directory with an optional flag to reverse the order."""
    try:
        files = [name for name in os.listdir(directory)
                if (not os.path.isdir(os.path.join(directory, name))) & name.lower().endswith(extension)]
    except:
        return None
    return sorted(files, reverse=reverse)


class CustomComboBox(QtGui.QComboBox):
    """This comboBox extends QComboBox, is editable, and suggests semi-fuzzy results from query
    https://stackoverflow.com/questions/4827207/how-do-i-filter-the-pyqt-qcombobox-items-based-on-the-text-input
    """
    def __init__( self,  parent = None):
        super( CustomComboBox, self ).__init__( parent )

        self.setFocusPolicy( QtCore.Qt.StrongFocus )
        self.setEditable( True )
        self.completer = QtGui.QCompleter( self )

        # always show all completions
        self.completer.setCompletionMode( QtGui.QCompleter.UnfilteredPopupCompletion )
        self.pFilterModel = QtGui.QSortFilterProxyModel( self )
        self.pFilterModel.setFilterCaseSensitivity( QtCore.Qt.CaseInsensitive )

        self.completer.setPopup( self.view() )

        self.setCompleter( self.completer )

        self.lineEdit().textEdited[unicode].connect( self.pFilterModel.setFilterFixedString )
        self.completer.activated.connect(self.setTextIfCompleterIsClicked)

    def createItemModel(self, comboList):
        model = QtGui.QStandardItemModel()
        for i,element in enumerate(comboList):
            item = QtGui.QStandardItem(element)
            model.setItem(i, 0, item)
        return model

    def setModel(self, model):
        super(CustomComboBox, self).setModel( model )
        self.pFilterModel.setSourceModel( model )
        self.completer.setModel(self.pFilterModel)

    def setModelColumn(self, column):
        self.completer.setCompletionColumn( column )
        self.pFilterModel.setFilterKeyColumn( column )
        super(CustomComboBox, self).setModelColumn( column )

    def addItems(self, comboList):
        super(CustomComboBox, self).addItems(comboList)
        self.setModel(self.createItemModel(comboList))

    def view( self ):
        return self.completer.popup()

    def index( self ):
        return self.currentIndex()

    def setTextIfCompleterIsClicked(self, text):
      if text:
        index = self.findText(text)
        self.setCurrentIndex(index)


class NukeProjectLauncher(QtGuiWidgets.QDialog):
    
    def __init__(self):
        super(NukeProjectLauncher, self).__init__(QtGuiWidgets.QApplication.activeWindow())
        self.jobsDir = DEFAULT_JOBS_DIR
        self.currentJobPath = ""
        self.tokenComboDict = OrderedDict()
        self.tokenDict = dict()
        self.project = None
        self.finalPath = ""
        self.initUI()
        self.populateJobs()
        self.show()

        
    def initUI(self):

        # Create job selection area ------------------------------------------------------
        self.jobSearchLocLabel = QtGui.QLabel(self.jobsDir)
        self.jobComboBox = CustomComboBox()
        self.jobComboBox.activated[str].connect(self.onJobChange)
        self.setFocus()

        jobvBox = QtGui.QVBoxLayout()
        jobvBox.addWidget(self.jobSearchLocLabel)
        jobvBox.addWidget(self.jobComboBox)

        jobGroupBox = QtGui.QGroupBox("Job")
        jobGroupBox.setLayout(jobvBox)

        # Token selection Area -----------------------------------------------------------

        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(self.formLayout.AllNonFixedFieldsGrow)

        tokenGroupBox = QtGui.QGroupBox("Tokens")
        tokenGroupBox.setLayout(self.formLayout)


        # File selection Area ------------------------------------------------------------
        self.fileComboBox = CustomComboBox()
        self.fileComboBox.activated[str].connect(self.onFileChange)

        filevBox = QtGui.QVBoxLayout()
        filevBox.addWidget(self.fileComboBox)

        fileGroupBox = QtGui.QGroupBox("File")
        fileGroupBox.setLayout(filevBox)

        self.pathLabel = QtGui.QLabel(self.jobsDir)

        # Launch and cancel buttons
        self.launchButton = QtGui.QPushButton("Launch")
        self.launchButton.clicked.connect(self.launchNuke)
        self.launchButton.setEnabled(False)
        cancelButton = QtGui.QPushButton("Cancel")
        cancelButton.clicked.connect(self.close)

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.launchButton)
        hbox.addWidget(cancelButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(jobGroupBox)
        vbox.addWidget(tokenGroupBox)
        vbox.addWidget(fileGroupBox)
        vbox.addWidget(self.pathLabel)
        vbox.addStretch(1)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.resize(600,0)
        self.setWindowTitle("Nuke Project Launcher") 

    def populateJobs(self):
        """Look in jobs folder for jobs that contain the config file at root"""
        jobsList = getDirList(self.jobsDir)
        jobsList[:] = [job for job in jobsList if os.path.isfile(os.path.join(self.jobsDir, job, CONFIG_FILE_NAME))]
        self.jobComboBox.clear()
        self.jobComboBox.addItems(jobsList)
        self.onJobChange(jobsList[0])


    def onJobChange(self, job):
        self.currentJobPath = os.path.join(self.jobsDir, job)
        self.project = Project(self.currentJobPath)
        self.pathLabel.setText(self.currentJobPath)
        self.createTokenCombos()
        self.launchButton.setEnabled(False)
        # self.comboLabel.adjustSize()

    def createTokenCombos(self):
        """Create a form with a combobox for each token"""

        # Remove all rows from the formLayout
        for i in reversed(range(self.formLayout.count())): 
            self.formLayout.itemAt(i).widget().setParent(None)

        self.tokenComboDict.clear()

        tokenList = self.project.getTokens()

        for token in tokenList:
            tokenCombo = CustomComboBox()
            index = tokenList.index(token)
            tokenCombo.activated.connect(self.onTokenChange)
            self.tokenComboDict[token] = tokenCombo
            if index == 0:
                tokenCombo.setTabOrder(self.jobComboBox, tokenCombo)

            self.formLayout.addRow(self.tr(token), tokenCombo)

        self.fileComboBox.clear()
        self.populateTokenCombo(self.tokenComboDict.keys()[0])


    def onTokenChange(self, text):
        thisCombo = self.sender()
        index = self.tokenComboDict.values().index(thisCombo)

        # Set self.tokenDict to list of all previous combos + new one
        self.tokenDict.clear()
        for token, combo in self.tokenComboDict.iteritems():
            self.tokenDict[token] = combo.currentText()
            if combo == thisCombo:
                # Set pathLabel to updated path
                currentPath = self.project.getPath(TEMPLATE, self.tokenDict, token)
                self.pathLabel.setText(os.path.join(currentPath, combo.currentText()))
                self.pathLabel.adjustSize()
                break

        # Always clear fileComboBox
        self.fileComboBox.clear()
        self.launchButton.setEnabled(False)

        # Populate next token combo 
        if index+1 < len(self.tokenComboDict.values()):
            self.populateTokenCombo(self.tokenComboDict.keys()[index+1])            
        # Else, populate the file combo
        else:
            self.populateFileCombo()


    def populateFileCombo(self):
        self.fileComboBox.clear()
        populatePath = self.project.getPath(TEMPLATE, self.tokenDict)
        fileList = getFileList(populatePath, EXTENSION)
        if len(fileList) > 0:
            self.fileComboBox.addItems(fileList)
            # Set to latest version
            self.fileComboBox.setCurrentIndex(self.fileComboBox.count()-1)
            self.onFileChange()
        

    def populateTokenCombo(self, token):
        comboBox = self.tokenComboDict[token]
        populatePath = self.project.getPath(TEMPLATE, self.tokenDict, token)
        comboBox.clear()

        folderList = getDirList(populatePath)
        comboBox.addItems(folderList)
        # comboBox.setModel(self.createItemModel(folderList))
        # comboBox.completer.setModel(comboBox.model())
        # comboBox.completer.setCompletionMode(QtGui.QCompleter.UnfilteredPopupCompletion)
        comboBox.setCurrentIndex(0)
        comboBox.activated.emit(0)

    def onFileChange(self):
        # Update pathLabel to reflect new file 
        currentPath = self.project.getPath(TEMPLATE, self.tokenDict)
        self.finalPath = os.path.join(currentPath, self.fileComboBox.currentText())
        self.pathLabel.setText(self.finalPath)
        self.launchButton.setEnabled(True)

    def launchNuke(self):
        nuke.scriptOpen(self.finalPath)
        self.close()


class Project():

    def __init__(self, jobPath):
        self.configReader = ConfigReader.ConfigReader(jobPath)

    def getTokens(self):
        return self.configReader.getTokens(TEMPLATE)

    def getPath(self, template, tokenDict, destinationToken=None):
        return self.configReader.getPath(template, tokenDict, destinationToken)


ex = NukeProjectLauncher()