#include "icon_registry.h"

#include <array>

namespace esphome {
namespace ui_engine {

struct IconEntry {
  const char *name;
  const char *glyph;
};

static constexpr std::array<IconEntry, 54> ICONS{{
    {"mdi:motion-sensor", "\U000F0D91"},
    {"mdi:motion-sensor-off", "\U000F1435"},
    {"mdi:lightbulb", "\U000F0335"},
    {"mdi:lightbulb-off", "\U000F0E4F"},
    {"mdi:door-open", "\U000F081C"},
    {"mdi:door-closed", "\U000F081B"},
    {"mdi:window-open", "\U000F05B1"},
    {"mdi:window-closed", "\U000F05AE"},
    {"mdi:garage-open", "\U000F06DA"},
    {"mdi:garage", "\U000F06D9"},
    {"mdi:thermometer", "\U000F050F"},
    {"mdi:water-percent", "\U000F058E"},
    {"mdi:weather-sunny", "\U000F0599"},
    {"mdi:weather-night", "\U000F0594"},
    {"mdi:weather-cloudy", "\U000F0590"},
    {"mdi:weather-rainy", "\U000F0597"},
    {"mdi:radiator", "\U000F0438"},
    {"mdi:air-conditioner", "\U000F001B"},
    {"mdi:fan", "\U000F0210"},
    {"mdi:blinds-open", "\U000F1011"},
    {"mdi:blinds", "\U000F00AC"},
    {"mdi:lock", "\U000F033E"},
    {"mdi:lock-open", "\U000F033F"},
    {"mdi:power", "\U000F0425"},
    {"mdi:home", "\U000F02DC"},
    {"mdi:robot-vacuum", "\U000F070D"},
    {"mdi:speaker", "\U000F04C3"},
    {"mdi:bell", "\U000F009A"},
    {"mdi:alert", "\U000F0026"},
    {"mdi:check-circle", "\U000F05E0"},
    {"mdi:close-circle", "\U000F0159"},
    {"mdi:wifi", "\U000F05A9"},
    {"mdi:wifi-off", "\U000F05AA"},
    {"mdi:battery", "\U000F0079"},
    {"mdi:battery-alert", "\U000F0083"},
    {"mdi:eye", "\U000F0208"},
    {"mdi:eye-off", "\U000F0209"},
    {"mdi:toggle-switch", "\U000F0521"},
    {"mdi:toggle-switch-off", "\U000F0522"},
    {"mdi:arrow-up", "\U000F005D"},
    {"mdi:arrow-down", "\U000F0045"},
    {"mdi:arrow-left", "\U000F004D"},
    {"mdi:arrow-right", "\U000F0054"},
    {"mdi:play", "\U000F040A"},
    {"mdi:pause", "\U000F03E4"},
    {"mdi:stop", "\U000F04DB"},
    {"mdi:skip-previous", "\U000F04AE"},
    {"mdi:skip-next", "\U000F04AD"},
    {"mdi:volume-minus", "\U000F075E"},
    {"mdi:volume-plus", "\U000F075D"},
    {"mdi:information", "\U000F02FC"},
    {"mdi:gauge", "\U000F029A"},
    {"mdi:fire", "\U000F0238"},
    {"mdi:snowflake", "\U000F0717"},
}};

const char *resolve_mdi_icon(const std::string &name) {
  if (name.empty()) {
    return nullptr;
  }
  for (const auto &entry : ICONS) {
    if (name == entry.name) {
      return entry.glyph;
    }
  }
  return nullptr;
}

}  // namespace ui_engine
}  // namespace esphome
