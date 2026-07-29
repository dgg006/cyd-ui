#include "config_parser.h"

#include <cstdlib>
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
    if (controls.isNull() || controls.size() < 1 || controls.size() > 6) {
      *error = "cada pagina debe contener entre 1 y 6 controles";
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

}  // namespace ui_engine
}  // namespace esphome
