import json
import re
from pathlib import Path

from esphome import automation
import esphome.codegen as cg
from esphome.components import font, http_request, output, rtttl, time, touchscreen
from esphome.components.touchscreen import CONF_TOUCHSCREEN_ID
import esphome.config_validation as cv
from esphome.components.lvgl import defines as lvgl_defines
from esphome.core import CORE
from esphome.const import CONF_ID, CONF_TIME_ID

DEPENDENCIES = ["lvgl", "http_request", "font", "output", "rtttl", "touchscreen"]
AUTO_LOAD = ["json"]

ui_engine_ns = cg.esphome_ns.namespace("ui_engine")
UiEngineComponent = ui_engine_ns.class_("UiEngineComponent", cg.Component)
ReloadAction = ui_engine_ns.class_("ReloadAction", automation.Action)
CONF_CONFIG_FILE = "config_file"
CONF_ON_ACTION = "on_action"
CONF_ON_NAVIGATION = "on_navigation"
CONF_ON_CALIBRATION = "on_calibration"
CONF_CONFIG_URL = "config_url"
CONF_HTTP_REQUEST_ID = "http_request_id"
CONF_SCREENSAVER_TIMEOUT = "screensaver_timeout"
CONF_ICON_FONT_ID = "icon_font_id"
CONF_BACKLIGHT_OUTPUT_ID = "backlight_output_id"
CONF_SOUND_ID = "sound_id"
COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
ICON_NAMES = {
    item["name"]
    for item in json.loads(Path(__file__).with_name("icons.json").read_text(encoding="utf-8"))
}

IDLE_MODES = {"clock_weather", "screen_off", "dim", "none"}
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def validate_device_settings(document):
    settings = document.get("settings")
    if settings is None:
        return
    if not isinstance(settings, dict):
        raise cv.Invalid("settings debe ser un objeto")

    display = settings.get("display", {})
    if not isinstance(display, dict):
        raise cv.Invalid("settings.display debe ser un objeto")
    for key in ("brightness", "minimum_brightness", "maximum_brightness"):
        value = display.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100):
            raise cv.Invalid(f"settings.display.{key} debe estar entre 0 y 100")
    minimum = display.get("minimum_brightness", 15)
    maximum = display.get("maximum_brightness", 100)
    if minimum > maximum:
        raise cv.Invalid("settings.display.minimum_brightness no puede superar maximum_brightness")
    if "auto_brightness" in display and not isinstance(display["auto_brightness"], bool):
        raise cv.Invalid("settings.display.auto_brightness debe ser booleano")
    dark = display.get("ldr_dark_voltage", 3.0)
    bright = display.get("ldr_bright_voltage", 0.2)
    if (not isinstance(dark, (int, float)) or isinstance(dark, bool) or
            not isinstance(bright, (int, float)) or isinstance(bright, bool) or
            not 0 <= dark <= 3.3 or not 0 <= bright <= 3.3 or dark == bright):
        raise cv.Invalid("la calibracion LDR debe usar valores distintos entre 0.0 y 3.3 V")

    appearance = settings.get("appearance", {})
    if not isinstance(appearance, dict):
        raise cv.Invalid("settings.appearance debe ser un objeto")
    if appearance.get("mode", "dark") not in {"dark", "light"}:
        raise cv.Invalid("settings.appearance.mode debe ser dark o light")
    if appearance.get("accent", "mint") not in {"mint", "blue", "violet", "amber", "rose"}:
        raise cv.Invalid("settings.appearance.accent no es valido")

    inactivity = settings.get("inactivity", {})
    if not isinstance(inactivity, dict):
        raise cv.Invalid("settings.inactivity debe ser un objeto")
    timeout = inactivity.get("timeout")
    if timeout is not None and (not isinstance(timeout, int) or isinstance(timeout, bool) or not 0 <= timeout <= 3600):
        raise cv.Invalid("settings.inactivity.timeout debe estar entre 0 y 3600")
    if inactivity.get("mode", "clock_weather") not in IDLE_MODES:
        raise cv.Invalid("settings.inactivity.mode no es valido")
    dim = inactivity.get("dim_brightness", 10)
    if not isinstance(dim, int) or isinstance(dim, bool) or not 0 <= dim <= 100:
        raise cv.Invalid("settings.inactivity.dim_brightness debe estar entre 0 y 100")

    night = settings.get("night", {})
    if not isinstance(night, dict):
        raise cv.Invalid("settings.night debe ser un objeto")
    if "enabled" in night and not isinstance(night["enabled"], bool):
        raise cv.Invalid("settings.night.enabled debe ser booleano")
    for key, default in (("start", "23:00"), ("end", "07:00")):
        if not isinstance(night.get(key, default), str) or not TIME_PATTERN.fullmatch(night.get(key, default)):
            raise cv.Invalid(f"settings.night.{key} debe usar HH:MM")
    night_brightness = night.get("brightness", 15)
    if not isinstance(night_brightness, int) or isinstance(night_brightness, bool) or not 0 <= night_brightness <= 100:
        raise cv.Invalid("settings.night.brightness debe estar entre 0 y 100")
    if night.get("mode", "screen_off") not in IDLE_MODES:
        raise cv.Invalid("settings.night.mode no es valido")

    sound = settings.get("sound", {})
    if not isinstance(sound, dict):
        raise cv.Invalid("settings.sound debe ser un objeto")
    for key in ("enabled", "touch", "navigation", "notifications", "mute_at_night"):
        if key in sound and not isinstance(sound[key], bool):
            raise cv.Invalid(f"settings.sound.{key} debe ser booleano")
    volume = sound.get("volume", 5)
    if not isinstance(volume, int) or isinstance(volume, bool) or not 0 <= volume <= 10:
        raise cv.Invalid("settings.sound.volume debe estar entre 0 y 10")
    for key in ("touch_volume", "navigation_volume", "notification_volume"):
        event_volume = sound.get(key, volume)
        if not isinstance(event_volume, int) or isinstance(event_volume, bool) or not 0 <= event_volume <= 10:
            raise cv.Invalid(f"settings.sound.{key} debe estar entre 0 y 10")

    touch = settings.get("touchscreen", {})
    if not isinstance(touch, dict):
        raise cv.Invalid("settings.touchscreen debe ser un objeto")
    values = {key: touch.get(key, default) for key, default in (
        ("x_min", 200), ("x_max", 3700), ("y_min", 240), ("y_max", 3800)
    )}
    for key, value in values.items():
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 4095:
            raise cv.Invalid(f"settings.touchscreen.{key} debe estar entre 0 y 4095")
    if values["x_min"] >= values["x_max"] or values["y_min"] >= values["y_max"]:
        raise cv.Invalid("settings.touchscreen requiere minimos menores que maximos")


