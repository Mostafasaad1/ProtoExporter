from abc import ABC, abstractmethod
from webots_exporter.datamodel import ProtocolConfig

class BaseProtocolWriter(ABC):
    @abstractmethod
    def write(self, export_dir: str, robot_name: str, joints: list[str], config: ProtocolConfig, peripherals: list[tuple[str, str]] = None) -> None:
        """
        Generates the necessary files in export_dir/controllers/<robot_name>_ctrl/
        """
        pass

    @abstractmethod
    def get_dependency_notice(self, robot_name: str, controller_dir: str) -> str:
        """
        Returns the dependency notice or instructions.
        """
        pass
