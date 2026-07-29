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
  std::string unit;
  std::string icon_raw;
  std::string icon_on_raw;
  std::string icon_off_raw;
  const char *resolved_icon{nullptr};
  const char *resolved_icon_on{nullptr};
  const char *resolved_icon_off{nullptr};
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
  int32_t screensaver_timeout_seconds{-1};
  std::vector<PageConfig> pages;
};

}  // namespace ui_engine
}  // namespace esphome