def validate_icon_font(value):
    font_id = cv.use_id(font.Font)(value)
    lvgl_defines.add_lv_use("font")
    lvgl_defines.get_esphome_fonts_used().add(font_id)
    return cv.requires_component("font")(font_id)


def validate_ui_document(document):
    if not isinstance(document, dict):
        raise cv.Invalid("la raiz debe ser un objeto")
    if document.get("schema_version") != 1:
        raise cv.Invalid("schema_version debe ser 1")
    validate_device_settings(document)
    timeout = document.get("screensaver_timeout", 30)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 0 <= timeout <= 3600:
        raise cv.Invalid("screensaver_timeout debe estar entre 0 y 3600 segundos")

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
        if template not in ("button_grid", "climate", "clock_weather", "sensor_grid", "cover"):
            raise cv.Invalid(f"{page_prefix}.template no esta registrado")
        variant = page.get("variant")
        capacities = {"two_buttons": 2, "four_buttons": 4, "six_buttons": 6}
        if template == "button_grid" and variant not in capacities:
            raise cv.Invalid(f"{page_prefix}.variant no es valida para button_grid")
        if template == "climate" and variant != "thermostat":
            raise cv.Invalid(f"{page_prefix}.variant debe ser thermostat")
        if template == "clock_weather" and variant != "screensaver":
            raise cv.Invalid(f"{page_prefix}.variant debe ser screensaver")
        if template == "sensor_grid" and variant != "four_values":
            raise cv.Invalid(f"{page_prefix}.variant debe ser four_values")
        if template == "cover" and variant != "position_controls":
            raise cv.Invalid(f"{page_prefix}.variant debe ser position_controls")
        is_screensaver = page.get("screensaver", False)
        if not isinstance(is_screensaver, bool):
            raise cv.Invalid(f"{page_prefix}.screensaver debe ser booleano")
        if is_screensaver:
            screensaver_count += 1
            if template != "clock_weather":
                raise cv.Invalid(f"{page_prefix}.screensaver requiere clock_weather")
        title_optional = template == "clock_weather" and variant == "screensaver"
        if not isinstance(page.get("title", ""), str) or (not title_optional and not page["title"].strip()):
            raise cv.Invalid(f"{page_prefix}.title es obligatorio salvo en el screensaver")

        controls = page.get("controls")
        maximum = capacities[variant] if template == "button_grid" else (
            (6 if template == "cover" else 5) if template in ("climate", "cover") else (
                3 if template == "clock_weather" else 4
            )
        )
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
            if template == "sensor_grid" and control_type != "value":
                raise cv.Invalid(f"{prefix}.type debe ser value")
            if template == "cover" and control_type not in ("button", "value"):
                raise cv.Invalid(f"{prefix}.type debe ser button o value")
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
            if "unit" in control and not isinstance(control["unit"], str):
                raise cv.Invalid(f"{prefix}.unit debe ser texto")
            for icon_field in ("icon", "icon_on", "icon_off"):
                icon_name = control.get(icon_field, "")
                if not isinstance(icon_name, str) or (icon_name and icon_name not in ICON_NAMES):
                    raise cv.Invalid(f"{prefix}.{icon_field} no es un icono MDI admitido")
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
            elif template == "cover":
                role = control.get("role")
                if role not in ("position", "state", "open", "close", "close_step", "open_step"):
                    raise cv.Invalid(f"{prefix}.role no es valido para cover")
                roles.add(role)

        if template == "climate" and roles != {
            "current_temperature", "target_temperature", "decrease", "power", "increase"
        }:
            raise cv.Invalid(f"{page_prefix} requiere los cinco roles de climate")
        if template == "clock_weather" and roles != {"condition", "outside_temperature", "humidity"}:
            raise cv.Invalid(f"{page_prefix} requiere los tres roles de clock_weather")
        if template == "cover" and roles != {"position", "state", "open", "close", "close_step", "open_step"}:
            raise cv.Invalid(f"{page_prefix} requiere los seis roles de cover")

    if screensaver_count > 1:
        raise cv.Invalid("solo puede existir una pagina screensaver")

    return document


