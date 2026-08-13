#pragma once

#include <map>
#include <array>
#include <string>

#include "esphome/components/online_image/online_image.h"
#include "lvgl.h"
#include "page_template.h"

namespace esphome {
namespace ui_engine {

class MediaPage : public PageTemplate {
 public:
  explicit MediaPage(online_image::OnlineImage *artwork_image) : artwork_image_(artwork_image) {}
  void create(lv_obj_t *parent) override;
  void apply(const PageConfig &config) override;
  bool update_control(const std::string &id, bool active, const std::string &value, ControlState state) override;
  void set_all_states(ControlState state) override;
  bool validate(const PageConfig &config, std::string *error) const override;
  void set_action_callback(ActionCallback callback) override { this->action_callback_ = std::move(callback); }
  void set_navigation_callback(NavigationCallback callback) override { this->navigation_callback_ = std::move(callback); }
  void set_navigation_enabled(bool enabled) override;
  void refresh_external_assets() override;
  void clear_external_assets() override;

 private:
  static void previous_page_callback(lv_event_t *event);
  static void next_page_callback(lv_event_t *event);
  static void player_selector_callback(lv_event_t *event);
  static void player_option_callback(lv_event_t *event);
  static void action_callback(lv_event_t *event);
  void emit(const std::string &id, const std::string &action);
  void refresh_value(const std::string &role);
  void update_artwork_url_(const std::string &url, ControlState state);
  void update_player_options_(const std::string &value);
  void set_player_menu_visible_(bool visible);

  lv_obj_t *title_{nullptr};
  lv_obj_t *previous_page_{nullptr};
  lv_obj_t *next_page_{nullptr};
  lv_obj_t *player_selector_{nullptr};
  lv_obj_t *player_{nullptr};
  lv_obj_t *player_chevron_{nullptr};
  lv_obj_t *player_menu_{nullptr};
  std::array<lv_obj_t *, 3> player_option_buttons_{};
  std::array<lv_obj_t *, 3> player_option_labels_{};
  std::array<std::string, 3> player_names_{};
  uint8_t player_count_{0};
  uint8_t selected_player_{0};
  lv_obj_t *media_title_{nullptr};
  lv_obj_t *artist_{nullptr};
  lv_obj_t *station_{nullptr};
  lv_obj_t *volume_{nullptr};
  lv_obj_t *volume_bar_{nullptr};
  lv_obj_t *volume_bar_fill_{nullptr};
  lv_obj_t *artwork_frame_{nullptr};
  lv_obj_t *artwork_placeholder_{nullptr};
  lv_obj_t *artwork_{nullptr};
  online_image::OnlineImage *artwork_image_{nullptr};
  std::string artwork_url_;
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
