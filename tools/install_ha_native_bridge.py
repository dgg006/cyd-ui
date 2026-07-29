"""Instala en Home Assistant el puente nativo temporal de CYD UI.

Convierte config/backend-map.json en dos automatizaciones:
- acciones táctiles del panel -> servicios de Home Assistant;
- estados de Home Assistant -> acción ESPHome update_control.

No sustituye al backend definitivo, pero permite una prueba doméstica completa
sin ejecutar ha_bridge.py ni un broker MQTT propio en la PC de desarrollo.
"""

import argparse
import json
from pathlib import Path

from ha_bridge import ha_request, read_ha_access


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_MAP_PATH = PROJECT_ROOT / "config" / "backend-map.json"
COMMAND_AUTOMATION_ID = "cyd_ui_native_commands"
STATE_AUTOMATION_ID = "cyd_ui_native_state_sync"


def load_controls():
    document = json.loads(BACKEND_MAP_PATH.read_text(encoding="utf-8"))
    return document["controls"]


def state_expr(entity_id):
    return f"states('{entity_id}')"


def unavailable_template(mapping):
    entity_id = mapping["entity_id"]
    base = f"{state_expr(entity_id)} in ['unknown', 'unavailable']"
    if attribute := mapping.get("attribute"):
        return f"{{{{ {base} or state_attr('{entity_id}', '{attribute}') is none }}}}"
    return f"{{{{ {base} }}}}"


def active_template(mapping):
    entity_id = mapping["entity_id"]
    if mapping.get("attribute") or mapping.get("value_only") and mapping.get("domain") != "binary_sensor":
        return False
    if mapping.get("state_active"):
        return f"{{{{ {state_expr(entity_id)} not in ['off', 'unknown', 'unavailable'] }}}}"
    return f"{{{{ {state_expr(entity_id)} == 'on' }}}}"


def value_template(mapping):
    entity_id = mapping["entity_id"]
    if attribute := mapping.get("attribute"):
        source = f"state_attr('{entity_id}', '{attribute}')"
    elif mapping.get("value_only"):
        source = state_expr(entity_id)
    else:
        return ""

    if value_map := mapping.get("value_map"):
        encoded = json.dumps(value_map, ensure_ascii=False)
        return f"{{{{ {encoded}.get({source}, {source}) }}}}"

    if "decimals" in mapping:
        decimals = int(mapping["decimals"])
        return (
            f"{{% set value = {source} %}}"
            f"{{{{ '' if value is none else ('%.{decimals}f' | format(value | float)) }}}}"
        )
    return f"{{{{ {source} }}}}"


def update_action(control_id, mapping):
    return {
        "action": "esphome.cyd_ui_update_control",
        "data": {
            "control_id": control_id,
            "active": active_template(mapping),
            "value": value_template(mapping),
            "reliability": (
                "{{ 'unavailable' if "
                + unavailable_template(mapping)[3:-3]
                + " else 'valid' }}"
            ),
        },
    }


def command_sequence(mapping):
    entity_id = mapping["entity_id"]
    domain = mapping.get("domain", entity_id.split(".", 1)[0])
    service = mapping.get("service", mapping["action"])

    if service == "set_temperature":
        delta = float(mapping["temperature_delta"])
        return [{
            "action": "climate.set_temperature",
            "target": {"entity_id": entity_id},
            "data": {
                "temperature": (
                    "{{ (state_attr('"
                    + entity_id
                    + "', 'temperature') | float(0) + "
                    + str(delta)
                    + ") | round(1) }}"
                )
            },
        }]

    if service == "set_cover_position":
        delta = float(mapping["position_delta"])
        return [{
            "action": "cover.set_cover_position",
            "target": {"entity_id": entity_id},
            "data": {
                "position": (
                    "{{ [[state_attr('"
                    + entity_id
                    + "', 'current_position') | float(0) + "
                    + str(delta)
                    + ", 0] | max, 100] | min | round(0) }}"
                )
            },
        }]

    return [{
        "action": f"{domain}.{service}",
        "target": {"entity_id": entity_id},
        "data": {},
    }]


def build_command_automation(controls):
    choices = []
    for control_id, mapping in controls.items():
        if not mapping.get("allow_control") or not mapping.get("entity_id"):
            continue
        action = mapping.get("action")
        if not action:
            continue
        choices.append({
            "conditions": [{
                "condition": "template",
                "value_template": (
                    "{{ trigger.event.data.control_id == '"
                    + control_id
                    + "' and trigger.event.data.action == '"
                    + action
                    + "' }}"
                ),
            }],
            "sequence": command_sequence(mapping),
        })

    return {
        "id": COMMAND_AUTOMATION_ID,
        "alias": "CYD UI - Ejecutar controles",
        "description": (
            "Puente nativo temporal. Ejecuta únicamente controles permitidos "
            "por backend-map.json; no habilita el encendido del calefactor."
        ),
        "triggers": [{"trigger": "event", "event_type": "esphome.cyd_ui_action"}],
        "conditions": [],
        "actions": [{"choose": choices}],
        "mode": "queued",
        "max": 10,
    }


def build_state_automation(controls):
    mapped = {
        control_id: mapping
        for control_id, mapping in controls.items()
        if mapping.get("entity_id") and mapping.get("publish_state") is not False
    }
    entity_ids = sorted({mapping["entity_id"] for mapping in mapped.values()})
    return {
        "id": STATE_AUTOMATION_ID,
        "alias": "CYD UI - Sincronizar estados",
        "description": (
            "Envía a la CYD los estados del mapa actual mediante la API nativa de ESPHome."
        ),
        "triggers": [
            {"trigger": "homeassistant", "event": "start"},
            {"trigger": "time_pattern", "minutes": "/1"},
            {"trigger": "state", "entity_id": entity_ids},
        ],
        "conditions": [{
            "condition": "template",
            "value_template": "{{ has_service('esphome', 'cyd_ui_update_control') }}",
        }],
        "actions": [
            update_action(control_id, mapping)
            for control_id, mapping in mapped.items()
        ],
        "mode": "restart",
    }


def install_automation(base_url, token, automation_id, config):
    return ha_request(
        base_url,
        token,
        f"/api/config/automation/config/{automation_id}",
        method="POST",
        payload=config,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install",
        action="store_true",
        help="Guarda las automatizaciones en Home Assistant. Sin esta opción solo muestra el resultado.",
    )
    args = parser.parse_args()

    controls = load_controls()
    automations = {
        COMMAND_AUTOMATION_ID: build_command_automation(controls),
        STATE_AUTOMATION_ID: build_state_automation(controls),
    }

    if not args.install:
        print(json.dumps(automations, ensure_ascii=False, indent=2))
        return

    base_url, token = read_ha_access()
    for automation_id, config in automations.items():
        install_automation(base_url, token, automation_id, config)
        print(f"Instalada: {config['alias']}")
    ha_request(base_url, token, "/api/services/automation/reload", method="POST", payload={})
    print("Automatizaciones recargadas.")


if __name__ == "__main__":
    main()