def validate_config_file(value):
    lvgl_defines.get_lv_fonts_used().update({"montserrat_20", "montserrat_32", "montserrat_48"})
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
        cv.Required(CONF_ICON_FONT_ID): validate_icon_font,
        cv.Required(CONF_BACKLIGHT_OUTPUT_ID): cv.use_id(output.FloatOutput),
        cv.Required(CONF_SOUND_ID): cv.use_id(rtttl.Rtttl),
        cv.Required(CONF_TOUCHSCREEN_ID): cv.use_id(touchscreen.Touchscreen),
        cv.Optional(CONF_SCREENSAVER_TIMEOUT, default="2min"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_ON_ACTION): automation.validate_automation(single=True),
        cv.Optional(CONF_ON_NAVIGATION): automation.validate_automation(single=True),
        cv.Optional(CONF_ON_CALIBRATION): automation.validate_automation(single=True),
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
    icon_font = await cg.get_variable(config[CONF_ICON_FONT_ID])
    backlight_output = await cg.get_variable(config[CONF_BACKLIGHT_OUTPUT_ID])
    sound_player = await cg.get_variable(config[CONF_SOUND_ID])
    touchscreen_component = await cg.get_variable(config[CONF_TOUCHSCREEN_ID])
    cg.add(var.set_clock(clock))
    cg.add(var.set_icon_font(icon_font))
    cg.add(var.set_backlight_output(backlight_output))
    cg.add(var.set_sound_player(sound_player))
    cg.add(var.set_touchscreen(touchscreen_component))
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
    if on_calibration_config := config.get(CONF_ON_CALIBRATION):
        await automation.build_automation(
            var.get_calibration_trigger(),
            [(cg.bool_, "success"), (cg.int_, "x_min"), (cg.int_, "x_max"),
             (cg.int_, "y_min"), (cg.int_, "y_max")],
            on_calibration_config,
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
