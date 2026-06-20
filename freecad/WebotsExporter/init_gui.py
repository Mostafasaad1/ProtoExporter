import os
import FreeCADGui


class WebotsExporterWorkbench(FreeCADGui.Workbench):
    MenuText = "Webots Exporter"
    ToolTip = "Export FreeCAD assemblies to Webots simulation files"
    Icon = os.path.join(os.path.dirname(__file__), "webots_exporter", "gui", "resources", "icon.svg")

    def Initialize(self) -> None:
        from .webots_exporter.commands import ExportToWebotsCommand, MotorSensorMappingCommand
        self.appendToolbar("Webots Export", ["ExportToWebots", "MotorSensorMapping"])
        self.appendMenu("Webots Export", ["ExportToWebots", "MotorSensorMapping"])

    def Activated(self) -> None:
        pass

    def Deactivated(self) -> None:
        pass


FreeCADGui.addWorkbench(WebotsExporterWorkbench())
