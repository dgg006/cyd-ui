#include "config_parser.h"

#include <cstdlib>
#include <set>

#include "ArduinoJson.h"
#include "esphome/components/json/json_util.h"

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
    if (page.template_name.empty() || page.variant.empty() || page.title.empty()) {
      *error = "template, variant y title son obligatorios";
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
