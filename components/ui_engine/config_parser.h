#pragma once

#include <string>

#include "model.h"

namespace esphome {
namespace ui_engine {

class ConfigParser {
 public:
  bool parse(const std::string &raw_json, UiConfig *output, std::string *error) const;

 private:
  bool parse_color(const char *text, uint32_t *color) const;
};

}  // namespace ui_engine
}  // namespace esphome

