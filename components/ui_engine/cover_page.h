#pragma once

#include <string>

#include "lvgl.h"
#include "page_template.h"

namespace esphome {
namespace ui_engine {

class CoverPage : public PageTemplate {
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
  static void open_callback(lv_event_t *event);
  static void close_callback(lv_event_t *event);
  static void close_step_callback(lv_event_t *event);
  static void open_step_callback(lv_event_t *event);
  void emit_action(const std::string &id, const std::string &action);
  void apply_value_state();

  lv_obj_t *title_{nullptr};
  lv_obj_t *previous_button_{nullptr};
  lv_obj_t *next_button_{nullptr};
  lv_obj_t *position_label_{nullptr};
  lv_obj_t *state_label_{nullptr};
  lv_obj_t *open_button_{nullptr};
  lv_obj_t *close_button_{nullptr};
  lv_obj_t *close_step_button_{nullptr};
  lv_obj_t *open_step_button_{nullptr};
  lv_obj_t *open_label_{nullptr};
  lv_obj_t *close_label_{nullptr};
  lv_obj_t *close_step_label_{nullptr};
  lv_obj_t *open_step_label_{nullptr};

  std::string position_id_;
  std::string state_id_;
  std::string open_id_;
  std::string close_id_;
  std::string close_step_id_;
  std::string open_step_id_;
  std::string open_action_{"open"};
  std::string close_action_{"close"};
  std::string close_step_action_{"close_step"};
  std::string open_step_action_{"open_step"};
  std::string position_value_;
  std::string state_value_;
  uint32_t position_color_{0x90CAF9};
  ControlState position_state_{ControlState::UNKNOWN};
  ControlState state_state_{ControlState::UNKNOWN};
  ActionCallback action_callback_;
  NavigationCallback navigation_callback_;
};

}  // namespace ui_engine
}  // namespace esphome
