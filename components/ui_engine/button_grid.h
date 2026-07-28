#pragma once

#include <array>
#include <cstddef>
#include <string>

#include "lvgl.h"
#include "model.h"
#include "page_template.h"

namespace esphome {
namespace ui_engine {

class ButtonGrid : public PageTemplate {
 public:
  void create(lv_obj_t *parent) override;
  void apply(const PageConfig &config) override;
  bool update_control(const std::string &id, bool active, ControlState state) override;
  void set_all_states(ControlState state) override;
  bool validate(const PageConfig &config, std::string *error) const override;
  void set_action_callback(ActionCallback callback) override { this->action_callback_ = std::move(callback); }
  void set_navigation_callback(NavigationCallback callback) override { this->navigation_callback_ = std::move(callback); }
  void set_navigation_enabled(bool enabled) override;

 private:
  struct EventBinding {
    ButtonGrid *grid;
    size_t index;
  };

  static void event_callback(lv_event_t *event);
  static void previous_callback(lv_event_t *event);
  static void next_callback(lv_event_t *event);
  void handle_click(size_t index);
  void apply_state(size_t index);
  void apply_layout(const std::string &variant);

  lv_obj_t *title_{nullptr};
  lv_obj_t *previous_button_{nullptr};
  lv_obj_t *next_button_{nullptr};
  std::array<lv_obj_t *, 6> buttons_{};
  std::array<lv_obj_t *, 6> labels_{};
  std::array<EventBinding, 6> bindings_{};
  std::array<std::string, 6> ids_{};
  std::array<uint32_t, 6> colors_{};
  std::array<ControlState, 6> states_{};
  std::array<bool, 6> active_{};
  ActionCallback action_callback_;
  NavigationCallback navigation_callback_;
};

}  // namespace ui_engine
}  // namespace esphome
