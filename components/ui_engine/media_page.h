#pragma once

#include <map>
#include <string>

#include "lvgl.h"
#include "page_template.h"

namespace esphome {
namespace ui_engine {

class MediaPage : public PageTemplate {
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
  static void previous_page_callback(lv_event_t *event);
  static void next_page_callback(lv_event_t *event);
  static void previous_player_callback(lv_event_t *event);
  static void next_player_callback(lv_event_t *event);
  static void action_callback(lv_event_t *event);
  void emit(const std::string &id, const std::string &action);
  void refresh_value(const std::string &role);

  lv_obj_t *title_{nullptr};
  lv_obj_t *previous_page_{nullptr};
  lv_obj_t *next_page_{nullptr};
  lv_obj_t *previous_player_{nullptr};
  lv_obj_t *next_player_{nullptr};
  lv_obj_t *player_{nullptr};
  lv_obj_t *media_title_{nullptr};
  lv_obj_t *artist_{nullptr};
  lv_obj_t *station_{nullptr};
  lv_obj_t *volume_{nullptr};
  std::map<std::string, lv_obj_t *> buttons_;
  std::map<std::string, lv_obj_t *> button_labels_;
  std::map<std::string, std::string> ids_;
  std::map<std::string, std::string> actions_;
  std::map<std::string, std::string> values_;
  std::map<std::string, ControlState> states_;
  ActionCallback action_callback_;
  NavigationCallback navigation_callback_;
};

}  // namespace ui_engine
}  // namespace esphome
