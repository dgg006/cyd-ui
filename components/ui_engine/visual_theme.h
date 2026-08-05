#pragma once

#include <string>

#include "lvgl.h"

namespace esphome {
namespace ui_engine {
namespace visual_theme {

inline uint32_t BACKGROUND = 0x0B1219;
inline uint32_t SURFACE = 0x16232E;
inline uint32_t SURFACE_MUTED = 0x202D38;
inline uint32_t TEXT = 0xF1F5F8;
inline uint32_t TEXT_MUTED = 0x9FB2C1;
inline uint32_t BORDER = 0x2A3A48;
inline uint32_t ACCENT = 0x50D5AD;

inline void configure(bool light_mode, const std::string &accent) {
  if (light_mode) {
    BACKGROUND = 0xEAF0F4;
    SURFACE = 0xFFFFFF;
    SURFACE_MUTED = 0xD9E2E8;
    TEXT = 0x17212B;
    TEXT_MUTED = 0x536575;
    BORDER = 0xC6D2DA;
  } else {
    BACKGROUND = 0x0B1219;
    SURFACE = 0x16232E;
    SURFACE_MUTED = 0x202D38;
    TEXT = 0xF1F5F8;
    TEXT_MUTED = 0x9FB2C1;
    BORDER = 0x2A3A48;
  }
  if (accent == "blue") ACCENT = 0x4AA3FF;
  else if (accent == "violet") ACCENT = 0xA78BFA;
  else if (accent == "amber") ACCENT = 0xF6B73C;
  else if (accent == "rose") ACCENT = 0xF472B6;
  else ACCENT = 0x50D5AD;
}

inline void page(lv_obj_t *parent) {
  lv_obj_set_style_bg_color(parent, lv_color_hex(BACKGROUND), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(parent, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_pad_all(parent, 0, LV_PART_MAIN);
}

inline void title(lv_obj_t *label) {
  lv_obj_set_style_text_font(label, &lv_font_montserrat_20, LV_PART_MAIN);
  lv_obj_set_style_text_color(label, lv_color_hex(ACCENT), LV_PART_MAIN);
}

inline void navigation(lv_obj_t *button) {
  lv_obj_set_style_bg_color(button, lv_color_hex(SURFACE), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(button, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_border_width(button, 1, LV_PART_MAIN);
  lv_obj_set_style_border_color(button, lv_color_hex(ACCENT), LV_PART_MAIN);
  lv_obj_set_style_radius(button, 10, LV_PART_MAIN);
}

inline void card(lv_obj_t *object) {
  lv_obj_set_style_bg_color(object, lv_color_hex(SURFACE), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(object, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_border_width(object, 1, LV_PART_MAIN);
  lv_obj_set_style_border_color(object, lv_color_hex(BORDER), LV_PART_MAIN);
  lv_obj_set_style_radius(object, 12, LV_PART_MAIN);
}

}  // namespace visual_theme
}  // namespace ui_engine
}  // namespace esphome
