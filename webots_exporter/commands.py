import os
import FreeCAD
import FreeCADGui
try:
    from PySide import QtWidgets
except ImportError:
    from PySide import QtGui as QtWidgets
from pathlib import Path

from .exporter import WebotsExporter
from .gui.task_panel import ExportTaskPanel


class ExportToWebotsCommand:
    def GetResources(self) -> dict[str, str]:
        icon_path = os.path.join(os.path.dirname(__file__), "gui", "resources", "icon.svg")
        return {
            "Pixmap": icon_path,
            "MenuText": "Export to Webots...",
            "ToolTip": "Export the active Assembly to a Webots .wbt simulation file",
        }

    def IsActive(self) -> bool:
        doc = FreeCAD.ActiveDocument
        if doc is None:
            return False
        return True

    def Activated(self) -> None:
        panel = ExportTaskPanel()
        FreeCADGui.Control.showDialog(panel)
        if panel.accept():
            opts = panel.options
            output_dir = Path(opts.output_dir)
            exporter = WebotsExporter(
                output_dir=output_dir,
                collision_strategy=opts.collision_strategy,
            )
            try:
                doc = FreeCAD.ActiveDocument
                result = exporter.run(doc)
                QtWidgets.QMessageBox.information(
                    None,
                    "Export Complete",
                    f"Assembly exported to:\n{result}",
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    None,
                    "Export Failed",
                    f"An error occurred during export:\n{e}",
                )


FreeCADGui.addCommand("ExportToWebots", ExportToWebotsCommand())
