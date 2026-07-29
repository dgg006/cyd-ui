"""Pure validation and revision helpers for CYD UI documents."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from .const import MAX_CONFIG_BYTES, MAX_HISTORY


CONTROL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


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
        if not isinstance(page.get("template"), str) or not page["template"]:
            errors.append(f"Página {page_number}: falta template.")
        if not isinstance(page.get("variant"), str) or not page["variant"]:
            errors.append(f"Página {page_number}: falta variant.")
        controls = page.get("controls")
        if not isinstance(controls, list) or not 1 <= len(controls) <= 6:
            errors.append(f"Página {page_number}: debe tener entre 1 y 6 controles.")
            continue
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

    unused_mappings = sorted(set(mappings) - control_ids)
    if unused_mappings:
        errors.append("Hay asociaciones sin control: " + ", ".join(unused_mappings))

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
    }
