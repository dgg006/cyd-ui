#pragma once

#include <string>

#include "esphome/core/preferences.h"

namespace esphome {
namespace ui_engine {

class FlashStorage {
 public:
  void begin();
  bool load(std::string *raw_json, std::string *error);
  bool save(const std::string &raw_json, std::string *error);

 private:
  ESPPreferenceObject preference_;
  uint32_t saved_checksum_{0};
  size_t saved_length_{0};
};

}  // namespace ui_engine
}  // namespace esphome
