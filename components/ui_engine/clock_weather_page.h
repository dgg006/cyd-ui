#pragma once

#include <string>

#include "esphome/components/time/real_time_clock.h"
#include "lvgl.h"
#include "page_template.h"

namespace esphome {
namespace ui_engine {

class ClockWeatherPage : public PageTemplate {
 public:
  explicit ClockWeatherPage(time::RealTimeClock *clock) : clock_(clock) {}
  void loop() override;
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
  void update_clock_();
  static const char *translate_condition_(const std::string &condition);
  static const char *condition_glyph_(const std::string &condition);
  static uint32_t condition_color_(const std::string &condition);

  time::RealTimeClock *clock_{nullptr};
  lv_obj_t *time_label_{nullptr};
  lv_obj_t *date_label_{nullptr};
  lv_obj_t *condition_label_{nullptr};
  lv_obj_t *condition_icon_label_{nullptr};
  lv_obj_t *temperature_label_{nullptr};
  lv_obj_t *humidity_label_{nullptr};
  lv_obj_t *previous_button_{nullptr};
  lv_obj_t *next_button_{nullptr};
  std::string condition_id_;
  std::string temperature_id_;
  std::string humidity_id_;
  uint32_t last_clock_update_{0};
  ActionCallback action_callback_;
  NavigationCallback navigation_callback_;
};

}  // namespace ui_engine
}  // namespace esphome
