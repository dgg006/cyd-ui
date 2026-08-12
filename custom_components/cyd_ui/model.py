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
    "media": {"full_controls": (11, 11)},
}
IDLE_MODES = {"clock_weather", "screen_off", "dim", "none"}
ACCENTS = {"mint", "blue", "violet", "amber", "rose"}


def migrate_media_artwork(
    ui: dict[str, Any], backend_map: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Add the optional artwork source to media pages saved before v0.7."""
    next_ui = deepcopy(ui)
    next_backend_map = deepcopy(backend_map)
    mappings = next_backend_map.setdefault("controls", {})
    changed = False
    used_ids = {
        control.get("id")
        for page in next_ui.get("pages", [])
        if isinstance(page, dict)
        for control in page.get("controls", [])
        if isinstance(control, dict)
    }
    for page in next_ui.get("pages", []):
        if not isinstance(page, dict) or page.get("template") != "media":
            continue
        controls = page.get("controls")
        if not isinstance(controls, list) or any(
            isinstance(control, dict) and control.get("role") == "artwork"
            for control in controls
        ):
            continue
        player = next(
            (control for control in controls
             if isinstance(control, dict) and control.get("role") == "player"),
            None,
        )
        if not isinstance(player, dict):
            continue
        player_id = str(player.get("id", "media_player"))
        artwork_id = f"{player_id}_artwork"
        suffix = 2
        while artwork_id in used_ids:
            artwork_id = f"{player_id}_artwork_{suffix}"
            suffix += 1
        used_ids.add(artwork_id)
        artwork = {
            "type": "value",
            "id": artwork_id,
            "caption": "Carátula",
            "role": "artwork",
            "color": "#FFFFFF",
            "meta": {},
            "unit": "",
        }
        insert_at = next(
            (index for index, control in enumerate(controls)
             if isinstance(control, dict) and control.get("role") == "volume"),
            len(controls),
        )
        controls.insert(insert_at, artwork)
        player_mapping = mappings.get(player_id, {})
        mappings[artwork_id] = {
            "entity_id": player_mapping.get("entity_id", ""),
            "domain": "media_player",
            "attribute": "media_image_url",
            "media_selector_id": player_id,
        }
        changed = True
    return next_ui, next_backend_map, changed


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_time(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value):
        return False
    hour, minute = (int(part) for part in value.split(":"))
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _validate_settings(ui: dict[str, Any], errors: list[str]) -> None:
    settings = ui.get("settings", {})
    if not isinstance(settings, dict):
        errors.append("Configuración: settings debe ser un objeto.")
        return
    sections = {
        name: settings.get(name, {})
        for name in ("display", "appearance", "inactivity", "night", "sound", "touchscreen")
    }
    for name, section in sections.items():
        if not isinstance(section, dict):
            errors.append(f"Configuración: {name} debe ser un objeto.")
    if errors:
        return

    display = sections["display"]
    for key in ("brightness", "minimum_brightness", "maximum_brightness"):
        value = display.get(key)
        if not _is_int(value) or not 0 <= value <= 100:
            errors.append(f"Pantalla: {key} debe ser un entero entre 0 y 100.")
    if not isinstance(display.get("auto_brightness"), bool):
        errors.append("Pantalla: auto_brightness debe ser sí o no.")
    if all(_is_int(display.get(key)) for key in ("minimum_brightness", "maximum_brightness")):
        if display["minimum_brightness"] > display["maximum_brightness"]:
            errors.append("Pantalla: el brillo mínimo no puede superar el máximo.")
    for key in ("ldr_dark_voltage", "ldr_bright_voltage"):
        value = display.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 3.3:
            errors.append(f"Pantalla: {key} debe estar entre 0.0 y 3.3 V.")
    if display.get("ldr_dark_voltage") == display.get("ldr_bright_voltage"):
        errors.append("Pantalla: los extremos de calibración LDR deben ser distintos.")

    appearance = sections["appearance"]
    if appearance.get("mode") not in {"dark", "light"}:
        errors.append("Aspecto: el modo debe ser dark o light.")
    if appearance.get("accent") not in ACCENTS:
        errors.append("Aspecto: el color de acento no es válido.")

    inactivity = sections["inactivity"]
    timeout = inactivity.get("timeout")
    if not _is_int(timeout) or not 0 <= timeout <= 3600:
        errors.append("Inactividad: el tiempo debe estar entre 0 y 3600 segundos.")
    if inactivity.get("mode") not in IDLE_MODES:
        errors.append("Inactividad: el modo seleccionado no es válido.")
    dim = inactivity.get("dim_brightness")
    if not _is_int(dim) or not 0 <= dim <= 100:
        errors.append("Inactividad: el brillo tenue debe estar entre 0 y 100.")

    night = sections["night"]
    if not isinstance(night.get("enabled"), bool):
        errors.append("Horario nocturno: enabled debe ser sí o no.")
    for key in ("start", "end"):
        if not _valid_time(night.get(key)):
            errors.append(f"Horario nocturno: {key} debe usar HH:MM.")
    night_brightness = night.get("brightness")
    if not _is_int(night_brightness) or not 0 <= night_brightness <= 100:
        errors.append("Horario nocturno: el brillo debe estar entre 0 y 100.")
    if night.get("mode") not in IDLE_MODES:
        errors.append("Horario nocturno: el modo seleccionado no es válido.")

    sound = sections["sound"]
    for key in ("enabled", "touch", "navigation", "notifications", "mute_at_night"):
        if not isinstance(sound.get(key), bool):
            errors.append(f"Sonido: {key} debe ser sí o no.")
    for key in ("volume", "touch_volume", "navigation_volume", "notification_volume"):
        value = sound.get(key)
        if not _is_int(value) or not 0 <= value <= 10:
            errors.append(f"Sonido: {key} debe estar entre 0 y 10.")

    touch = sections["touchscreen"]
    for key in ("x_min", "x_max", "y_min", "y_max"):
        if not _is_int(touch.get(key)):
            errors.append(f"Pantalla táctil: {key} debe ser entero.")
    if all(_is_int(touch.get(key)) for key in ("x_min", "x_max", "y_min", "y_max")):
        if not (0 <= touch["x_min"] < touch["x_max"] <= 4095):
            errors.append("Pantalla táctil: el rango X no es válido.")
        if not (0 <= touch["y_min"] < touch["y_max"] <= 4095):
            errors.append("Pantalla táctil: el rango Y no es válido.")


def validate_document(ui: Any, backend_map: Any) -> list[str]:
    """Reject structurally unsafe documents before persistent storage."""
    errors: list[str] = []
    if not isinstance(ui, dict):
        return ["La interfaz debe ser un objeto."]
    if ui.get("schema_version") != 1:
        errors.append("schema_version debe ser 1.")

    timeout = ui.get("screensaver_timeout")
    if not _is_int(timeout) or not 0 <= timeout <= 3600:
        errors.append("El tiempo del protector debe estar entre 0 y 3600 segundos.")
    _validate_settings(ui, errors)

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
        if not isinstance(controls, list) or not 1 <= len(controls) <= 12:
            errors.append(f"Página {page_number}: debe tener entre 1 y 12 controles.")
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
        for extra_id in mapping.get("entity_ids", []):
            if not isinstance(extra_id, str) or not ENTITY_ID_PATTERN.fullmatch(extra_id):
                errors.append(f"Un reproductor de {control_id} no es un ID válido.")
        fallback_id = mapping.get("fallback_entity_id", "")
        if fallback_id and not ENTITY_ID_PATTERN.fullmatch(str(fallback_id)):
            errors.append(f"La fuente alternativa de {control_id} no es un ID válido.")

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
