import os
import sys

from data_agent.local_agent import LocalAgent
from PySide6 import QtCore, QtWidgets

from qt_data_extractor.mainwindow import MainWindow

__author__ = "Meir Tseitlin"
__copyright__ = "Imubit"
__license__ = "LGPLv3"


def run():
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.pysideplugin=false"

    app = QtWidgets.QApplication(sys.argv)

    with LocalAgent() as agent:
        gui = MainWindow(agent.api)
        gui.setup()
        gui.show()

        app.exec()


if __name__ == "__main__":
    run()
