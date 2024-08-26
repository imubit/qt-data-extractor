import logging
import os
import sys
from collections import OrderedDict
from datetime import datetime

import pandas as pd
from data_agent.exceptions import GroupAlreadyExists, TargetConnectionError
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (  # QToolTip,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QTreeWidgetItem,
)

from qt_data_extractor import __version__
from qt_data_extractor.design.create_connection import CreateConnectionDialog
from qt_data_extractor.design.pandas_model import DataTableDialog
from qt_data_extractor.worker_thread import Worker

log = logging.getLogger(__name__)

WINDOW_DEFAULT_TITLE = "Imubit Data Extractor"
SHORT_VERSION = f'{__version__.split(".")[0]}.{__version__.split(".")[1]}'
MAX_TAGS_TO_LOAD = 100
MAX_PREVIEW_SAMPLES = 500
ENABLE_EDITING_CONFIG_BEFORE_EXTRACTION = False
TAGS_FILTER_DEFAULT_PLACEHOLDER = "Search tags by filter..."

bundle_dir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))


class NoDelayHintProxyStyle(QtWidgets.QProxyStyle):
    def __init__(self):
        QtWidgets.QProxyStyle.__init__(self)

    def styleHint(self, hint, option=..., widget=..., returnData=...):
        if hint == QtWidgets.QStyle.SH_ToolTip_WakeUpDelay:
            return 0

        return QtWidgets.QProxyStyle.styleHint(self, hint, option, widget, returnData)


