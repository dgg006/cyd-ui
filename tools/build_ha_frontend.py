"""Build the Home Assistant editor assets from the proven local configurator."""

from __future__ import annotations

import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "configurator" / "static"
TARGET = ROOT / "custom_components" / "cyd_ui" / "frontend"


API_IMPLEMENTATION = '''async function api(path,options={}){
  const body=options.body?JSON.parse(options.body):{};
  if(path==="/api/catalog")return fetch("/cyd_ui_static/catalog.json").then(r=>r.json());
  if(path==="/api/icons")return fetch("/cyd_ui_static/icons.json").then(r=>r.json()).then(icons=>({icons}));
  if(path==="/api/project"){
    const project=await hass.callWS({type:"cyd_ui/config/get"});
    if(!project.ui)throw new Error("Todavía no hay un proyecto importado.");
    return {ui:project.ui,backend_map:project.backend_map};
  }
  if(path==="/api/entities")return hass.callWS({type:"cyd_ui/entities/list"});
  if(path==="/api/validate")return hass.callWS({type:"cyd_ui/config/validate",ui:body.ui,backend_map:body.backend_map});
  if(path==="/api/save"){
    const result=await hass.callWS({type:"cyd_ui/config/save",ui:body.ui,backend_map:body.backend_map});
    return {...result,backup:`revisión ${result.revision}`,delivery_note:result.device_applied?"Aplicado directamente en la pantalla.":"Entrega pendiente o realizada por el puente remoto."};
  }
  if(path==="/api/device-status")return hass.callWS({type:"cyd_ui/device/status"});
  if(path==="/api/test-sound")return hass.callWS({type:"cyd_ui/sound/preview",volume:Number(body.volume)});
  if(path==="/api/reminder/send")return hass.callWS({type:"cyd_ui/reminder/send",reminder_id:body.reminder_id,title:body.title,message:body.message,level:body.level,sound:body.sound===true});
  if(path==="/api/reminder/dismiss")return hass.callWS({type:"cyd_ui/reminder/dismiss",reminder_id:body.reminder_id||""});
  if(path==="/api/touch-calibration/start")return hass.callWS({type:"cyd_ui/touch_calibration/start"});
  if(path==="/api/reload")return hass.callWS({type:"cyd_ui/device/reload"});
  throw new Error("Esta acción estará disponible al conectar el panel directamente con la CYD.");
}'''


def build() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    source_js = (SOURCE / "app.js").read_text(encoding="utf-8")
    old_api_start = "async function api(path,options={}){"
    api_start = source_js.index(old_api_start)
    api_end = source_js.index("\n", api_start)
    source_js = source_js[:api_start] + API_IMPLEMENTATION + source_js[api_end:]
    source_js = source_js.replace(
        'saveButton.textContent="Guardar y aplicar"',
        'saveButton.textContent="Guardar en Home Assistant"',
    )
    wrapper = '''export function startCydUiEditor(root,hass){
const document={
  querySelector:(selector)=>root.querySelector(selector),
  createElement:(tag)=>window.document.createElement(tag),
  get visibilityState(){return window.document.visibilityState;}
};
'''
    (TARGET / "editor-app.js").write_text(
        wrapper + source_js + "\nreturn ()=>stopLdrPolling();\n}\n", encoding="utf-8"
    )

    css = (SOURCE / "app.css").read_text(encoding="utf-8")
    css = css.replace(":root {", ":host {")
    css = css.replace(" body{", " :host{")
    css = css.replace(
        'url("/assets/materialdesignicons-webfont.ttf")',
        'url("/cyd_ui_static/materialdesignicons-webfont.ttf")',
    )
    (TARGET / "editor.css").write_text(css, encoding="utf-8")
    shutil.copyfile(
        ROOT / "fonts" / "materialdesignicons-webfont.ttf",
        TARGET / "materialdesignicons-webfont.ttf",
    )
    shutil.copyfile(ROOT / "components" / "ui_engine" / "icons.json", TARGET / "icons.json")

    catalog_source = (ROOT / "configurator" / "server.py").read_text(encoding="utf-8")
    # The catalog is intentionally duplicated as JSON for the browser bundle. A test
    # guards its template names against the local configurator.
    catalog = {
        "button_grid": {
            "label": "Botones",
            "variants": {"two_buttons": 2, "four_buttons": 4, "six_buttons": 6},
            "controls": {"kind": "repeated", "type": "button"},
        },
        "climate": {
            "label": "Climatización",
            "variants": {"thermostat": 5},
            "controls": {"kind": "fixed", "roles": [
                {"role": "current_temperature", "type": "value", "caption": "Actual"},
                {"role": "target_temperature", "type": "value", "caption": "Objetivo"},
                {"role": "decrease", "type": "button", "caption": "-", "action": "decrement"},
                {"role": "power", "type": "button", "caption": "Estado", "action": "toggle"},
                {"role": "increase", "type": "button", "caption": "+", "action": "increment"},
            ]},
        },
        "clock_weather": {
            "label": "Reloj y clima",
            "variants": {"screensaver": 3},
            "screensaver": True,
            "controls": {"kind": "fixed", "roles": [
                {"role": "condition", "type": "value", "caption": "Estado"},
                {"role": "outside_temperature", "type": "value", "caption": "Exterior"},
                {"role": "humidity", "type": "value", "caption": "Humedad"},
            ]},
        },
        "sensor_grid": {
            "label": "Sensores",
            "variants": {"four_values": 4},
            "controls": {"kind": "variable", "type": "value", "minimum": 1, "maximum": 4},
        },
        "cover": {
            "label": "Cortina",
            "variants": {"position_controls": 6},
            "controls": {"kind": "fixed", "roles": [
                {"role": "position", "type": "value", "caption": "Posición"},
                {"role": "state", "type": "value", "caption": "Estado"},
                {"role": "open", "type": "button", "caption": "Abrir todo", "action": "open"},
                {"role": "close", "type": "button", "caption": "Cerrar todo", "action": "close"},
                {"role": "close_step", "type": "button", "caption": "Cerrar 10%", "action": "close_step"},
                {"role": "open_step", "type": "button", "caption": "Abrir 10%", "action": "open_step"},
            ]},
        },
        "media": {
            "label": "Multimedia",
            "variants": {"full_controls": 10},
            "controls": {"kind": "fixed", "roles": [
                {"role": "player", "type": "value", "caption": "Reproductor"},
                {"role": "title", "type": "value", "caption": "Canción"},
                {"role": "artist", "type": "value", "caption": "Artista"},
                {"role": "station", "type": "value", "caption": "Emisora"},
                {"role": "volume", "type": "value", "caption": "Volumen"},
                {"role": "previous", "type": "button", "caption": "|<", "action": "previous"},
                {"role": "play_pause", "type": "button", "caption": "Play", "action": "play_pause"},
                {"role": "next", "type": "button", "caption": ">|", "action": "next"},
                {"role": "volume_down", "type": "button", "caption": "-", "action": "volume_down"},
                {"role": "volume_up", "type": "button", "caption": "+", "action": "volume_up"},
            ]},
        },
    }
    if not all(f'"{name}"' in catalog_source for name in catalog):
        raise RuntimeError("El catálogo del configurador cambió; actualizá este bundle.")
    (TARGET / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    initial_project = {
        "ui": json.loads((ROOT / "config" / "ui.json").read_text(encoding="utf-8")),
        "backend_map": json.loads(
            (ROOT / "config" / "backend-map.json").read_text(encoding="utf-8")
        ),
    }
    (TARGET / "initial-project.json").write_text(
        json.dumps(initial_project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
