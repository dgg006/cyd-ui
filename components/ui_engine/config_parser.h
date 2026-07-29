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
  bool parse_time(const char *text, uint16_t *minutes) const;
  bool parse_idle_mode(const char *text, IdleMode *mode) const;
};

}  // namespace ui_engine
}  // namespace esphome
