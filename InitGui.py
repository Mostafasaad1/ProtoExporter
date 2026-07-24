import os
import FreeCAD
import FreeCADGui


def _get_mod_path():
    """Return the absolute path to this addon's directory, safely."""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    for mod_dir in [
        os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "WebotsExporter"),
        os.path.join(FreeCAD.getResourceDir(), "Mod", "WebotsExporter"),
    ]:
        if os.path.isdir(mod_dir):
            return mod_dir
    return ""


class WebotsExporterWorkbench(FreeCADGui.Workbench):
    MenuText = "Webots Exporter"
    ToolTip = "Export FreeCAD assemblies to Webots simulation files"
    # Icon MUST be set before FreeCADGui.addWorkbench() is called.
    # We cannot use module-level globals inside the class body when
    # FreeCAD exec's this file, so we set Icon as a plain string literal
    # resolved just below the class definition.

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        from webots_exporter.commands import ExportToWebotsCommand
        self.appendToolbar("Webots Export", ["ExportToWebots"])
        self.appendMenu("Webots Export", ["ExportToWebots"])

    def Activated(self):
        pass

    def Deactivated(self):
        pass


# Set Icon after the class is defined so module-level _get_mod_path() is accessible.
WebotsExporterWorkbench.Icon = os.path.join(
    _get_mod_path(), "webots_exporter", "gui", "resources", "icon.svg"
)

FreeCADGui.addWorkbench(WebotsExporterWorkbench())

