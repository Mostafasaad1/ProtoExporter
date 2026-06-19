import os
import sys
import FreeCADGui

# Add the workbench directory to sys.path to ensure webots_exporter is importable
wb_path = os.path.dirname(__file__)
if wb_path not in sys.path:
    sys.path.append(wb_path)


class WebotsExporterWorkbench(FreeCADGui.Workbench):
    MenuText = "Webots Exporter"
    ToolTip = "Export FreeCAD assemblies to Webots simulation files"
    Icon = os.path.join(wb_path, "webots_exporter", "gui", "resources", "icon.svg")

    def Initialize(self) -> None:
        from webots_exporter.commands import ExportToWebotsCommand
        self.appendToolbar("Webots Export", ["ExportToWebots"])
        self.appendMenu("Webots Export", ["ExportToWebots"])

    def Activated(self) -> None:
        pass

    def Deactivated(self) -> None:
        pass


FreeCADGui.addWorkbench(WebotsExporterWorkbench())
