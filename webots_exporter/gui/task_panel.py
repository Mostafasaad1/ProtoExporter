from pathlib import Path
try:
    from PySide import QtCore, QtGui
    try:
        from PySide import QtWidgets
    except ImportError:
        from PySide import QtGui as QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        try:
            from PySide6 import QtCore, QtGui, QtWidgets
        except ImportError:
            from unittest.mock import MagicMock
            QtCore = MagicMock()
            QtGui = MagicMock()
            QtWidgets = MagicMock()

COLLISION_OPTIONS = ["Auto", "Primitives Only", "Decimated Mesh Only", "Convex Hull"]


class ExportOptions:
    def __init__(
        self,
        output_dir: str = "",
        collision_strategy: str = "Auto",
        visual_quality_pct: float = 50.0,
        custom_description: str = "",
        doc_url: str = "",
        license: str = "",
    ):
        self.output_dir = output_dir
        self.collision_strategy = collision_strategy
        self.visual_quality_pct = visual_quality_pct
        self.custom_description = custom_description
        self.doc_url = doc_url
        self.license = license


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

        # Base / Root part override selection
        self._root_combo = QtWidgets.QComboBox()
        self._root_combo.addItem("Auto (Inferred)")
        layout.addWidget(QtWidgets.QLabel("Base / Root Part:"))
        layout.addWidget(self._root_combo)

        # Visual quality slider selection
        layout.addWidget(QtWidgets.QLabel("Mesh Visual Quality:"))
        self._quality_layout = QtWidgets.QHBoxLayout()
        self._quality_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._quality_slider.setRange(1, 100)
        self._quality_slider.setValue(50)
        self._quality_label = QtWidgets.QLabel("Visual Quality: 50%")
        self._quality_layout.addWidget(self._quality_slider)
        self._quality_layout.addWidget(self._quality_label)
        layout.addLayout(self._quality_layout)
        self._quality_slider.valueChanged.connect(self._on_quality_changed)

        # Controller Protocol selection
        layout.addWidget(QtWidgets.QLabel("Controller Protocol:"))
        self._protocol_combo = QtWidgets.QComboBox()
        self._protocol_combo.addItems([
            "None", "TCP Socket", "ROS 2", "Modbus TCP", "OPC UA Client", "Python GUI"
        ])
        layout.addWidget(self._protocol_combo)

        # Container for protocol specific configs
        self._protocol_config_widget = QtWidgets.QWidget()
        self._protocol_config_layout = QtWidgets.QFormLayout(self._protocol_config_widget)
        self._protocol_config_layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(self._protocol_config_widget)
        
        self._modbus_ip_input = QtWidgets.QLineEdit("0.0.0.0")
        self._modbus_port_input = QtWidgets.QLineEdit("502")

        self._opcua_server_input = QtWidgets.QLineEdit("opc.tcp://127.0.0.1:4840")
        self._opcua_csv_path = QtWidgets.QLineEdit("")
        self._opcua_csv_btn = QtWidgets.QPushButton("Browse...")
        
        self._opcua_csv_container = QtWidgets.QWidget()
        opcua_csv_lay = QtWidgets.QHBoxLayout(self._opcua_csv_container)
        opcua_csv_lay.setContentsMargins(0, 0, 0, 0)
        opcua_csv_lay.addWidget(self._opcua_csv_path)
        opcua_csv_lay.addWidget(self._opcua_csv_btn)

        self._opcua_csv_btn.clicked.connect(self._on_browse_csv)
        self._protocol_combo.currentIndexChanged.connect(self._on_protocol_changed)
        self._protocol_config_widget.hide()

        # Advanced Settings section
        self._adv_toggle_btn = QtWidgets.QPushButton("▶ Advanced Settings")
        self._adv_toggle_btn.setCheckable(True)
        self._adv_toggle_btn.setChecked(False)
        self._adv_toggle_btn.setStyleSheet("text-align: left; font-weight: bold;")
        
        self._adv_widget = QtWidgets.QWidget()
        adv_layout = QtWidgets.QFormLayout(self._adv_widget)
        adv_layout.setContentsMargins(5, 5, 5, 5)

        self._license_input = QtWidgets.QLineEdit("")
        self._license_input.setPlaceholderText("e.g. Apache 2.0")

        self._doc_url_input = QtWidgets.QLineEdit("")
        self._doc_url_input.setPlaceholderText("https://...")

        self._desc_input = QtWidgets.QTextEdit("")
        self._desc_input.setPlaceholderText("Custom description for PROTO header...")
        self._desc_input.setMaximumHeight(70)

        adv_layout.addRow("License:", self._license_input)
        adv_layout.addRow("Documentation URL:", self._doc_url_input)
        adv_layout.addRow("Custom Description:", self._desc_input)

        self._adv_widget.hide()
        self._adv_toggle_btn.clicked.connect(self._toggle_advanced_settings)

        layout.addWidget(self._adv_toggle_btn)
        layout.addWidget(self._adv_widget)

        # Warning label
        self._warning_label = QtWidgets.QLabel("")
        self._warning_label.setStyleSheet("color: red;")
        self._warning_label.setWordWrap(True)
        self._warning_label.hide()
        layout.addWidget(self._warning_label)

        # Joint motors & sensors mapping section
        layout.addWidget(QtWidgets.QLabel("Joint Motors & Sensors Configuration:"))
        
        btn_layout = QtWidgets.QHBoxLayout()
        self._btn_all_actuated = QtWidgets.QPushButton("Select All Actuators")
        self._btn_all_sensed = QtWidgets.QPushButton("Select All Sensors")
        btn_layout.addWidget(self._btn_all_actuated)
        btn_layout.addWidget(self._btn_all_sensed)
        layout.addLayout(btn_layout)

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
        self._btn_all_actuated.clicked.connect(self._select_all_actuated)
        self._btn_all_sensed.clicked.connect(self._select_all_sensed)
        self.options = ExportOptions()
        self._joints = []
        
        # Populate joint table
        self._populate_joints()

    def _on_quality_changed(self, value: int) -> None:
        self._quality_label.setText(f"Visual Quality: {value}%")

    def _toggle_advanced_settings(self, checked: bool) -> None:
        if checked:
            self._adv_toggle_btn.setText("▼ Advanced Settings")
            self._adv_widget.show()
        else:
            self._adv_toggle_btn.setText("▶ Advanced Settings")
            self._adv_widget.hide()

    def _on_protocol_changed(self, index: int) -> None:
        # Clear existing rows in QFormLayout
        while self._protocol_config_layout.count() > 0:
            item = self._protocol_config_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        self._warning_label.hide()
        self._warning_label.setText("")

        protocol_name = self._protocol_combo.currentText()
        if protocol_name == "Modbus TCP":
            self._protocol_config_layout.addRow("Modbus Bind IP:", self._modbus_ip_input)
            self._protocol_config_layout.addRow("Modbus Bind Port:", self._modbus_port_input)
            self._protocol_config_widget.show()
        elif protocol_name == "OPC UA Client":
            self._protocol_config_layout.addRow("OPC UA Server URI:", self._opcua_server_input)
            self._protocol_config_layout.addRow("OPC UA CSV Node Map:", self._opcua_csv_container)
            self._protocol_config_widget.show()
            # If a CSV path is already loaded, re-validate it
            if self._opcua_csv_path.text():
                self._validate_csv(self._opcua_csv_path.text())
        else:
            self._protocol_config_widget.hide()

    def _on_browse_csv(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.form, "Select OPC UA CSV Node Map", "", "CSV Files (*.csv)"
        )
        if file_path:
            self._opcua_csv_path.setText(file_path)
            self._validate_csv(file_path)

    def _validate_csv(self, file_path: str) -> list[str]:
        import csv
        warnings = []
        if not file_path or not Path(file_path).exists():
            return warnings
        
        # Get active joints list
        joint_labels = [getattr(j, "Label", getattr(j, "Name", "")) for j in self._joints]
        
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None) # Skip header row
                for row_idx, row in enumerate(reader, start=1):
                    if not row:
                        continue
                    if len(row) < 2:
                        warnings.append(f"Row {row_idx+1}: Invalid row format (must have at least 2 columns).")
                        continue
                        
                    # opcua.py expects: joint_name, [type], node_id
                    joint_name = row[0].strip()
                    
                    if joint_name not in joint_labels:
                        warnings.append(f"Row {row_idx+1}: Joint '{joint_name}' not found in the assembly.")
        except Exception as e:
            warnings.append(f"Error reading CSV: {e}")
        
        if warnings:
            warning_text = "OPC UA CSV Node Map Warnings:\n" + "\n".join(warnings)
            self._warning_label.setText(warning_text)
            self._warning_label.show()
        else:
            self._warning_label.setText("")
            self._warning_label.hide()
            
        return warnings

    def _populate_joints(self) -> None:
        import FreeCAD
        doc = FreeCAD.ActiveDocument
        if not doc:
            return
            
        # Populate Root Part dropdown
        try:
            from ..exporter import WebotsExporter
            from pathlib import Path
            temp_exporter = WebotsExporter(output_dir=Path("/tmp"))
            parts = temp_exporter._collect_parts(doc)
            curr_selection = self._root_combo.currentText()
            self._root_combo.clear()
            self._root_combo.addItem("Auto (Inferred)")
            for p in parts:
                lbl = getattr(p, "Label", getattr(p, "Name", ""))
                if lbl:
                    self._root_combo.addItem(lbl)
            idx = self._root_combo.findText(curr_selection)
            if idx >= 0:
                self._root_combo.setCurrentIndex(idx)
        except Exception:
            pass

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

    def _select_all_actuated(self) -> None:
        self._set_all_checkboxes(1, True)

    def _select_all_sensed(self) -> None:
        self._set_all_checkboxes(2, True)

    def _set_all_checkboxes(self, col: int, state: bool) -> None:
        for i in range(self.table.rowCount()):
            widget = self.table.cellWidget(i, col)
            if widget:
                cb = widget.layout().itemAt(0).widget()
                if isinstance(cb, QtWidgets.QCheckBox):
                    cb.setChecked(state)

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
        target_assembly = None
        for obj in selection:
            if obj.TypeId in ("Assembly::Assembly", "Assembly::AssemblyObject"):
                has_assembly_sel = True
                target_assembly = obj
                break
            curr = obj
            while hasattr(curr, "getParentGroup") and curr.getParentGroup() is not None:
                parent = curr.getParentGroup()
                if parent.TypeId in ("Assembly::Assembly", "Assembly::AssemblyObject"):
                    has_assembly_sel = True
                    target_assembly = parent
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
                        target_assembly = obj
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

        from ..exporter import WebotsExporter, sanitize_name
        from pathlib import Path
        
        world_name = "assembly_export"
        if target_assembly is not None:
            raw_name = getattr(target_assembly, "Label", getattr(target_assembly, "Name", "assembly_export"))
            world_name = sanitize_name(raw_name)
        
        output_dir = Path(directory) / world_name
        
        # Ensure the directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        quality_pct = self._quality_slider.value()

        # Get protocol choice
        protocol_str = self._protocol_combo.currentText()
        from ..datamodel import ControllerProtocol, ProtocolConfig
        
        protocol_map = {
            "None": ControllerProtocol.NONE,
            "TCP Socket": ControllerProtocol.TCP_SOCKET,
            "ROS 2": ControllerProtocol.ROS2,
            "Modbus TCP": ControllerProtocol.MODBUS_TCP,
            "OPC UA Client": ControllerProtocol.OPC_UA,
            "Python GUI": ControllerProtocol.PYTHON_GUI,
        }
        protocol = protocol_map.get(protocol_str, ControllerProtocol.NONE)
        
        # Build ProtocolConfig
        modbus_port = 502
        try:
            modbus_port = int(self._modbus_port_input.text().strip())
        except ValueError:
            pass
            
        protocol_config = ProtocolConfig(
            protocol=protocol,
            modbus_ip=self._modbus_ip_input.text().strip(),
            modbus_port=modbus_port,
            opcua_server=self._opcua_server_input.text().strip(),
            opcua_csv_path=self._opcua_csv_path.text().strip()
        )

        # Run OPC UA CSV validation if selected
        if protocol == ControllerProtocol.OPC_UA:
            csv_path = protocol_config.opcua_csv_path
            if not csv_path:
                QtWidgets.QMessageBox.warning(
                    self.form, "Warning", "Please select an OPC UA CSV Node Map file."
                )
                return False
            self._validate_csv(csv_path)

        root_choice = self._root_combo.currentText()
        override_root = None if root_choice.startswith("Auto") else root_choice

        custom_desc = self._desc_input.toPlainText().strip()
        doc_url = self._doc_url_input.text().strip()
        license_str = self._license_input.text().strip()

        self.options = ExportOptions(
            output_dir=str(output_dir),
            collision_strategy=strategy,
            visual_quality_pct=float(quality_pct),
            custom_description=custom_desc,
            doc_url=doc_url,
            license=license_str,
        )

        exporter = WebotsExporter(
            output_dir=output_dir,
            world_name=world_name,
            collision_strategy=strategy,
            visual_quality_pct=float(quality_pct),
            protocol_config=protocol_config,
            override_root=override_root,
            custom_description=custom_desc,
            doc_url=doc_url,
            license=license_str,
        )
        try:
            doc = FreeCAD.ActiveDocument
            result = exporter.run(doc)
            
            msg = f"Assembly exported to:\n{result}"
            if protocol != ControllerProtocol.NONE:
                notice = exporter.get_dependency_notice()
                if notice:
                    msg += f"\n\nRequired dependencies:\n{notice}"
                else:
                    msg += "\n\nNo extra dependencies required."
            
            QtWidgets.QMessageBox.information(
                self.form,
                "Export Complete",
                msg,
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
