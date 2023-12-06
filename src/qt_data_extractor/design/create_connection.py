from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
)


class DirectoryBrowserField(QDialog):
    def __init__(self):
        super().__init__()

        self._main_layout = QHBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)

        self._selected_dir = QLineEdit()
        self._main_layout.addWidget(self._selected_dir)

        dir_browser = QPushButton("...")
        dir_browser.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        def on_folder_select():
            folder = str(
                QFileDialog.getExistingDirectory(self, "Select Archive Folder")
            )
            self._selected_dir.setText(folder)

        dir_browser.clicked.connect(on_folder_select)
        self._main_layout.addWidget(dir_browser)

        self.setLayout(self._main_layout)

    def text(self):
        return self._selected_dir.text()


class FileBrowserField(QDialog):
    def __init__(self):
        super().__init__()

        self._main_layout = QHBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)

        self._selected_file = QLineEdit()
        self._main_layout.addWidget(self._selected_file)

        file_browser = QPushButton("...")
        file_browser.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        def on_file_select():
            selected_file, _ = QFileDialog.getSaveFileName(self, "Select Archive File")
            self._selected_file.setText(selected_file)

        file_browser.clicked.connect(on_file_select)
        self._main_layout.addWidget(file_browser)

        self.setLayout(self._main_layout)

    def text(self):
        return self._selected_file.text()


class CreateConnectionDialog(QDialog):
    def __init__(self, connectors):
        super().__init__()

        self._connectors = connectors

        self._main_layout = QGridLayout()

        submit_button = QPushButton(self.tr("&Submit"))
        submit_button.setDefault(True)
        submit_button.setEnabled(False)
        submit_button.clicked.connect(self.accept)

        cancel_button = QPushButton(self.tr("&Cancel"))
        # cancelButton.setAutoDefault(False)
        cancel_button.clicked.connect(self.reject)

        @QtCore.Slot(str)
        def on_mandatory_field_changed(val):
            if not val.strip():
                submit_button.setEnabled(False)
            else:
                submit_button.setEnabled(True)

        self._main_layout.addWidget(QLabel("Enter new connection details:"), 0, 0)

        self.connection_name = QLineEdit()
        self.connection_name.setValidator(
            QtGui.QRegularExpressionValidator("[a-zA-Z0-9\_]+")  # noqa: W605
        )
        self.connection_name.textChanged.connect(on_mandatory_field_changed)
        self._main_layout.addWidget(QLabel("Connection name:"), 1, 0)
        self._main_layout.addWidget(self.connection_name, 1, 1)

        self.connection_type = QComboBox()
        for connector in self._connectors:
            self.connection_type.addItem(f"{connector}", self._connectors[connector])

        @QtCore.Slot(str)
        def on_connection_type_change(index):
            _update_dynamic_fields()

        self.connection_type.currentIndexChanged.connect(on_connection_type_change)

        self._main_layout.addWidget(QLabel("Connection type:"), 2, 0)
        self._main_layout.addWidget(self.connection_type, 2, 1)

        self.dynamic_fields = {}

        def _update_dynamic_fields():
            self.dynamic_fields = {}

            for row in range(10):
                for col in range(2):
                    layout = self._main_layout.itemAtPosition(3 + row, col)
                    if layout is not None:
                        layout.widget().deleteLater()
                        self._main_layout.removeItem(layout)

            connection_data = self.connection_type.currentData()
            if not connection_data:
                return

            fields = connection_data["connection_fields"]

            for i, field_name in enumerate(fields):
                label = QLabel(f"{fields[field_name]['name']}:")
                if fields[field_name]["type"] == "str":
                    widget = QLineEdit()
                elif fields[field_name]["type"] == "list":
                    widget = QComboBox()
                    for item in fields[field_name]["values"]:
                        widget.addItem(item)
                elif fields[field_name]["type"] == "local_folder":
                    widget = DirectoryBrowserField()
                elif fields[field_name]["type"] == "local_file":
                    widget = FileBrowserField()
                else:
                    raise RuntimeError("Unsupported Widget")

                self._main_layout.addWidget(label, 3 + i, 0)
                self._main_layout.addWidget(widget, 3 + i, 1)

                self.dynamic_fields[field_name] = widget

            self._main_layout.setSizeConstraint(QLayout.SetMinimumSize)

        self._button_box = QDialogButtonBox()
        self._button_box.addButton(submit_button, QDialogButtonBox.ActionRole)
        self._button_box.addButton(cancel_button, QDialogButtonBox.ActionRole)

        # self._button_box.clicked.connect(self.accept)
        # self._button_box.rejected.connect(self.reject)

        self._main_layout.addWidget(self._button_box, 20, 0)

        self._main_layout.setSizeConstraint(QLayout.SetMinimumSize)

        self.setLayout(self._main_layout)

        _update_dynamic_fields()

    @property
    def values(self):
        res = {
            "conn_name": self.connection_name.text().strip(),
            "conn_type": self.connection_type.currentText().strip(),
        }

        for field in self.dynamic_fields:
            if isinstance(self.dynamic_fields[field], QLineEdit) or isinstance(
                self.dynamic_fields[field], DirectoryBrowserField
            ):
                res[field] = self.dynamic_fields[field].text().strip()
            elif isinstance(self.dynamic_fields[field], QComboBox):
                res[field] = self.dynamic_fields[field].currentText().strip()

        return res
