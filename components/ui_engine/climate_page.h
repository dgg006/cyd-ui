#pragma once

#include <string>

#include "lvgl.h"
#include "page_template.h"

namespace esphome {
namespace ui_engine {

class ClimatePage : public PageTemplate {
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
  static void decrease_callback(lv_event_t *event);
  static void power_callback(lv_event_t *event);
  static void increase_callback(lv_event_t *event);
  void emit_action(const std::string &id, const std::string &action);
  void apply_power_state();

  lv_obj_t *title_{nullptr};
  lv_obj_t *previous_button_{nullptr};
  lv_obj_t *next_button_{nullptr};
  lv_obj_t *current_label_{nullptr};
  lv_obj_t *target_label_{nullptr};
  lv_obj_t *decrease_button_{nullptr};
  lv_obj_t *power_button_{nullptr};
  lv_obj_t *increase_button_{nullptr};
  lv_obj_t *decrease_label_{nullptr};
  lv_obj_t *power_label_{nullptr};
  lv_obj_t *increase_label_{nullptr};

  std::string current_id_;
  std::string target_id_;
  std::string decrease_id_;
  std::string power_id_;
  std::string increase_id_;
  std::string decrease_action_{"decrement"};
  std::string power_action_{"toggle"};
  std::string increase_action_{"increment"};
  uint32_t power_color_{0xD84315};
  bool power_active_{false};
  ControlState power_state_{ControlState::UNKNOWN};
  ActionCallback action_callback_;
  NavigationCallback navigation_callback_;
};

}  // namespace ui_engine
}  // namespace esphome
