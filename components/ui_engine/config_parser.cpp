#include "config_parser.h"

#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <set>

#include "ArduinoJson.h"
#include "esphome/components/json/json_util.h"
#include "icon_registry.h"

namespace esphome {
namespace ui_engine {

bool ConfigParser::parse(const std::string &raw_json, UiConfig *output, std::string *error) const {
  JsonDocument document = esphome::json::parse_json(raw_json);
  if (document.isNull() || !document.is<JsonObject>()) {
    *error = "JSON invalido o raiz no es un objeto";
    return false;
  }

  JsonObject root = document.as<JsonObject>();
  if (!root["schema_version"].is<int>() || root["schema_version"].as<int>() != 1) {
    *error = "schema_version debe ser 1";
    return false;
  }

  JsonArray pages = root["pages"].as<JsonArray>();
  if (pages.isNull() || pages.size() < 1 || pages.size() > 8) {
    *error = "pages debe contener entre 1 y 8 paginas";
    return false;
  }

  UiConfig candidate;
  candidate.schema_version = 1;
  if (root.containsKey("screensaver_timeout")) {
    if (!root["screensaver_timeout"].is<int>()) {
      *error = "screensaver_timeout debe ser una cantidad entera de segundos";
      return false;
    }
    candidate.screensaver_timeout_seconds = root["screensaver_timeout"].as<int>();
    if (candidate.screensaver_timeout_seconds < 0 || candidate.screensaver_timeout_seconds > 3600) {
      *error = "screensaver_timeout debe estar entre 0 y 3600 segundos";
      return false;
    }
    candidate.settings.inactivity.timeout_seconds = candidate.screensaver_timeout_seconds;
  }

  JsonObject settings = root["settings"].as<JsonObject>();
  if (!settings.isNull()) {
    JsonObject display = settings["display"].as<JsonObject>();
    if (!display.isNull()) {
      auto read_percent = [error](JsonObject object, const char *key, uint8_t *target) {
        if (!object.containsKey(key)) return true;
        if (!object[key].is<int>()) {
          *error = std::string("settings.display.") + key + " debe ser entero";
          return false;
        }
        const int value = object[key].as<int>();
        if (value < 0 || value > 100) {
          *error = std::string("settings.display.") + key + " debe estar entre 0 y 100";
          return false;
        }
        *target = static_cast<uint8_t>(value);
        return true;
      };
      if (!read_percent(display, "brightness", &candidate.settings.display.brightness) ||
          !read_percent(display, "minimum_brightness", &candidate.settings.display.minimum_brightness) ||
          !read_percent(display, "maximum_brightness", &candidate.settings.display.maximum_brightness)) {
        return false;
      }
      if (candidate.settings.display.minimum_brightness > candidate.settings.display.maximum_brightness) {
        *error = "settings.display.minimum_brightness no puede superar maximum_brightness";
        return false;
      }
      if (display.containsKey("auto_brightness")) {
        if (!display["auto_brightness"].is<bool>()) {
          *error = "settings.display.auto_brightness debe ser booleano";
          return false;
        }
        candidate.settings.display.auto_brightness = display["auto_brightness"].as<bool>();
      }
      for (const char *key : {"ldr_dark_voltage", "ldr_bright_voltage"}) {
        if (display.containsKey(key) && !display[key].is<float>()) {
          *error = std::string("settings.display.") + key + " debe ser numerico";
          return false;
        }
      }
      if (display.containsKey("ldr_dark_voltage"))
        candidate.settings.display.ldr_dark_voltage = display["ldr_dark_voltage"].as<float>();
      if (display.containsKey("ldr_bright_voltage"))
        candidate.settings.display.ldr_bright_voltage = display["ldr_bright_voltage"].as<float>();
      if (candidate.settings.display.ldr_dark_voltage < 0.0f || candidate.settings.display.ldr_dark_voltage > 3.3f ||
          candidate.settings.display.ldr_bright_voltage < 0.0f ||
          candidate.settings.display.ldr_bright_voltage > 3.3f ||
          candidate.settings.display.ldr_dark_voltage == candidate.settings.display.ldr_bright_voltage) {
        *error = "los valores de calibracion LDR deben ser distintos y estar entre 0.0 y 3.3 V";
        return false;
      }
    }

    JsonObject appearance = settings["appearance"].as<JsonObject>();
    if (!appearance.isNull()) {
      const char *mode = appearance["mode"] | "dark";
      if (std::strcmp(mode, "dark") == 0) candidate.settings.appearance.light_mode = false;
      else if (std::strcmp(mode, "light") == 0) candidate.settings.appearance.light_mode = true;
      else {
        *error = "settings.appearance.mode debe ser dark o light";
        return false;
      }
      const char *accent = appearance["accent"] | "mint";
      if (std::strcmp(accent, "mint") && std::strcmp(accent, "blue") && std::strcmp(accent, "violet") &&
          std::strcmp(accent, "amber") && std::strcmp(accent, "rose")) {
        *error = "settings.appearance.accent no es valido";
        return false;
      }
      candidate.settings.appearance.accent = accent;
    }

    JsonObject inactivity = settings["inactivity"].as<JsonObject>();
    if (!inactivity.isNull()) {
      if (inactivity.containsKey("timeout")) {
        if (!inactivity["timeout"].is<int>()) {
          *error = "settings.inactivity.timeout debe ser entero";
          return false;
        }
        candidate.settings.inactivity.timeout_seconds = inactivity["timeout"].as<int>();
        if (candidate.settings.inactivity.timeout_seconds < 0 || candidate.settings.inactivity.timeout_seconds > 3600) {
          *error = "settings.inactivity.timeout debe estar entre 0 y 3600 segundos";
          return false;
        }
      }
      if (inactivity.containsKey("mode") &&
          !this->parse_idle_mode(inactivity["mode"] | "", &candidate.settings.inactivity.mode)) {
        *error = "settings.inactivity.mode no es valido";
        return false;
      }
      if (inactivity.containsKey("dim_brightness")) {
        const int value = inactivity["dim_brightness"].as<int>();
        if (!inactivity["dim_brightness"].is<int>() || value < 0 || value > 100) {
          *error = "settings.inactivity.dim_brightness debe estar entre 0 y 100";
          return false;
        }
        candidate.settings.inactivity.dim_brightness = static_cast<uint8_t>(value);
      }
    }

    JsonObject night = settings["night"].as<JsonObject>();
    if (!night.isNull()) {
      if (night.containsKey("enabled")) {
        if (!night["enabled"].is<bool>()) {
          *error = "settings.night.enabled debe ser booleano";
          return false;
        }
        candidate.settings.night.enabled = night["enabled"].as<bool>();
      }
      if (night.containsKey("start") && !this->parse_time(night["start"] | "", &candidate.settings.night.start_minutes)) {
        *error = "settings.night.start debe usar HH:MM";
        return false;
      }
      if (night.containsKey("end") && !this->parse_time(night["end"] | "", &candidate.settings.night.end_minutes)) {
        *error = "settings.night.end debe usar HH:MM";
        return false;
      }
      if (night.containsKey("brightness")) {
        const int value = night["brightness"].as<int>();
        if (!night["brightness"].is<int>() || value < 0 || value > 100) {
          *error = "settings.night.brightness debe estar entre 0 y 100";
          return false;
        }
        candidate.settings.night.brightness = static_cast<uint8_t>(value);
      }
      if (night.containsKey("mode") && !this->parse_idle_mode(night["mode"] | "", &candidate.settings.night.mode)) {
        *error = "settings.night.mode no es valido";
        return false;
      }
    }

    JsonObject sound = settings["sound"].as<JsonObject>();
    if (!sound.isNull()) {
      for (const char *key : {"enabled", "touch", "navigation", "notifications", "mute_at_night"}) {
        if (sound.containsKey(key) && !sound[key].is<bool>()) {
          *error = std::string("settings.sound.") + key + " debe ser booleano";
          return false;
        }
      }
      if (sound.containsKey("enabled")) candidate.settings.sound.enabled = sound["enabled"].as<bool>();
      if (sound.containsKey("touch")) candidate.settings.sound.touch = sound["touch"].as<bool>();
      if (sound.containsKey("navigation")) candidate.settings.sound.navigation = sound["navigation"].as<bool>();
      if (sound.containsKey("notifications"))
        candidate.settings.sound.notifications = sound["notifications"].as<bool>();
      if (sound.containsKey("mute_at_night"))
        candidate.settings.sound.mute_at_night = sound["mute_at_night"].as<bool>();
      if (sound.containsKey("volume")) {
        const int value = sound["volume"].as<int>();
        if (!sound["volume"].is<int>() || value < 0 || value > 10) {
          *error = "settings.sound.volume debe estar entre 0 y 10";
          return false;
        }
        candidate.settings.sound.volume = static_cast<uint8_t>(value);
      }
      candidate.settings.sound.touch_volume = candidate.settings.sound.volume;
      candidate.settings.sound.navigation_volume = candidate.settings.sound.volume;
      candidate.settings.sound.notification_volume = candidate.settings.sound.volume;
      for (const char *key : {"touch_volume", "navigation_volume", "notification_volume"}) {
        if (!sound.containsKey(key)) continue;
        const int value = sound[key].as<int>();
        if (!sound[key].is<int>() || value < 0 || value > 10) {
          *error = std::string("settings.sound.") + key + " debe estar entre 0 y 10";
          return false;
        }
        if (strcmp(key, "touch_volume") == 0) candidate.settings.sound.touch_volume = static_cast<uint8_t>(value);
        if (strcmp(key, "navigation_volume") == 0)
          candidate.settings.sound.navigation_volume = static_cast<uint8_t>(value);
        if (strcmp(key, "notification_volume") == 0)
          candidate.settings.sound.notification_volume = static_cast<uint8_t>(value);
      }
    }

    JsonObject touchscreen = settings["touchscreen"].as<JsonObject>();
    if (!touchscreen.isNull()) {
      int16_t *targets[] = {&candidate.settings.touchscreen.x_min, &candidate.settings.touchscreen.x_max,
                            &candidate.settings.touchscreen.y_min, &candidate.settings.touchscreen.y_max};
      const char *keys[] = {"x_min", "x_max", "y_min", "y_max"};
      for (size_t index = 0; index < 4; index++) {
        if (!touchscreen.containsKey(keys[index])) continue;
        const int value = touchscreen[keys[index]].as<int>();
        if (!touchscreen[keys[index]].is<int>() || value < 0 || value > 4095) {
          *error = std::string("settings.touchscreen.") + keys[index] + " debe estar entre 0 y 4095";
          return false;
        }
        *targets[index] = static_cast<int16_t>(value);
      }
      if (candidate.settings.touchscreen.x_min >= candidate.settings.touchscreen.x_max ||
          candidate.settings.touchscreen.y_min >= candidate.settings.touchscreen.y_max) {
        *error = "settings.touchscreen requiere minimos menores que maximos";
        return false;
      }
    }
  }
  std::set<std::string> ids;
  for (JsonObject page_json : pages) {
    if (page_json.isNull()) {
      *error = "cada pagina debe ser un objeto";
      return false;
    }

    PageConfig page;
    page.template_name = page_json["template"] | "";
    page.variant = page_json["variant"] | "";
    page.title = page_json["title"] | "";
    page.screensaver = page_json["screensaver"] | false;
    const bool title_optional = page.template_name == "clock_weather" && page.variant == "screensaver";
    if (page.template_name.empty() || page.variant.empty() || (!title_optional && page.title.empty())) {
      *error = "template, variant y title son obligatorios salvo en el screensaver";
      return false;
    }

    JsonArray controls = page_json["controls"].as<JsonArray>();
    if (controls.isNull() || controls.size() < 1 || controls.size() > 10) {
      *error = "cada pagina debe contener entre 1 y 10 controles";
      return false;
    }

    for (JsonObject control_json : controls) {
      ControlConfig control;
      control.type = control_json["type"] | "";
      control.id = control_json["id"] | "";
      control.caption = control_json["caption"] | "";
      control.role = control_json["role"] | "";
      control.action = control_json["action"] | "";
      control.unit = control_json["unit"] | "";
      control.icon_raw = control_json["icon"] | "";
      control.icon_on_raw = control_json["icon_on"] | "";
      control.icon_off_raw = control_json["icon_off"] | "";
      const char *color_text = control_json["color"] | "";

      if ((control.type != "button" && control.type != "value") || control.id.empty() || control.caption.empty()) {
        *error = "cada control requiere type=button/value, id y caption";
        return false;
      }
      if (!ids.insert(control.id).second) {
        *error = "los id de controles deben ser unicos en todo el documento";
        return false;
      }
      if (!this->parse_color(color_text, &control.color)) {
        *error = "color debe tener formato #RRGGBB";
        return false;
      }
      control.resolved_icon = resolve_mdi_icon(control.icon_raw);
      control.resolved_icon_on = resolve_mdi_icon(control.icon_on_raw);
      control.resolved_icon_off = resolve_mdi_icon(control.icon_off_raw);
      if ((!control.icon_raw.empty() && control.resolved_icon == nullptr) ||
          (!control.icon_on_raw.empty() && control.resolved_icon_on == nullptr) ||
          (!control.icon_off_raw.empty() && control.resolved_icon_off == nullptr)) {
        *error = "icon, icon_on e icon_off deben ser nombres MDI admitidos";
        return false;
      }
      if (control_json["meta"].is<JsonObject>()) {
        serializeJson(control_json["meta"], control.meta_raw);
      }
      page.controls.push_back(std::move(control));
    }
    candidate.pages.push_back(std::move(page));
  }
  *output = std::move(candidate);
  return true;
}

bool ConfigParser::parse_color(const char *text, uint32_t *color) const {
  if (text == nullptr || text[0] != '#' || std::char_traits<char>::length(text) != 7) {
    return false;
  }
  char *end = nullptr;
  const unsigned long value = std::strtoul(text + 1, &end, 16);
  if (end == nullptr || *end != '\0') {
    return false;
  }
  *color = static_cast<uint32_t>(value);
  return true;
}

bool ConfigParser::parse_time(const char *text, uint16_t *minutes) const {
  if (text == nullptr) return false;
  unsigned hour = 0;
  unsigned minute = 0;
  char trailing = '\0';
  if (std::sscanf(text, "%2u:%2u%c", &hour, &minute, &trailing) != 2 || hour > 23 || minute > 59) return false;
  *minutes = static_cast<uint16_t>(hour * 60 + minute);
  return true;
}

bool ConfigParser::parse_idle_mode(const char *text, IdleMode *mode) const {
  const std::string value = text == nullptr ? "" : text;
  if (value == "clock_weather") *mode = IdleMode::CLOCK_WEATHER;
  else if (value == "screen_off") *mode = IdleMode::SCREEN_OFF;
  else if (value == "dim") *mode = IdleMode::DIM;
  else if (value == "none") *mode = IdleMode::NONE;
  else return false;
  return true;
}

}  // namespace ui_engine
}  // namespace esphome