class MainWindow(QtCore.QObject):
    def __init__(self, api):
        loader = QUiLoader()

        self._api = api
        self._existing_connections = []
        self._registered_connectors = self._api.list_supported_connectors()
        self._registered_connectors = {
            k: self._registered_connectors[k]
            for k in self._registered_connectors
            if self._registered_connectors[k]["category"] == "historian"
        }
        self._w = loader.load(
            os.path.abspath(os.path.join(bundle_dir, "design/main-window.ui")), None
        )
        self._dialogCopyPrompt = loader.load(
            os.path.abspath(os.path.join(bundle_dir, "design/copy-prompt.ui")),
            parentWidget=self._w,
        )
        self._dialogCopyPrompt.setWindowTitle(WINDOW_DEFAULT_TITLE)
        self._dialogCopyProgress = loader.load(
            os.path.abspath(os.path.join(bundle_dir, "design/copy-progress.ui")),
            parentWidget=self._w,
        )
        self._dialogCopyProgress.setWindowTitle(WINDOW_DEFAULT_TITLE)
        self._dialogCreateConnection = CreateConnectionDialog(
            connectors=self._registered_connectors
        )
        self._dialogCreateConnection.setWindowTitle(WINDOW_DEFAULT_TITLE)
        self._dialogManageConnections = loader.load(
            os.path.abspath(os.path.join(bundle_dir, "design/manage-connections.ui")),
            parentWidget=self._w,
        )
        self._dialogManageConnections.setWindowTitle(WINDOW_DEFAULT_TITLE)

        self._w.comboSampleRate.setToolTip(
            """
            <h3>READ BEFORE CHANGING...</h3><br />
            <b><i>Changing this setting may have undesirable effects:</i></b>
            <ul>
            <li> When used with Osisoft PI plugin and the data has a lower frequency than selected in this option,
            the data will be "filled forward"", effectively creating a fake data that does not necessarily corresponds
            to the original signal.</li>
            </ul>
        """
        )

        self._w.comboSampleRate.setStyle(NoDelayHintProxyStyle())

        self.threadpool = QtCore.QThreadPool()

    def _show_msg_box(self, msg, icon=QMessageBox.Icon.Information):
        mb = QMessageBox(self._w)
        mb.setIcon(QMessageBox.Icon.Information)
        mb.setWindowTitle(self._w.windowTitle())
        mb.setText(msg)
        return mb.exec_()

    @staticmethod
    def _connection_title(conn_name, conn_type):
        return f"{conn_name} ({conn_type})"

    def _get_selected_tags(self):
        return [
            self._w.treeSelectedTags.topLevelItem(i).data(0, QtCore.Qt.UserRole)
            for i in range(0, self._w.treeSelectedTags.topLevelItemCount())
        ]

    @property
    def _current_connection(self):
        return self._w.comboLeftConnection.currentData()

    # SLOTS

    @QtCore.Slot(str)
    def on_connection_change(self):
        current_conn = self._current_connection
        if not current_conn:
            self._refresh_current_connection_view(current_conn=None)
            return

        if current_conn == "add_new":
            self._w.comboLeftConnection.setCurrentIndex(-1)
            self.on_create_new_connection()
            return

        if not current_conn["enabled"]:
            self._refresh_current_connection_view(current_conn)
            self._show_msg_box(
                f"Connection '{current_conn['name']}' disabled!",
                icon=QMessageBox.Icon.Warning,
            )
            return

        is_connected = self._api.is_connected(current_conn["name"])

        if is_connected:
            conn_info = self._api.connection_info(current_conn["name"])
        else:
            try:
                self._api.enable_connection(current_conn["name"])
            except TargetConnectionError as e:
                self._refresh_current_connection_view(current_conn)
                self._show_msg_box(
                    f"Error connecting '{current_conn['name']}': {str(e)}",
                    icon=QMessageBox.Icon.Error,
                )
                return

        # conn_info = self._api.connection_info(current_conn['name'])
        self._refresh_current_connection_view(current_conn, conn_info)

    @QtCore.Slot()
    def on_create_new_connection(self):
        if self._dialogCreateConnection.exec_() != QDialog.Accepted:
            return

        args = self._dialogCreateConnection.values
        args["enabled"] = True
        args["ignore_existing"] = False

        try:
            self._api.create_connection(**args)
            self._refresh_connections()
            self._w.comboLeftConnection.setCurrentText(
                self._connection_title(args["conn_name"], args["conn_type"])
            )

        except Exception as e:
            QMessageBox.critical(self._w, self._w.windowTitle(), str(e))

    @QtCore.Slot()
    def on_manage_connections(self):
        delete_button = QPushButton(self.tr("&Delete"))

        # self._dialogManageConnections.tableConnections.clear()
        self._dialogManageConnections.tableConnections.setRowCount(
            len(self._existing_connections)
        )
        for i, conn in enumerate(self._existing_connections):
            self._dialogManageConnections.tableConnections.setItem(
                i, 0, QTableWidgetItem(conn["name"])
            )
            item_type = QTableWidgetItem(conn["type"])
            item_type.setFlags(item_type.flags() & ~QtCore.Qt.ItemIsEditable)
            self._dialogManageConnections.tableConnections.setItem(i, 1, item_type)
            item_enabled = QTableWidgetItem(conn["enabled"])
            item_enabled.setFlags(item_enabled.flags() & ~QtCore.Qt.ItemIsEditable)
            item_enabled.setCheckState(
                QtCore.Qt.Checked if conn["enabled"] else QtCore.Qt.Unchecked
            )
            self._dialogManageConnections.tableConnections.setItem(i, 2, item_enabled)

        if len(self._existing_connections) > 0:

            @QtCore.Slot()
            def on_delete_connection():
                item = self._dialogManageConnections.tableConnections.item(
                    self._dialogManageConnections.tableConnections.currentRow(), 0
                )

                if not item:
                    return

                conn_name = item.text()

                if (
                    QMessageBox.question(
                        self._w,
                        self._w.windowTitle(),
                        f'Delete "{conn_name}" connection? (this operation cannot be undone)',
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    == QMessageBox.StandardButton.Yes
                ):
                    self._api.delete_connection(conn_name)
                    self._dialogManageConnections.tableConnections.removeRow(
                        self._dialogManageConnections.tableConnections.currentRow()
                    )
                    self._refresh_connections()

            delete_button.clicked.connect(on_delete_connection)
            self._dialogManageConnections.buttonBox.addButton(
                delete_button, QDialogButtonBox.ResetRole
            )

        if self._dialogManageConnections.exec_() == QDialog.Accepted:
            pass

        if len(self._existing_connections) > 0:
            self._dialogManageConnections.buttonBox.removeButton(delete_button)

    @QtCore.Slot()
    def on_view_tags(self, left=True):
        source_conn = self._w.comboLeftConnection.currentData()

        items = (
            self._w.treeLeftTagHierarchy.selectedItems()
            if left
            else self._w.treeSelectedTags.selectedItems()
        )

        # for i in items:
        #     print(i.data(0, QtCore.Qt.UserRole), ':::', i.parent().data(0, QtCore.Qt.UserRole))

        source_tags = {
            i.data(0, QtCore.Qt.UserRole): i.data(1, QtCore.Qt.UserRole) for i in items
        }

        if not source_tags:
            self._show_msg_box("No tags selected!")
            return

        try:
            df = self._api.read_tag_values_period(
                conn_name=source_conn["name"],
                tags=list(source_tags.keys()),
                first_timestamp=self._w.dateTimeLeftFrom.dateTime().toPython(),
                last_timestamp=self._w.dateTimeLeftTo.dateTime().toPython(),
                time_frequency=self._w.comboSampleRate.currentText(),
                max_results=MAX_PREVIEW_SAMPLES,
            )

            if len(df) == 0:
                self._show_msg_box("No data available in the selected period!")
                return

            dlg = DataTableDialog(df, parent=self._w)
            dlg.show()

        except Exception as e:
            QMessageBox.critical(self._w, self._w.windowTitle(), str(e))

    @QtCore.Slot()
    def on_selected_tags_change(self):
        selected_items = len(self._w.treeSelectedTags.selectedItems())
        total_items = self._w.treeSelectedTags.topLevelItemCount()
        self._w.labelRightPanelStatus.setText(
            f"{selected_items} / {total_items} tags"
            if selected_items > 0
            else f"{total_items} tags"
        )

    @QtCore.Slot()
    def on_add_selected_tags(self):
        source_items = self._w.treeLeftTagHierarchy.selectedItems()

        source_tags = {
            i.data(0, QtCore.Qt.UserRole): i.data(1, QtCore.Qt.UserRole)
            for i in source_items
        }
        if not source_tags:
            return

        for i, tag_name in enumerate(source_tags):
            if tag_name in self._get_selected_tags():
                continue

            row = [source_tags[tag_name]["Name"]]

            item = QTreeWidgetItem(row)
            item.setData(0, QtCore.Qt.UserRole, (tag_name))
            item.setData(1, QtCore.Qt.UserRole, (source_tags[tag_name]))

            self._w.treeSelectedTags.addTopLevelItem(item)

        self._mark_selected_tags()

        self.on_selected_tags_change()

    @QtCore.Slot()
    def on_remove_selected_tags(self, all):
        if all:
            self._w.treeSelectedTags.clear()
            self._mark_selected_tags()
            return

        root = self._w.treeSelectedTags.invisibleRootItem()
        for item in self._w.treeSelectedTags.selectedItems():
            (item.parent() or root).removeChild(item)

        self._mark_selected_tags()

    @QtCore.Slot()
    def on_copy_tags(self):
        source_conn = self._w.comboLeftConnection.currentData()
        source_tags = self._get_selected_tags()

        if not source_tags:
            self._show_msg_box("No tags selected!")
            return

        if not self._w.comboArchiveDirectory.currentText():
            self._show_msg_box("Archive directory not selected!")
            return

        now = datetime.now()

        dest_conn_name = self._dialogCopyPrompt.comboCopyTarget.currentText()

        filename = (
            f'extractor-output-v{SHORT_VERSION}-{now.strftime("%Y-%m-%dT%H-%M-%S")}'
        )

        file_path = os.path.join(
            self._w.comboArchiveDirectory.currentText(),
            filename,
        )

        self._dialogCopyPrompt.labelCopyDescription.setText(
            f"Extract {len(source_tags)} tags to"
        )
        self._dialogCopyPrompt.comboCopyTarget.addItem(
            self._w.comboArchiveDirectory.currentText()
        )
        self._dialogCopyPrompt.dateTimeFrom.setDateTime(
            self._w.dateTimeLeftFrom.dateTime()
        )
        self._dialogCopyPrompt.dateTimeTo.setDateTime(self._w.dateTimeLeftTo.dateTime())
        self._dialogCopyPrompt.comboSampleRate.setCurrentIndex(
            self._w.comboSampleRate.currentIndex()
        )
        self._dialogCopyPrompt.checkboxAttributesOnly.stateChanged.connect(
            lambda state: self._dialogCopyPrompt.groupboxDataSettings.setEnabled(
                state == 0
            )
        )
        self._dialogCopyPrompt.checkboxAttributesOnly.setCheckState(
            self._w.checkboxExtractAttributesOnly.checkState()
        )

        if not ENABLE_EDITING_CONFIG_BEFORE_EXTRACTION:
            # Put everything in readonly mode
            self._dialogCopyPrompt.comboCopyTarget.setEnabled(False)
            self._dialogCopyPrompt.groupboxDataSettings.setEnabled(False)
            self._dialogCopyPrompt.checkboxAttributesOnly.setEnabled(False)

        do_copy_prompt = self._dialogCopyPrompt.exec_()
        if do_copy_prompt != 1:
            return

        try:
            dest_group = ""
            copy_from_timestamp = (
                self._dialogCopyPrompt.dateTimeFrom.dateTime().toPython()
            )
            copy_to_timestamp = self._dialogCopyPrompt.dateTimeTo.dateTime().toPython()
            attributes_only = self._dialogCopyPrompt.checkboxAttributesOnly.isChecked()

            self._dialogCopyProgress.buttonBox.button(QDialogButtonBox.Cancel).setText(
                "Cancel"
            )
            self._dialogCopyProgress.buttonBox.button(
                QDialogButtonBox.Cancel
            ).setEnabled(False)
            self._dialogCopyProgress.textExtractionLog.clear()
            self._dialogCopyProgress.labelCopy.setText("Extraction in progress...")
            self._dialogCopyProgress.labelFrom.setText(f'From: [{source_conn["name"]}]')
            self._dialogCopyProgress.labelTo.setText(f"To: [{filename}.zip]")
            self._dialogCopyProgress.labelTotalCopied.setText(f"0 / {len(source_tags)}")
            self._dialogCopyProgress.progressBar.setRange(0, len(source_tags))
            self._dialogCopyProgress.progressBar.setValue(0)

            self._dialogCopyProgress.show()

            # Functions executed from worker thread
            def update_progress(tag, counter):
                log.info(f"Extracting tag ({counter}) - {tag}")
                self._dialogCopyProgress.textExtractionLog.append(
                    f"Extracting tag {counter}: {tag}"
                )
                self._dialogCopyProgress.progressBar.setValue(counter - 1)
                self._dialogCopyProgress.labelFrom.setText(
                    f'From: [{source_conn["name"]}] {tag} ...'
                )
                self._dialogCopyProgress.labelTotalCopied.setText(
                    f"{counter} / {len(source_tags)}"
                )

            def copy_process_run(progress_callback):
                self._dialogCopyProgress.textExtractionLog.append(
                    f'Initialiizing data extraction from [{source_conn["name"]}]...'
                )
                self._dialogCopyProgress.textExtractionLog.append(
                    f"Opening {file_path}.zip archive..."
                )
                dest_conn = self._api.create_connection(
                    conn_name=dest_conn_name,
                    conn_type="zip",
                    enabled=True,
                    ignore_existing=True,
                    zipfile_path=f"{file_path}.zip",
                )

                self._api.copy_attributes(
                    src_conn=source_conn["name"],
                    tags=source_tags,
                    dest_conn=dest_conn["name"],
                    dest_group=dest_group,
                )

                if not attributes_only:
                    try:
                        self._api.copy_period(
                            src_conn=source_conn["name"],
                            tags=source_tags,
                            dest_conn=dest_conn["name"],
                            dest_group=dest_group,
                            first_timestamp=copy_from_timestamp,
                            last_timestamp=copy_to_timestamp,
                            time_frequency=self._dialogCopyPrompt.comboSampleRate.currentText(),
                            on_conflict="ask",
                            # progress_callback=lambda tag, counter: update_progress(tag, counter))
                            progress_callback=lambda tag, counter: progress_callback.emit(
                                tag, counter
                            ),
                        )

                    except GroupAlreadyExists as e:
                        if (
                            QMessageBox.question(
                                self._w,
                                self._w.windowTitle(),
                                f"{e} \n Would you like to proceed and append to existing data?",
                                QMessageBox.Yes | QMessageBox.No,
                            )
                            == QMessageBox.StandardButton.Yes
                        ):
                            self._api.copy_period(
                                src_conn=source_conn["name"],
                                tags=source_tags,
                                dest_conn=dest_conn["name"],
                                dest_group=dest_group,
                                first_timestamp=copy_from_timestamp,
                                last_timestamp=copy_to_timestamp,
                                time_frequency=self._dialogCopyPrompt.comboSampleRate.currentText(),
                                on_conflict="append",
                                # progress_callback=lambda tag, counter: update_progress(tag, counter))
                                progress_callback=lambda tag, counter: progress_callback.emit(
                                    tag, counter
                                ),
                            )

            def complete_success(result):
                self._dialogCopyProgress.progressBar.setValue(len(source_tags))
                self._dialogCopyProgress.labelCopy.setText("Extraction Completed!")
                self._dialogCopyProgress.textExtractionLog.append(
                    "Extraction finished successfuly!"
                )
                self.on_remove_selected_tags(all=True)

            def complete_error(result):
                self._dialogCopyProgress.labelCopy.setText("Extraction Failed!")
                self._dialogCopyProgress.textExtractionLog.append(
                    "Extraction Failed!\n\r"
                )
                self._dialogCopyProgress.textExtractionLog.append(str(result[0]))
                self._dialogCopyProgress.textExtractionLog.append(str(result[1]))
                self._dialogCopyProgress.textExtractionLog.append(str(result[2]))

            def worker_complete():
                self._api.delete_connection(dest_conn_name)

                with open(f"{file_path}.log", "w") as writer:
                    writer.write(
                        self._dialogCopyProgress.textExtractionLog.toPlainText()
                    )

                self._dialogCopyProgress.labelFrom.setText("")
                self._dialogCopyProgress.labelTo.setText("")
                self._dialogCopyProgress.buttonBox.button(
                    QDialogButtonBox.Cancel
                ).setText("Close")
                self._dialogCopyProgress.buttonBox.button(
                    QDialogButtonBox.Cancel
                ).setEnabled(True)

            worker = Worker(copy_process_run)
            worker.signals.progress.connect(update_progress)
            worker.signals.result.connect(complete_success)
            worker.signals.error.connect(complete_error)
            worker.signals.finished.connect(worker_complete)

            self.threadpool.start(worker)

        except Exception as e:
            QMessageBox.critical(self._w, self._w.windowTitle(), str(e))

    def _mark_selected_tags(self):
        selected_tags = self._get_selected_tags()

        font_deselected = QtGui.QFont()
        font_deselected.setBold(False)

        font_selected = QtGui.QFont()
        font_selected.setBold(True)

        for i in range(0, self._w.treeLeftTagHierarchy.topLevelItemCount()):
            item = self._w.treeLeftTagHierarchy.topLevelItem(i)

            tag_name = item.data(0, QtCore.Qt.UserRole)
            for i in range(item.columnCount()):
                item.setFont(
                    i, font_selected if tag_name in selected_tags else font_deselected
                )

    # Dynamic tree expansion
    @QtCore.Slot(QTreeWidgetItem)
    def on_tree_expanded(self, clicked_item):
        conn_name = self._current_connection["name"]
        display_attributes = OrderedDict(self._current_connection["default_attributes"])

        tag = clicked_item.data(1, QtCore.Qt.UserRole)
        if tag["HasChildren"]:
            # Reload children
            for i in reversed(range(clicked_item.childCount())):
                clicked_item.removeChild(clicked_item.child(i))

            children = self._api.list_tags(
                conn_name,
                filter=tag["Name"],
                include_attributes=True,
                max_results=MAX_TAGS_TO_LOAD,
            )

            for i, child_name in enumerate(children):
                row = [
                    str(children[child_name][key])
                    if key in children[child_name]
                    else ""
                    for j, key in enumerate(display_attributes.keys())
                ]

                child_item = QTreeWidgetItem(row)
                child_item.setData(0, QtCore.Qt.UserRole, (child_name))
                child_item.setData(1, QtCore.Qt.UserRole, (children[child_name]))

                clicked_item.addChild(child_item)

    @QtCore.Slot()
    def on_tree_selection_changed(self):
        total_items = self._w.treeLeftTagHierarchy.topLevelItemCount()
        selected_items = len(self._w.treeLeftTagHierarchy.selectedItems())
        too_many_tags_msg = (
            " (Too Many Tags to Display - Narrow Your Search)"
            if total_items >= MAX_TAGS_TO_LOAD
            else ""
        )
        self._w.labelLeftPanelStatus.setText(
            f"{selected_items} / {total_items} tags {too_many_tags_msg}"
            if selected_items > 0
            else f"{total_items} tags {too_many_tags_msg}"
        )

    @QtCore.Slot()
    def on_refresh_tags_tree(self, filter):
        try:
            conn_name = self._current_connection["name"]
            display_attributes = OrderedDict(
                self._current_connection["default_attributes"]
            )

            # Prepare headers
            self._w.treeLeftTagHierarchy.clear()
            self._w.treeLeftTagHierarchy.setColumnCount(len(display_attributes))
            self._w.treeLeftTagHierarchy.setHeaderLabels(
                [a["Name"] for a in display_attributes.values()]
            )

            # Update items
            tags = self._api.list_tags(
                conn_name,
                filter=filter,
                include_attributes=list(display_attributes.keys()),
                max_results=MAX_TAGS_TO_LOAD,
            )

            # Update top level rows
            for i, tag_name in enumerate(tags):
                row = [
                    str(tags[tag_name][key]) if key in tags[tag_name] else ""
                    for j, key in enumerate(display_attributes.keys())
                ]

                item = QTreeWidgetItem(row)
                item.setData(0, QtCore.Qt.UserRole, (tag_name))
                item.setData(1, QtCore.Qt.UserRole, (tags[tag_name]))

                if tags[tag_name]["HasChildren"]:
                    item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

                self._w.treeLeftTagHierarchy.addTopLevelItem(item)

            self._mark_selected_tags()

            # If filter is a list of tags - we need to show which tags were not found
            if isinstance(filter, list):
                lower_exist = [s.lower() for s in tags.keys()]
                missing_tags = [s for s in filter if s.lower() not in lower_exist]

                self._show_msg_box(
                    f"Cannot find {len(missing_tags)} tag(s): {', '.join(missing_tags)}"[
                        :2000
                    ],
                    icon=QMessageBox.Icon.Warning,
                )

            self.on_tree_selection_changed()

        except Exception as e:
            mb = QMessageBox(self._w)
            # mb.setIcon(QMessageBox.Icon.Error)
            mb.setWindowTitle(self._w.windowTitle())
            mb.setText(f"Error retrieving tags: {str(e)}")
            mb.exec_()

    @QtCore.Slot(str)
    def on_tags_file_select(self):
        filename, filter = QFileDialog.getOpenFileName(
            parent=self._w,
            caption="Select Tags File",
            dir=".",
            # filter='*.xls, *.xlsx, *.xlsm, *.xlsb, *.odf, *.ods, *.odt')
            filter="*.xlsx",
        )
        if not filename:
            return

        try:
            df = pd.read_excel(filename, header=None)
            df = df.dropna()
            tags_to_find = df.iloc[:, 0].tolist()

            self.on_refresh_tags_tree(filter=tags_to_find)
            self._w.comboLeftTagFilter.clear()

        except Exception as e:
            mb = QMessageBox(self._w)
            # mb.setIcon(QMessageBox.Icon.Error)
            mb.setWindowTitle(self._w.windowTitle())
            mb.setText(f"Error reading excel file: {str(e)}")
            mb.exec_()

    def _refresh_connections(self):
        """ """
        self._w.comboLeftConnection.clear()

        self._existing_connections = self._api.list_connections()

        for conn in [
            conn
            for conn in self._existing_connections
            if conn["category"] == "historian"
        ]:
            self._w.comboLeftConnection.addItem(
                self._connection_title(conn["name"], conn["type"]), conn
            )

        self._w.comboLeftConnection.addItem("-- Add New Connection... --", "add_new")

        # Deselect last item
        if self._w.comboLeftConnection.count() == 1:
            self._w.comboLeftConnection.setCurrentIndex(-1)

    def _enable_current_connection(self):
        self._w.buttonLeftConnect.hide()
        current_conn = self._w.comboLeftConnection.currentData()
        try:
            print(f"Enabling connection '{current_conn['name']}'...")
            self._api.enable_connection(current_conn["name"])
            conn_info = self._api.connection_info(current_conn["name"])
            current_conn["enabled"] = True
            self._w.comboLeftConnection.setItemData(
                self._w.comboLeftConnection.currentIndex(), current_conn
            )
            self._refresh_current_connection_view(current_conn, conn_info)
        except Exception as e:
            self._refresh_current_connection_view(current_conn)
            mb = QMessageBox(self._w)
            mb.setIcon(QMessageBox.Icon.Information)
            mb.setWindowTitle(self._w.windowTitle())
            mb.setText(f"Error connecting to '{current_conn['name']}' - {str(e)}")
            mb.exec_()

    class FilterWidgetEventInspector(QtCore.QObject):
        def eventFilter(self, obj, event):
            if event.type() == QtCore.QEvent.FocusOut:
                if obj.currentText().strip() == "":
                    obj.setCurrentText(TAGS_FILTER_DEFAULT_PLACEHOLDER)

            elif event.type() == QtCore.QEvent.FocusIn:
                if obj.currentText().strip() == TAGS_FILTER_DEFAULT_PLACEHOLDER:
                    obj.setCurrentText("")

            return QtCore.QObject.eventFilter(self, obj, event)

    _filterWidgetEventInspector = FilterWidgetEventInspector()

    def _refresh_current_connection_view(self, current_conn, conn_info=None):
        self._w.buttonLeftConnect.hide()
        self._w.labelLeftConnectionDetails.setText("")
        self._w.treeLeftTagHierarchy.clear()
        self._w.labelLeftPanelStatus.clear()

        if not current_conn:
            return

        if not current_conn["enabled"]:
            self._w.labelLeftConnectionDetails.setText("Connection disabled.")
            self._w.buttonLeftConnect.show()
            return

        if conn_info is None:
            return

        self._w.labelLeftConnectionDetails.setText(conn_info["OneLiner"])

        # - Filters configuration -
        self._w.comboLeftTagFilter.setCurrentText(TAGS_FILTER_DEFAULT_PLACEHOLDER)

        if "name" in current_conn["supported_filters"]:
            self._w.comboLeftTagFilter.show()
        else:
            self._w.comboLeftTagFilter.hide()

        if "tags_file" in current_conn["supported_filters"]:
            self._w.buttonLeftTagsFileSelect.show()
        else:
            self._w.buttonLeftTagsFileSelect.hide()

        # Selection dates
        if "time" in current_conn["supported_filters"]:
            # now = QtCore.QDateTime.currentDateTime()
            end_time = QtCore.QDateTime.currentDateTimeUtc()
            start_time = end_time.addDays(-30)
            self._w.dateTimeLeftFrom.setDateTime(start_time)
            self._w.dateTimeLeftTo.setDateTime(end_time)
            self._w.widgetLeftTimeFilter.show()

        else:
            self._w.widgetLeftTimeFilter.hide()

        # Tag tree
        # self.on_refresh_tags_tree(filter=filter)

    def setup(self):
        self._w.setWindowTitle(f"{WINDOW_DEFAULT_TITLE} - v{__version__}")

        # Connection list
        self._refresh_connections()

        self._w.comboLeftConnection.currentTextChanged.connect(
            self.on_connection_change
        )

        self._w.buttonLeftConnect.clicked.connect(self._enable_current_connection)

        self.on_connection_change()

        # Menu Bar
        self._w.actionAddNewConnection.triggered.connect(self.on_create_new_connection)
        self._w.actionManageConnections.triggered.connect(self.on_manage_connections)

        # Display

        self._w.comboLeftTagFilter.textActivated.connect(self.on_refresh_tags_tree)
        self._w.comboLeftTagFilter.installEventFilter(self._filterWidgetEventInspector)

        self._w.treeLeftTagHierarchy.itemExpanded.connect(self.on_tree_expanded)
        self._w.treeLeftTagHierarchy.itemSelectionChanged.connect(
            self.on_tree_selection_changed
        )

        self._w.treeSelectedTags.itemSelectionChanged.connect(
            self.on_selected_tags_change
        )

        # Controls
        self._w.buttonLeftView.clicked.connect(lambda: self.on_view_tags(left=True))
        # shortcut_view = QtGui.QShortcut(QtGui.QKeySequence("F3"), self._w)
        # shortcut_view.activated.connect(self.on_view_tags)
        self._w.buttonRightView.clicked.connect(lambda: self.on_view_tags(left=False))

        self._w.buttonLeftTagsFileSelect.clicked.connect(self.on_tags_file_select)

        self._w.buttonAddSelectedTags.clicked.connect(self.on_add_selected_tags)

        self._w.buttonRemoveAllSelected.clicked.connect(
            lambda: self.on_remove_selected_tags(all=True)
        )
        self._w.buttonRemoveSelected.clicked.connect(
            lambda: self.on_remove_selected_tags(all=False)
        )

        self._w.buttonCopy.clicked.connect(self.on_copy_tags)
        shortcut_copy = QtGui.QShortcut(QtGui.QKeySequence("F5"), self._w)
        shortcut_copy.activated.connect(self.on_copy_tags)

        def on_directory_select():
            selected_dir = QFileDialog.getExistingDirectory(
                self._w, "Select Archive Folder"
            )
            if not selected_dir:
                return

            ind = self._w.comboArchiveDirectory.findText(selected_dir)
            if ind == -1:
                self._w.comboArchiveDirectory.insertItem(0, selected_dir)
                ind = 0
            self._w.comboArchiveDirectory.setCurrentIndex(ind)

        for conn in [
            conn
            for conn in self._existing_connections
            if conn["category"] != "historian"
        ]:
            self._w.comboArchiveDirectory.addItem(conn["name"])
        self._w.buttonSelectArchiveFile.clicked.connect(on_directory_select)

        # Refresh
        # shortcutRefresh = QtGui.QShortcut(QtGui.QKeySequence('Ctrl+r'), self._w)
        # shortcutRefresh.activated.connect(QtWidgets.QApplication.instance().quit)

        # Exit
        self._w.buttonExit.clicked.connect(QtWidgets.QApplication.instance().quit)
        shortcut_quit = QtGui.QShortcut(QtGui.QKeySequence("Alt+F4"), self._w)
        shortcut_quit.activated.connect(QtWidgets.QApplication.instance().quit)

    def show(self):
        self._w.show()
