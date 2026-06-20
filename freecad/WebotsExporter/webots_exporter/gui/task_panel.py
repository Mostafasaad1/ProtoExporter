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
            
        import FreeCAD
        import FreeCADGui
        selection = FreeCADGui.Selection.getSelection()
        has_assembly_sel = False
        for obj in selection:
            if obj.TypeId in ("Assembly::Assembly", "Assembly::AssemblyObject"):
                has_assembly_sel = True
                break
            curr = obj
            while hasattr(curr, "getParentGroup") and curr.getParentGroup() is not None:
                parent = curr.getParentGroup()
                if parent.TypeId in ("Assembly::Assembly", "Assembly::AssemblyObject"):
                    has_assembly_sel = True
                    break
                curr = parent
            if has_assembly_sel:
                break
                
        if not has_assembly_sel:
            doc = FreeCAD.ActiveDocument
            has_any_assembly = False
            if doc is not None:
                for obj in doc.Objects:
                    if obj.TypeId in ("Assembly::Assembly", "Assembly::AssemblyObject"):
                        has_any_assembly = True
                        break
            if not has_any_assembly:
                QtWidgets.QMessageBox.critical(
                    self.form,
                    "No Assembly Found",
                    "No Assembly exists in the active document to export."
                )
                return False
                
            reply = QtWidgets.QMessageBox.question(
                self.form,
                "No Selection",
                "No Assembly is selected. Do you want to export the first Assembly found in the document?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return False

        from ..exporter import WebotsExporter
        from pathlib import Path
        
        output_dir = Path(directory)
        exporter = WebotsExporter(
            output_dir=output_dir,
            collision_strategy=strategy,
        )
        try:
            doc = FreeCAD.ActiveDocument
            result = exporter.run(doc)
            QtWidgets.QMessageBox.information(
                self.form,
                "Export Complete",
                f"Assembly exported to:\n{result}",
            )
            return True
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.form,
                "Export Failed",
                f"An error occurred during export:\n{e}",
            )
            return False

    def reject(self) -> None:
        import FreeCADGui
        FreeCADGui.Control.closeDialog()

    def getStandardButtons(self) -> int:
        ok = QtWidgets.QDialogButtonBox.Ok
        cancel = QtWidgets.QDialogButtonBox.Cancel
        ok_val = ok.value if hasattr(ok, "value") else int(ok)
        cancel_val = cancel.value if hasattr(cancel, "value") else int(cancel)
        return ok_val | cancel_val
