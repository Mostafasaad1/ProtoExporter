import os
import FreeCADGui


class WebotsExporterWorkbench(FreeCADGui.Workbench):
    MenuText = "Webots Exporter"
    ToolTip = "Export FreeCAD assemblies to Webots simulation files"

    def __init__(self) -> None:
        dir_path = os.path.dirname(__file__) if "__file__" in globals() else ""
        self.__class__.Icon = os.path.join(dir_path, "webots_exporter", "gui", "resources", "icon.svg")

    def Initialize(self) -> None:
        from webots_exporter.commands import ExportToWebotsCommand
        self.appendToolbar("Webots Export", ["ExportToWebots"])
        self.appendMenu("Webots Export", ["ExportToWebots"])

    def Activated(self) -> None:
        pass

    def Deactivated(self) -> None:
        pass


FreeCADGui.addWorkbench(WebotsExporterWorkbench())

