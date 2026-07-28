import json
import re

from esphome import automation
import esphome.codegen as cg
from esphome.components import http_request, time
import esphome.config_validation as cv
from esphome.components.lvgl import defines as lvgl_defines
from esphome.core import CORE
from esphome.const import CONF_ID, CONF_TIME_ID

DEPENDENCIES = ["lvgl", "http_request"]
AUTO_LOAD = ["json"]

ui_engine_ns = cg.esphome_ns.namespace("ui_engine")
UiEngineComponent = ui_engine_ns.class_("UiEngineComponent", cg.Component)
ReloadAction = ui_engine_ns.class_("ReloadAction", automation.Action)
CONF_CONFIG_FILE = "config_file"
CONF_ON_ACTION = "on_action"
CONF_ON_NAVIGATION = "on_navigation"
CONF_CONFIG_URL = "config_url"
CONF_HTTP_REQUEST_ID = "http_request_id"
CONF_SCREENSAVER_TIMEOUT = "screensaver_timeout"
COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate_ui_document(document):
    if not isinstance(document, dict):
        raise cv.Invalid("la raiz debe ser un objeto")
    if document.get("schema_version") != 1:
        raise cv.Invalid("schema_version debe ser 1")

    pages = document.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= 8:
        raise cv.Invalid("pages debe contener entre 1 y 8 paginas")

    ids = set()
    screensaver_count = 0
    for page_index, page in enumerate(pages):
        page_prefix = f"pages[{page_index}]"
        if not isinstance(page, dict):
            raise cv.Invalid(f"{page_prefix} debe ser un objeto")
        template = page.get("template")
        if template not in ("button_grid", "climate", "clock_weather"):
            raise cv.Invalid(f"{page_prefix}.template no esta registrado")
        variant = page.get("variant")
        capacities = {"two_buttons": 2, "four_buttons": 4, "six_buttons": 6}
        if template == "button_grid" and variant not in capacities:
            raise cv.Invalid(f"{page_prefix}.variant no es valida para button_grid")
        if template == "climate" and variant != "thermostat":
            raise cv.Invalid(f"{page_prefix}.variant debe ser thermostat")
        if template == "clock_weather" and variant != "screensaver":
            raise cv.Invalid(f"{page_prefix}.variant debe ser screensaver")
        is_screensaver = page.get("screensaver", False)
        if not isinstance(is_screensaver, bool):
            raise cv.Invalid(f"{page_prefix}.screensaver debe ser booleano")
        if is_screensaver:
            screensaver_count += 1
            if template != "clock_weather":
                raise cv.Invalid(f"{page_prefix}.screensaver requiere clock_weather")
        if not isinstance(page.get("title"), str) or not page["title"].strip():
            raise cv.Invalid(f"{page_prefix}.title es obligatorio")

        controls = page.get("controls")
        maximum = capacities[variant] if template == "button_grid" else (5 if template == "climate" else 3)
        if not isinstance(controls, list) or not 1 <= len(controls) <= maximum:
            raise cv.Invalid(f"{page_prefix}.controls no es valido para {variant}")

        roles = set()

        for control_index, control in enumerate(controls):
            prefix = f"{page_prefix}.controls[{control_index}]"
            if not isinstance(control, dict):
                raise cv.Invalid(f"{prefix} debe ser un objeto")
            control_type = control.get("type")
            if template == "button_grid" and control_type != "button":
                raise cv.Invalid(f"{prefix}.type debe ser button")
            if template == "climate" and control_type not in ("button", "value"):
                raise cv.Invalid(f"{prefix}.type debe ser button o value")
            if template == "clock_weather" and control_type != "value":
                raise cv.Invalid(f"{prefix}.type debe ser value")
            control_id = control.get("id")
            if not isinstance(control_id, str) or not control_id.strip():
                raise cv.Invalid(f"{prefix}.id es obligatorio")
            if control_id in ids:
                raise cv.Invalid(f"id de control duplicado: {control_id}")
            ids.add(control_id)
            if not isinstance(control.get("caption"), str) or not control["caption"].strip():
                raise cv.Invalid(f"{prefix}.caption es obligatorio")
            if not isinstance(control.get("color"), str) or not COLOR_PATTERN.fullmatch(control["color"]):
                raise cv.Invalid(f"{prefix}.color debe tener formato #RRGGBB")
            if "meta" in control and not isinstance(control["meta"], dict):
                raise cv.Invalid(f"{prefix}.meta debe ser un objeto")
            if template == "climate":
                role = control.get("role")
                if role not in ("current_temperature", "target_temperature", "decrease", "power", "increase"):
                    raise cv.Invalid(f"{prefix}.role no es valido para climate")
                roles.add(role)
            elif template == "clock_weather":
                role = control.get("role")
                if role not in ("condition", "outside_temperature", "humidity"):
                    raise cv.Invalid(f"{prefix}.role no es valido para clock_weather")
                roles.add(role)

        if template == "climate" and roles != {
            "current_temperature", "target_temperature", "decrease", "power", "increase"
        }:
            raise cv.Invalid(f"{page_prefix} requiere los cinco roles de climate")
        if template == "clock_weather" and roles != {"condition", "outside_temperature", "humidity"}:
            raise cv.Invalid(f"{page_prefix} requiere los tres roles de clock_weather")

    if screensaver_count > 1:
        raise cv.Invalid("solo puede existir una pagina screensaver")

    return document


