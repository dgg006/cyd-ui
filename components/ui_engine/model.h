#pragma once

#include <string>
#include <vector>

namespace esphome {
namespace ui_engine {

enum class ControlState {
  UNKNOWN,
  VALID,
  STALE_OR_DISCONNECTED,
};

struct ControlConfig {
  std::string type;
  std::string id;
  std::string caption;
  std::string role;
  std::string action;
  uint32_t color{0};
  std::string meta_raw;
};

struct PageConfig {
  std::string template_name;
  std::string variant;
  std::string title;
  bool screensaver{false};
  std::vector<ControlConfig> controls;
};

struct UiConfig {
  int schema_version{0};
  std::vector<PageConfig> pages;
};

}  // namespace ui_engine
}  // namespace esphome
