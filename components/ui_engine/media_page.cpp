#include "media_page.h"

#include <algorithm>
#include <cstdlib>
#include <set>

#include "visual_theme.h"

namespace esphome {
namespace ui_engine {

namespace {
constexpr const char *VALUE_ROLES[] = {"player", "title", "artist", "station", "volume", "artwork"};
constexpr const char *BUTTON_ROLES[] = {"previous", "play_pause", "next", "volume_down", "volume_up"};
constexpr const char *ICON_PREVIOUS = "\U000F04AE";
constexpr const char *ICON_PLAY = "\U000F040A";
constexpr const char *ICON_PAUSE = "\U000F03E4";
constexpr const char *ICON_NEXT = "\U000F04AD";
constexpr const char *ICON_VOLUME_DOWN = "\U000F075E";
constexpr const char *ICON_VOLUME_UP = "\U000F075D";

const char *button_icon(const std::string &role) {
  if (role == "previous") return ICON_PREVIOUS;
  if (role == "play_pause") return ICON_PLAY;
  if (role == "next") return ICON_NEXT;
  if (role == "volume_down") return ICON_VOLUME_DOWN;
  if (role == "volume_up") return ICON_VOLUME_UP;
  return "";
}
}

void MediaPage::create(lv_obj_t *parent) {
  lv_obj_clean(parent);
  visual_theme::page(parent);

  this->title_ = lv_label_create(parent);
  visual_theme::title(this->title_);
  lv_obj_align(this->title_, LV_ALIGN_TOP_MID, 0, 7);

  auto make_nav = [this, parent](int x, lv_event_cb_t callback, const char *text) {
    lv_obj_t *button = lv_button_create(parent);
    lv_obj_set_size(button, 34, 30);
    lv_obj_set_pos(button, x, 3);
    visual_theme::navigation(button);
    lv_obj_t *label = lv_label_create(button);
    lv_label_set_text(label, text);
    lv_obj_center(label);
    lv_obj_add_event_cb(button, callback, LV_EVENT_CLICKED, this);
    return button;
  };
  this->previous_page_ = make_nav(5, previous_page_callback, "<");
  this->next_page_ = make_nav(281, next_page_callback, ">");

  this->artwork_frame_ = lv_obj_create(parent);
  lv_obj_set_size(this->artwork_frame_, 72, 72);
  lv_obj_set_pos(this->artwork_frame_, 14, 44);
  lv_obj_set_style_radius(this->artwork_frame_, 0, LV_PART_MAIN);
  lv_obj_set_style_bg_color(this->artwork_frame_, lv_color_hex(visual_theme::BACKGROUND), LV_PART_MAIN);
  lv_obj_set_style_border_width(this->artwork_frame_, 0, LV_PART_MAIN);
  lv_obj_set_style_pad_all(this->artwork_frame_, 0, LV_PART_MAIN);
  lv_obj_remove_flag(this->artwork_frame_, LV_OBJ_FLAG_SCROLLABLE);

  this->artwork_placeholder_ = lv_label_create(this->artwork_frame_);
  lv_label_set_text(this->artwork_placeholder_, "IMG");
  lv_obj_set_style_text_color(this->artwork_placeholder_, lv_color_hex(visual_theme::TEXT_MUTED), LV_PART_MAIN);
  lv_obj_center(this->artwork_placeholder_);

  this->artwork_ = lv_image_create(this->artwork_frame_);
  lv_obj_set_size(this->artwork_, 72, 72);
  lv_obj_center(this->artwork_);
  lv_obj_add_flag(this->artwork_, LV_OBJ_FLAG_HIDDEN);

  // Compact player selector. For now a tap advances to the next configured
  // player; its visual contract already leaves room for a real option list.
  this->player_selector_ = lv_button_create(parent);
  lv_obj_set_size(this->player_selector_, 214, 31);
  lv_obj_set_pos(this->player_selector_, 98, 41);
  visual_theme::card(this->player_selector_);
  lv_obj_set_style_pad_left(this->player_selector_, 9, LV_PART_MAIN);
  lv_obj_set_style_pad_right(this->player_selector_, 25, LV_PART_MAIN);
  lv_obj_add_event_cb(this->player_selector_, player_selector_callback, LV_EVENT_CLICKED, this);

  this->player_ = lv_label_create(this->player_selector_);
  lv_obj_set_width(this->player_, 178);
  lv_obj_set_height(this->player_, 18);
  lv_obj_set_style_text_align(this->player_, LV_TEXT_ALIGN_LEFT, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->player_, lv_color_hex(visual_theme::ACCENT), LV_PART_MAIN);
  lv_label_set_long_mode(this->player_, LV_LABEL_LONG_DOT);
  lv_obj_align(this->player_, LV_ALIGN_LEFT_MID, 0, 0);

  this->player_chevron_ = lv_label_create(this->player_selector_);
  lv_label_set_text(this->player_chevron_, "v");
  lv_obj_set_style_text_color(this->player_chevron_, lv_color_hex(visual_theme::TEXT_MUTED), LV_PART_MAIN);
  lv_obj_align(this->player_chevron_, LV_ALIGN_RIGHT_MID, 0, -1);

  this->media_title_ = lv_label_create(parent);
  lv_obj_set_width(this->media_title_, 214);
  lv_obj_set_height(this->media_title_, 23);
  if (this->text_font_ != nullptr)
    lv_obj_set_style_text_font(this->media_title_, this->text_font_->get_lv_font(), LV_PART_MAIN);
  lv_obj_set_style_text_align(this->media_title_, LV_TEXT_ALIGN_LEFT, LV_PART_MAIN);
  lv_label_set_long_mode(this->media_title_, LV_LABEL_LONG_DOT);
  lv_obj_set_pos(this->media_title_, 98, 80);

  this->artist_ = lv_label_create(parent);
  lv_obj_set_width(this->artist_, 214);
  lv_obj_set_height(this->artist_, 18);
  lv_obj_set_style_text_align(this->artist_, LV_TEXT_ALIGN_LEFT, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->artist_, lv_color_hex(visual_theme::TEXT_MUTED), LV_PART_MAIN);
  lv_label_set_long_mode(this->artist_, LV_LABEL_LONG_DOT);
  lv_obj_set_pos(this->artist_, 98, 108);

  this->station_ = lv_label_create(parent);
  lv_obj_set_width(this->station_, 214);
  lv_obj_set_height(this->station_, 18);
  lv_obj_set_style_text_align(this->station_, LV_TEXT_ALIGN_LEFT, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->station_, lv_color_hex(visual_theme::TEXT_MUTED), LV_PART_MAIN);
  lv_label_set_long_mode(this->station_, LV_LABEL_LONG_DOT);
  lv_obj_set_pos(this->station_, 98, 131);

  auto make_button = [this, parent](const std::string &role, int x, int y, int width, int height) {
    lv_obj_t *button = lv_button_create(parent);
    lv_obj_set_size(button, width, height);
    lv_obj_set_pos(button, x, y);
    visual_theme::card(button);
    lv_obj_t *label = lv_label_create(button);
    if (this->icon_font_ != nullptr)
      lv_obj_set_style_text_font(label, this->icon_font_->get_lv_font(), LV_PART_MAIN);
    lv_obj_center(label);
    lv_obj_add_event_cb(button, action_callback, LV_EVENT_CLICKED, this);
    this->buttons_[role] = button;
    this->button_labels_[role] = label;
  };
  make_button("previous", 8, 188, 56, 44);
  make_button("play_pause", 70, 188, 56, 44);
  make_button("next", 132, 188, 56, 44);
  make_button("volume_down", 194, 188, 56, 44);
  make_button("volume_up", 256, 188, 56, 44);

  this->volume_ = lv_label_create(parent);
  lv_obj_set_width(this->volume_, 72);
  lv_obj_set_style_text_align(this->volume_, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->volume_, lv_color_hex(visual_theme::TEXT_MUTED), LV_PART_MAIN);
  lv_obj_set_pos(this->volume_, 14, 122);

  this->volume_bar_ = lv_obj_create(parent);
  lv_obj_set_size(this->volume_bar_, 72, 7);
  lv_obj_set_pos(this->volume_bar_, 14, 145);
  lv_obj_set_style_radius(this->volume_bar_, 4, LV_PART_MAIN);
  lv_obj_set_style_bg_color(this->volume_bar_, lv_color_hex(visual_theme::SURFACE_MUTED), LV_PART_MAIN);
  lv_obj_set_style_border_width(this->volume_bar_, 0, LV_PART_MAIN);
  lv_obj_set_style_pad_all(this->volume_bar_, 0, LV_PART_MAIN);
  lv_obj_remove_flag(this->volume_bar_, LV_OBJ_FLAG_SCROLLABLE);

  this->volume_bar_fill_ = lv_obj_create(this->volume_bar_);
  lv_obj_set_size(this->volume_bar_fill_, 0, 7);
  lv_obj_set_pos(this->volume_bar_fill_, 0, 0);
  lv_obj_set_style_radius(this->volume_bar_fill_, 4, LV_PART_MAIN);
  lv_obj_set_style_bg_color(this->volume_bar_fill_, lv_color_hex(visual_theme::ACCENT), LV_PART_MAIN);
  lv_obj_set_style_border_width(this->volume_bar_fill_, 0, LV_PART_MAIN);
  lv_obj_set_style_pad_all(this->volume_bar_fill_, 0, LV_PART_MAIN);
  lv_obj_remove_flag(this->volume_bar_fill_, LV_OBJ_FLAG_SCROLLABLE);
}

void MediaPage::apply(const PageConfig &config) {
  lv_label_set_text(this->title_, config.title.c_str());
  this->ids_.clear();
  this->actions_.clear();
  this->values_.clear();
  this->states_.clear();
  for (const auto &control : config.controls) {
    this->ids_[control.role] = control.id;
    this->actions_[control.role] = control.action;
    this->states_[control.role] = ControlState::UNKNOWN;
    if (auto it = this->button_labels_.find(control.role); it != this->button_labels_.end()) {
      lv_label_set_text(it->second, button_icon(control.role));
      lv_obj_set_style_bg_color(this->buttons_[control.role], lv_color_hex(control.color), LV_PART_MAIN);
      lv_obj_set_style_text_color(this->buttons_[control.role],
                                  lv_color_hex(visual_theme::contrasting_text(control.color)), LV_PART_MAIN);
    }
  }
  for (const char *role : VALUE_ROLES) this->refresh_value(role);
  this->refresh_external_assets();
}

bool MediaPage::update_control(const std::string &id, bool active, const std::string &value, ControlState state) {
  for (const auto &item : this->ids_) {
    if (item.second != id) continue;
    this->values_[item.first] = value;
    this->states_[item.first] = state;
    if (item.first == "artwork") {
      this->update_artwork_url_(value, state);
      return true;
    }
    this->refresh_value(item.first);
    if (item.first == "play_pause") {
      lv_label_set_text(this->button_labels_[item.first], active ? ICON_PAUSE : ICON_PLAY);
      lv_obj_set_style_border_color(this->buttons_[item.first],
                                    lv_color_hex(active ? visual_theme::ACCENT : visual_theme::BORDER), LV_PART_MAIN);
      lv_obj_set_style_border_width(this->buttons_[item.first], active ? 3 : 1, LV_PART_MAIN);
    }
    return true;
  }
  return false;
}

void MediaPage::set_all_states(ControlState state) {
  for (auto &item : this->states_) item.second = state;
  for (const char *role : VALUE_ROLES) this->refresh_value(role);
}

bool MediaPage::validate(const PageConfig &config, std::string *error) const {
  if (config.template_name != "media" || config.variant != "full_controls") {
    *error = "Media requiere template=media y variant=full_controls";
    return false;
  }
  const std::set<std::string> value_roles = {"player", "title", "artist", "station", "volume", "artwork"};
  const std::set<std::string> button_roles = {"previous", "play_pause", "next", "volume_down", "volume_up"};
  std::set<std::string> found;
  for (const auto &control : config.controls) {
    found.insert(control.role);
    if ((value_roles.count(control.role) && control.type != "value") ||
        (button_roles.count(control.role) && control.type != "button")) {
      *error = "Media tiene un tipo de control incorrecto";
      return false;
    }
  }
  std::set<std::string> required = value_roles;
  required.insert(button_roles.begin(), button_roles.end());
  if (found != required) {
    *error = "Media requiere sus once roles completos";
    return false;
  }
  return true;
}

void MediaPage::set_navigation_enabled(bool enabled) {
  for (lv_obj_t *button : {this->previous_page_, this->next_page_}) {
    if (enabled) lv_obj_remove_flag(button, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(button, LV_OBJ_FLAG_HIDDEN);
  }
}

void MediaPage::previous_page_callback(lv_event_t *event) {
  auto *page = static_cast<MediaPage *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(-1);
}
void MediaPage::next_page_callback(lv_event_t *event) {
  auto *page = static_cast<MediaPage *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(1);
}
void MediaPage::player_selector_callback(lv_event_t *event) {
  auto *page = static_cast<MediaPage *>(lv_event_get_user_data(event));
  page->emit(page->ids_["player"], "next_player");
}
void MediaPage::action_callback(lv_event_t *event) {
  auto *page = static_cast<MediaPage *>(lv_event_get_user_data(event));
  lv_obj_t *target = static_cast<lv_obj_t *>(lv_event_get_target(event));
  for (const auto &item : page->buttons_) {
    if (item.second == target) {
      page->emit(page->ids_[item.first], page->actions_[item.first]);
      return;
    }
  }
}
void MediaPage::emit(const std::string &id, const std::string &action) {
  if (!id.empty() && !action.empty() && this->action_callback_) this->action_callback_(id, action);
}

void MediaPage::refresh_value(const std::string &role) {
  if (role == "artwork") return;
  lv_obj_t *label = nullptr;
  const char *fallback = "--";
  if (role == "player") { label = this->player_; fallback = "Sin reproductor"; }
  else if (role == "title") { label = this->media_title_; fallback = "Sin reproduccion"; }
  else if (role == "artist") { label = this->artist_; fallback = "--"; }
  else if (role == "station") { label = this->station_; fallback = "--"; }
  else if (role == "volume") { label = this->volume_; fallback = "Vol --"; }
  if (label == nullptr) return;
  const bool valid = this->states_[role] == ControlState::VALID;
  std::string text = valid && !this->values_[role].empty() ? this->values_[role] : fallback;
  if (role == "volume" && valid && !this->values_[role].empty()) text = "Vol " + text + " %";
  lv_label_set_text(label, text.c_str());
  lv_obj_set_style_text_color(label, lv_color_hex(valid ?
      (role == "player" ? visual_theme::ACCENT : visual_theme::TEXT) : visual_theme::TEXT_MUTED), LV_PART_MAIN);
  if (role == "volume" && this->volume_bar_fill_ != nullptr) {
    const int value = valid ? std::max(0, std::min(100, std::atoi(this->values_[role].c_str()))) : 0;
    lv_obj_set_width(this->volume_bar_fill_, value * 72 / 100);
  }
}

void MediaPage::update_artwork_url_(const std::string &url, ControlState state) {
  if (this->artwork_image_ == nullptr) return;
  if (state != ControlState::VALID || url.empty() || url == "-") {
    this->artwork_url_.clear();
    this->artwork_image_->release();
    this->clear_external_assets();
    return;
  }
  if (url == this->artwork_url_ && this->artwork_image_->is_loaded()) {
    this->refresh_external_assets();
    return;
  }
  this->artwork_url_ = url;
  this->clear_external_assets();
  this->artwork_image_->set_url(url);
  this->artwork_image_->update();
}

void MediaPage::refresh_external_assets() {
  if (this->artwork_ == nullptr || this->artwork_image_ == nullptr || !this->artwork_image_->is_loaded()) return;
  lv_image_set_src(this->artwork_, this->artwork_image_->get_lv_image_dsc());
  lv_obj_remove_flag(this->artwork_, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(this->artwork_placeholder_, LV_OBJ_FLAG_HIDDEN);
  lv_obj_invalidate(this->artwork_frame_);
}

void MediaPage::clear_external_assets() {
  if (this->artwork_ == nullptr) return;
  lv_obj_add_flag(this->artwork_, LV_OBJ_FLAG_HIDDEN);
  lv_obj_remove_flag(this->artwork_placeholder_, LV_OBJ_FLAG_HIDDEN);
  lv_obj_invalidate(this->artwork_frame_);
}

}  // namespace ui_engine
}  // namespace esphome