def validate_config_file(value):
    lvgl_defines.get_lv_fonts_used().update({"montserrat_32", "montserrat_48"})
    value = cv.file_(value)
    path = CORE.relative_config_path(value)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise cv.Invalid(f"JSON de ui_engine invalido: {error}") from error
    try:
        validate_ui_document(document)
    except cv.Invalid as error:
        raise cv.Invalid(f"JSON de ui_engine invalido: {error}") from error
    return value

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(UiEngineComponent),
        cv.Required(CONF_CONFIG_FILE): validate_config_file,
        cv.Optional(CONF_CONFIG_URL): cv.url,
        cv.Optional(CONF_HTTP_REQUEST_ID): cv.use_id(http_request.HttpRequestComponent),
        cv.Required(CONF_TIME_ID): cv.use_id(time.RealTimeClock),
        cv.Optional(CONF_SCREENSAVER_TIMEOUT, default="2min"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_ON_ACTION): automation.validate_automation(single=True),
        cv.Optional(CONF_ON_NAVIGATION): automation.validate_automation(single=True),
    }
).extend(cv.COMPONENT_SCHEMA)


def validate_http_options(config):
    has_url = CONF_CONFIG_URL in config
    has_client = CONF_HTTP_REQUEST_ID in config
    if has_url != has_client:
        raise cv.Invalid("config_url y http_request_id deben configurarse juntos")
    return config


CONFIG_SCHEMA = cv.All(CONFIG_SCHEMA, validate_http_options)


async def to_code(config):
    lvgl_defines.add_define("LV_USE_LABEL")
    lvgl_defines.add_define("LV_USE_BUTTON")
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    clock = await cg.get_variable(config[CONF_TIME_ID])
    cg.add(var.set_clock(clock))
    cg.add(var.set_screensaver_timeout(config[CONF_SCREENSAVER_TIMEOUT].total_milliseconds))
    config_path = CORE.relative_config_path(config[CONF_CONFIG_FILE])
    cg.add(var.set_initial_config(config_path.read_text(encoding="utf-8")))
    if CONF_CONFIG_URL in config:
        http_client = await cg.get_variable(config[CONF_HTTP_REQUEST_ID])
        cg.add(var.set_http_config(http_client, config[CONF_CONFIG_URL]))
    if on_action_config := config.get(CONF_ON_ACTION):
        await automation.build_automation(
            var.get_action_trigger(),
            [(cg.std_string, "control_id"), (cg.std_string, "action")],
            on_action_config,
        )
    if on_navigation_config := config.get(CONF_ON_NAVIGATION):
        await automation.build_automation(
            var.get_navigation_trigger(),
            [(cg.int_, "page_index")],
            on_navigation_config,
        )


@automation.register_action(
    "ui_engine.reload",
    ReloadAction,
    cv.Schema({cv.Required(CONF_ID): cv.use_id(UiEngineComponent)}),
    synchronous=True,
)
async def reload_action_to_code(config, action_id, template_arg, args):
    action = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(action, config[CONF_ID])
    return action
