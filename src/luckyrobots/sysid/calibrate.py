"""Apply identified parameters to MuJoCo XML models."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from .sysid import SysIdResult

logger = logging.getLogger("luckyrobots.sysid")


def apply_params(
    model_xml: str | Path,
    result: SysIdResult | str | Path,
    output_path: str | Path,
) -> Path:
    """Apply identified parameters to a MuJoCo XML model.

    Loads the XML, modifies attributes in-place using ElementTree,
    and writes the calibrated model to output_path.

    Args:
        model_xml: Path to original MuJoCo XML.
        result: SysIdResult or path to saved result JSON.
        output_path: Where to write the calibrated XML.

    Returns:
        Path to the written calibrated XML.
    """
    if isinstance(result, (str, Path)):
        result = SysIdResult.load(result)

    model_xml = Path(model_xml)
    output_path = Path(output_path)

    tree = ET.parse(model_xml)
    root = tree.getroot()

    for name, value in result.params.items():
        _apply_single_param(root, name, value)

    tree.write(str(output_path), xml_declaration=True)
    logger.info("Calibrated model written to %s", output_path)
    return output_path


def _apply_single_param(root: ET.Element, param_name: str, value: float) -> None:
    """Apply a single parameter change to an XML tree."""
    # Search joints
    for joint in root.iter("joint"):
        jname = joint.get("name", "")
        short = jname.replace("_joint", "")
        if param_name == f"{short}_armature":
            joint.set("armature", str(value))
            return
        if param_name == f"{short}_damping":
            joint.set("damping", str(value))
            return
        if param_name == f"{short}_frictionloss":
            joint.set("frictionloss", str(value))
            return

    # Search bodies
    for body in root.iter("body"):
        bname = body.get("name", "")
        if param_name == f"{bname}_mass":
            inertial = body.find("inertial")
            if inertial is not None:
                inertial.set("mass", str(value))
            return

    # Search geoms
    for geom in root.iter("geom"):
        gname = geom.get("name", "")
        if param_name == f"{gname}_friction":
            existing = geom.get("friction", "1 0.005 0.0001")
            parts = existing.split()
            parts[0] = str(value)
            geom.set("friction", " ".join(parts))
            return
