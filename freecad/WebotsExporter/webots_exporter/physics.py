import re
from typing import Any, Optional
from .datamodel import WbPhysics, WbVec3
from .exceptions import PhysicsError
from .datamodel import WBT_SCALE


def parse_density_value(val: Any) -> Optional[float]:
    if val is None:
        return None
    if hasattr(val, "Value"):
        try:
            if hasattr(val, "getValueAs"):
                try:
                    return float(val.getValueAs("kg/m³"))
                except Exception:
                    pass
            return float(val.Value)
        except Exception:
            pass
    try:
        val_str = str(val).strip()
        match = re.match(r"^([\d\.\+\-eE]+)\s*(.*)$", val_str)
        if match:
            num = float(match.group(1))
            unit = match.group(2).lower()
            if "g/cm" in unit or "g/mm" in unit:
                return num * 1000.0
            elif "kg/m" in unit:
                return num
            elif "kg/dm" in unit:
                return num * 1000.0
            return num
    except Exception:
        pass
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def get_material_density(fc_part: Any) -> Optional[float]:
    material = getattr(fc_part, "Material", None)
    if not material and hasattr(fc_part, "LinkedObject") and fc_part.LinkedObject:
        material = getattr(fc_part.LinkedObject, "Material", None)
        
    if material is None:
        return None
        
    # 1. Direct attribute
    for attr in ["Density", "density"]:
        if hasattr(material, attr):
            val = getattr(material, attr)
            if val is not None:
                parsed = parse_density_value(val)
                if parsed is not None:
                    return parsed
                
    # 2. Mechanical.Density
    if hasattr(material, "Mechanical"):
        mech = material.Mechanical
        if mech is not None:
            for attr in ["Density", "density"]:
                if hasattr(mech, attr):
                    val = getattr(mech, attr)
                    if val is not None:
                        parsed = parse_density_value(val)
                        if parsed is not None:
                            return parsed
                        
    # 3. Card dictionary/property
    if hasattr(material, "Card"):
        card = material.Card
        if isinstance(card, dict):
            for key in ["Density", "density"]:
                if key in card:
                    parsed = parse_density_value(card[key])
                    if parsed is not None:
                        return parsed
        elif card is not None:
            for attr in ["Density", "density"]:
                if hasattr(card, attr):
                    val = getattr(card, attr)
                    if val is not None:
                        parsed = parse_density_value(val)
                        if parsed is not None:
                            return parsed
                        
    # 4. Dictionary interface
    if isinstance(material, dict):
        for key in ["Density", "density"]:
            if key in material:
                parsed = parse_density_value(material[key])
                if parsed is not None:
                    return parsed
                
    # 5. Case-insensitive attribute search
    try:
        for attr in dir(material):
            if "density" in attr.lower():
                val = getattr(material, attr)
                parsed = parse_density_value(val)
                if parsed is not None:
                    return parsed
    except Exception:
        pass
        
    return None


class PhysicsCalculator:
    def compute(self, fc_part: Any, fc_shape: Any) -> Optional[WbPhysics]:
        mass = getattr(fc_shape, "Mass", None)
        volume = getattr(fc_shape, "Volume", None)
        com = getattr(fc_shape, "CenterOfMass", None)

        mass_val = None
        if mass is not None:
            try:
                mass_val = float(mass)
            except (TypeError, ValueError):
                pass

        if mass_val is None:
            if volume is not None:
                try:
                    vol_val = float(volume)
                    density_kg_m3 = get_material_density(fc_part)
                    if density_kg_m3 is None:
                        density_kg_m3 = 1000.0
                    mass_val = vol_val * 1e-9 * density_kg_m3
                except (TypeError, ValueError):
                    mass_val = 1.0
            else:
                mass_val = 1.0
        else:
            # Try to get density from Material
            density_kg_m3 = get_material_density(fc_part)
            
            if density_kg_m3 is not None and volume is not None:
                try:
                    vol_val = float(volume)
                    # mass = volume (in mm³) * 1e-9 (to m³) * density (in kg/m³)
                    mass_val = vol_val * 1e-9 * density_kg_m3
                except (TypeError, ValueError):
                    pass
            elif volume is not None:
                # Fallback to mass == volume check (unconfigured density heuristic)
                try:
                    vol_val = float(volume)
                    if vol_val > 0 and abs(mass_val - vol_val) / vol_val < 1e-4:
                        mass_val *= 1e-6
                except (TypeError, ValueError):
                    pass

        if mass_val <= 0.0:
            mass_val = 1e-4

        com_vec = WbVec3()
        if com is not None:
            try:
                com_vec = WbVec3.from_mm(float(com.x), float(com.y), float(com.z))
            except (AttributeError, TypeError, ValueError):
                pass

        return WbPhysics(mass=mass_val, center_of_mass=com_vec, density=-1.0)
