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

        # Output folder selection
        self._output_path = QtWidgets.QLineEdit("")
        self._browse_btn = QtWidgets.QPushButton("Browse...")
        
        layout.addWidget(QtWidgets.QLabel("Output Directory:"))
        dir_layout = QtWidgets.QHBoxLayout()
        dir_layout.addWidget(self._output_path)
        dir_layout.addWidget(self._browse_btn)
        layout.addLayout(dir_layout)

        # Collision strategy selection
        self._collision_combo = QtWidgets.QComboBox()
        self._collision_combo.addItems(COLLISION_OPTIONS)
        layout.addWidget(QtWidgets.QLabel("Collision Strategy:"))
        layout.addWidget(self._collision_combo)

        # Joint motors & sensors mapping section
        layout.addWidget(QtWidgets.QLabel("Joint Motors & Sensors Configuration:"))

        # Table of joints
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Joint", "Actuated", "Sensed"])
        
        # Adjust section resize modes
        header = self.table.horizontalHeader()
        if hasattr(header, "setSectionResizeMode"):
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        else:
            header.setResizeMode(0, QtWidgets.QHeaderView.Stretch)
            
        layout.addWidget(self.table)

        self._browse_btn.clicked.connect(self._on_browse)
        self.options = ExportOptions()
        self._joints = []
        
        # Populate joint table
        self._populate_joints()

    def _populate_joints(self) -> None:
        import FreeCAD
        doc = FreeCAD.ActiveDocument
        if not doc:
            return
            
        joints = []
        for obj in doc.Objects:
            if obj.TypeId == "Assembly::JointGroup":
                continue
            if hasattr(obj, "Reference1") or hasattr(obj, "JointType") or obj.TypeId.startswith("Assembly::Joint"):
                joints.append(obj)
                
        self.table.setRowCount(len(joints))
        self._joints = joints
        
        for i, joint in enumerate(joints):
            # Joint Name/Label
            item_name = QtWidgets.QTableWidgetItem(joint.Label or joint.Name)
            item_name.setFlags(item_name.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 0, item_name)
            
            # Actuated checkbox widget
            act_widget = QtWidgets.QWidget()
            act_layout = QtWidgets.QHBoxLayout(act_widget)
            act_layout.setContentsMargins(0, 0, 0, 0)
            act_layout.setAlignment(QtCore.Qt.AlignCenter)
            act_cb = QtWidgets.QCheckBox()
            
            # Read current property value if exists
            val_act = False
            if hasattr(joint, "WebotsActuated"):
                val_act = bool(joint.WebotsActuated)
            elif hasattr(joint, "Actuated"):
                val_act = bool(joint.Actuated)
            act_cb.setChecked(val_act)
            
            act_layout.addWidget(act_cb)
            self.table.setCellWidget(i, 1, act_widget)
            
            # Sensed checkbox widget
            sens_widget = QtWidgets.QWidget()
            sens_layout = QtWidgets.QHBoxLayout(sens_widget)
            sens_layout.setContentsMargins(0, 0, 0, 0)
            sens_layout.setAlignment(QtCore.Qt.AlignCenter)
            sens_cb = QtWidgets.QCheckBox()
            
            val_sens = False
            if hasattr(joint, "WebotsSensed"):
                val_sens = bool(joint.WebotsSensed)
            elif hasattr(joint, "Sensed"):
                val_sens = bool(joint.Sensed)
            sens_cb.setChecked(val_sens)
            
            sens_layout.addWidget(sens_cb)
            self.table.setCellWidget(i, 2, sens_widget)

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

        # Apply motor & sensor mappings to the joints from the checkboxes
        for i, joint in enumerate(self._joints):
            act_widget = self.table.cellWidget(i, 1)
            sens_widget = self.table.cellWidget(i, 2)
            
            if act_widget and sens_widget:
                act_cb = act_widget.layout().itemAt(0).widget()
                sens_cb = sens_widget.layout().itemAt(0).widget()
                
                act_val = act_cb.isChecked()
                sens_val = sens_cb.isChecked()
                
                # Check / inject properties
                if not hasattr(joint, "WebotsActuated"):
                    try:
                        joint.addProperty("App::PropertyBool", "WebotsActuated", "Webots")
                    except Exception:
                        pass
                if hasattr(joint, "WebotsActuated"):
                    joint.WebotsActuated = act_val
                elif hasattr(joint, "Actuated"):
                    joint.Actuated = act_val
                    
                if not hasattr(joint, "WebotsSensed"):
                    try:
                        joint.addProperty("App::PropertyBool", "WebotsSensed", "Webots")
                    except Exception:
                        pass
                if hasattr(joint, "WebotsSensed"):
                    joint.WebotsSensed = sens_val
                elif hasattr(joint, "Sensed"):
                    joint.Sensed = sens_val

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
