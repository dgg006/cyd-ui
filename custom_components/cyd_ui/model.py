"""Pure validation and revision helpers for CYD UI documents."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from .const import MAX_CONFIG_BYTES, MAX_HISTORY


CONTROL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
ENTITY_ID_PATTERN = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
TEMPLATE_VARIANTS: dict[str, dict[str, tuple[int, int]]] = {
    "button_grid": {
        "two_buttons": (2, 2),
        "four_buttons": (4, 4),
        "six_buttons": (6, 6),
    },
    "climate": {"thermostat": (5, 5)},
    "clock_weather": {"screensaver": (3, 3)},
    "sensor_grid": {"four_values": (1, 4)},
    "cover": {"position_controls": (6, 6)},
}


def validate_document(ui: Any, backend_map: Any) -> list[str]:
    """Reject structurally unsafe documents before persistent storage."""
    errors: list[str] = []
    if not isinstance(ui, dict):
        return ["La interfaz debe ser un objeto."]
    if ui.get("schema_version") != 1:
        errors.append("schema_version debe ser 1.")

    pages = ui.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= 8:
        errors.append("Debe haber entre 1 y 8 páginas.")
        pages = []

    mappings = backend_map.get("controls") if isinstance(backend_map, dict) else None
    if not isinstance(mappings, dict):
        errors.append("El mapa de backend debe contener un objeto controls.")
        mappings = {}

    control_ids: set[str] = set()
    for page_number, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            errors.append(f"Página {page_number}: debe ser un objeto.")
            continue
        template = page.get("template")
        variant = page.get("variant")
        if not isinstance(template, str) or not template:
            errors.append(f"Página {page_number}: falta template.")
        elif template not in TEMPLATE_VARIANTS:
            errors.append(f"Página {page_number}: template desconocido.")
        if not isinstance(variant, str) or not variant:
            errors.append(f"Página {page_number}: falta variant.")
        elif template in TEMPLATE_VARIANTS and variant not in TEMPLATE_VARIANTS[template]:
            errors.append(f"Página {page_number}: variante desconocida.")
        controls = page.get("controls")
        if not isinstance(controls, list) or not 1 <= len(controls) <= 6:
            errors.append(f"Página {page_number}: debe tener entre 1 y 6 controles.")
            continue
        if template in TEMPLATE_VARIANTS and variant in TEMPLATE_VARIANTS[template]:
            minimum, maximum = TEMPLATE_VARIANTS[template][variant]
            if not minimum <= len(controls) <= maximum:
                errors.append(
                    f"Página {page_number}: la variante requiere entre {minimum} y {maximum} controles."
                )
        for control_number, control in enumerate(controls, start=1):
            if not isinstance(control, dict):
                errors.append(
                    f"Página {page_number}, control {control_number}: debe ser un objeto."
                )
                continue
            control_id = control.get("id")
            if not isinstance(control_id, str) or not CONTROL_ID_PATTERN.fullmatch(control_id):
                errors.append(
                    f"Página {page_number}, control {control_number}: ID inválido."
                )
            elif control_id in control_ids:
                errors.append(f"El control {control_id} está repetido.")
            else:
                control_ids.add(control_id)
            if control.get("type") not in {"button", "value"}:
                errors.append(
                    f"Página {page_number}, control {control_number}: tipo inválido."
                )
            if not isinstance(control.get("caption"), str) or not control["caption"].strip():
                errors.append(
                    f"Página {page_number}, control {control_number}: falta texto visible."
                )
            if not COLOR_PATTERN.fullmatch(str(control.get("color", ""))):
                errors.append(
                    f"Página {page_number}, control {control_number}: color inválido."
                )

    unused_mappings = sorted(set(mappings) - control_ids)
    if unused_mappings:
        errors.append("Hay asociaciones sin control: " + ", ".join(unused_mappings))
    for control_id in control_ids:
        mapping = mappings.get(control_id)
        if not isinstance(mapping, dict):
            continue
        entity_id = mapping.get("entity_id", "")
        if entity_id and not ENTITY_ID_PATTERN.fullmatch(str(entity_id)):
            errors.append(f"La entidad de {control_id} no es un ID válido.")

    try:
        encoded_size = len(
            json.dumps(
                {"ui": ui, "backend_map": backend_map},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    except (TypeError, ValueError):
        errors.append("La configuración contiene valores que no son JSON.")
    else:
        if encoded_size > MAX_CONFIG_BYTES:
            errors.append("La configuración supera el tamaño máximo permitido.")
    return errors


def create_revision(
    current: dict[str, Any], ui: dict[str, Any], backend_map: dict[str, Any], updated_at: str
) -> dict[str, Any]:
    """Build the next immutable storage revision and bounded history."""
    revision = int(current.get("revision", 0)) + 1
    history = list(current.get("history", []))
    if current.get("ui") is not None:
        history.append(
            {
                "revision": int(current.get("revision", 0)),
                "updated_at": current.get("updated_at"),
                "ui": deepcopy(current["ui"]),
                "backend_map": deepcopy(current.get("backend_map", {"controls": {}})),
            }
        )
    return {
        "revision": revision,
        "updated_at": updated_at,
        "ui": deepcopy(ui),
        "backend_map": deepcopy(backend_map),
        "history": history[-MAX_HISTORY:],
        "native_bridge_enabled": bool(current.get("native_bridge_enabled", False)),
        "temporary_automation_states": deepcopy(
            current.get("temporary_automation_states", {})
        ),
    }
