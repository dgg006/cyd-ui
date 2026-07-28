#pragma once

#include <array>
#include <string>

#include "lvgl.h"
#include "page_template.h"

namespace esphome {
namespace ui_engine {

class SensorGrid : public PageTemplate {
 public:
  void create(lv_obj_t *parent) override;
  void apply(const PageConfig &config) override;
  bool update_control(const std::string &id, bool active, const std::string &value, ControlState state) override;
  void set_all_states(ControlState state) override;
  bool validate(const PageConfig &config, std::string *error) const override;
  void set_action_callback(ActionCallback callback) override { this->action_callback_ = std::move(callback); }
  void set_navigation_callback(NavigationCallback callback) override { this->navigation_callback_ = std::move(callback); }
  void set_navigation_enabled(bool enabled) override;

 private:
  static void previous_callback(lv_event_t *event);
  static void next_callback(lv_event_t *event);
  void apply_state_(size_t index);

  lv_obj_t *title_{nullptr};
  lv_obj_t *previous_button_{nullptr};
  lv_obj_t *next_button_{nullptr};
  std::array<lv_obj_t *, 4> cards_{};
  std::array<lv_obj_t *, 4> captions_{};
  std::array<lv_obj_t *, 4> values_{};
  std::array<std::string, 4> ids_{};
  std::array<std::string, 4> units_{};
  std::array<std::string, 4> raw_values_{};
  std::array<uint32_t, 4> colors_{};
  std::array<ControlState, 4> states_{};
  ActionCallback action_callback_;
  NavigationCallback navigation_callback_;
};

}  // namespace ui_engine
}  // namespace esphome
