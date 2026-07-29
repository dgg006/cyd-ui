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

enum class IdleMode {
  CLOCK_WEATHER,
  SCREEN_OFF,
  DIM,
  NONE,
};

struct DisplaySettings {
  uint8_t brightness{100};
  bool auto_brightness{false};
  uint8_t minimum_brightness{15};
  uint8_t maximum_brightness{100};
  float ldr_dark_voltage{3.0f};
  float ldr_bright_voltage{0.2f};
};

struct InactivitySettings {
  int32_t timeout_seconds{-1};
  IdleMode mode{IdleMode::CLOCK_WEATHER};
  uint8_t dim_brightness{10};
};

struct NightSettings {
  bool enabled{false};
  uint16_t start_minutes{23 * 60};
  uint16_t end_minutes{7 * 60};
  uint8_t brightness{15};
  IdleMode mode{IdleMode::SCREEN_OFF};
};

struct SoundSettings {
  bool enabled{true};
  uint8_t volume{5};
  bool touch{true};
  uint8_t touch_volume{5};
  bool navigation{true};
  uint8_t navigation_volume{5};
  bool notifications{true};
  uint8_t notification_volume{5};
  bool mute_at_night{false};
};

struct TouchSettings {
  int16_t x_min{200};
  int16_t x_max{3700};
  int16_t y_min{240};
  int16_t y_max{3800};
};

struct DeviceSettings {
  DisplaySettings display;
  InactivitySettings inactivity;
  NightSettings night;
  SoundSettings sound;
  TouchSettings touchscreen;
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
  DeviceSettings settings;
  std::vector<PageConfig> pages;
};

}  // namespace ui_engine
}  // namespace esphome
