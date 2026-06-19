from pathlib import Path
from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    from PySide import QtGui as QtWidgets

COLLISION_OPTIONS = ["Auto", "Primitives Only", "Decimated Mesh Only"]


class ExportOptions:
    def __init__(self, output_dir: str = "", collision_strategy: str = "Auto"):
        self.output_dir = output_dir
        self.collision_strategy = collision_strategy


class ExportWorker(QtCore.QThread):
    finished = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, exporter, doc):
        super().__init__()
        self._exporter = exporter
        self._doc = doc

    def run(self):
        try:
            result = self._exporter.run(self._doc)
            self.finished.emit(str(result))
        except Exception as e:
            self.error.emit(str(e))


class ExportTaskPanel:
    def __init__(self):
        self.form = QtWidgets.QWidget()
        self._worker = None
        layout = QtWidgets.QVBoxLayout(self.form)

        self._output_path = QtWidgets.QLineEdit("")
        self._browse_btn = QtWidgets.QPushButton("Browse...")
        self._collision_combo = QtWidgets.QComboBox()
        self._collision_combo.addItems(COLLISION_OPTIONS)

        layout.addWidget(QtWidgets.QLabel("Output Directory:"))
        dir_layout = QtWidgets.QHBoxLayout()
        dir_layout.addWidget(self._output_path)
        dir_layout.addWidget(self._browse_btn)
        layout.addLayout(dir_layout)

        layout.addWidget(QtWidgets.QLabel("Collision Strategy:"))
        layout.addWidget(self._collision_combo)

        self._browse_btn.clicked.connect(self._on_browse)
        self.options = ExportOptions()

    def _on_browse(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self.form, "Select Output Directory"
        )
        if directory:
            self._output_path.setText(directory)

    def accept(self) -> bool:
        directory = self._output_path.text()
        strategy = self._collision_combo.currentText()
        if not directory:
            QtWidgets.QMessageBox.warning(
                self.form, "Warning", "Please select an output directory."
            )
            return False
        self.options = ExportOptions(
            output_dir=directory, collision_strategy=strategy
        )
        return True

    def reject(self) -> None:
        pass

    def get_standard_buttons(self) -> int:
        return int(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
