from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


WBT_SCALE = 0.001


class JointType(Enum):
    HINGE = "Hinge"
    SLIDER = "Slider"
    BALL = "Ball"


class BoundingKind(Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    MESH = "mesh"


@dataclass
class WbVec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @staticmethod
    def from_mm(x_mm: float, y_mm: float, z_mm: float) -> WbVec3:
        return WbVec3(x_mm * WBT_SCALE, y_mm * WBT_SCALE, z_mm * WBT_SCALE)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class WbAxisAngle:
    x: float = 0.0
    y: float = 1.0
    z: float = 0.0
    angle: float = 0.0

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.z, self.angle)


@dataclass
class WbAppearance:
    diffuse_color: tuple[float, float, float] = (0.8, 0.8, 0.8)
    transparency: float = 0.0


@dataclass
class WbShapeGeometry:
    obj_relpath: str
    appearance: WbAppearance = field(default_factory=WbAppearance)


@dataclass
class WbBoundingObject:
    kind: BoundingKind = BoundingKind.BOX
    size: WbVec3 = field(default_factory=lambda: WbVec3(1, 1, 1))
    radius: float = 0.5
    height: float = 1.0
    local_offset: WbVec3 = field(default_factory=WbVec3)
    mesh_relpath: str = ""


@dataclass
class WbPhysics:
    mass: float = 1.0
    center_of_mass: WbVec3 = field(default_factory=WbVec3)
    density: float = -1.0


@dataclass
class WbJointNode:
    joint_type: JointType = JointType.HINGE
    anchor: WbVec3 = field(default_factory=WbVec3)
    axis: WbAxisAngle = field(default_factory=WbAxisAngle)
    min_stop: float = 0.0
    max_stop: float = 0.0
    child: Optional[WbSolidNode] = None


@dataclass
class WbSolidNode:
    name: str = "unnamed"
    translation: WbVec3 = field(default_factory=WbVec3)
    rotation: WbAxisAngle = field(default_factory=WbAxisAngle)
    geometries: list[WbShapeGeometry] = field(default_factory=list)
    bounding_object: Optional[WbBoundingObject] = None
    physics: Optional[WbPhysics] = None
    child_joints: list[WbJointNode] = field(default_factory=list)
    source_fc_names: list[str] = field(default_factory=list)
