#include "media_page.h"

#include <set>

#include "visual_theme.h"

namespace esphome {
namespace ui_engine {

namespace {
constexpr const char *VALUE_ROLES[] = {"player", "title", "artist", "station", "volume"};
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

  this->previous_player_ = make_nav(48, previous_player_callback, "<");
  lv_obj_set_pos(this->previous_player_, 48, 36);
  this->next_player_ = make_nav(238, next_player_callback, ">");
  lv_obj_set_pos(this->next_player_, 238, 36);

  this->player_ = lv_label_create(parent);
  lv_obj_set_width(this->player_, 145);
  lv_obj_set_style_text_align(this->player_, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->player_, lv_color_hex(visual_theme::ACCENT), LV_PART_MAIN);
  lv_label_set_long_mode(this->player_, LV_LABEL_LONG_DOT);
  lv_obj_set_pos(this->player_, 87, 42);

  this->media_title_ = lv_label_create(parent);
  lv_obj_set_width(this->media_title_, 286);
  if (this->text_font_ != nullptr)
    lv_obj_set_style_text_font(this->media_title_, this->text_font_->get_lv_font(), LV_PART_MAIN);
  lv_obj_set_style_text_align(this->media_title_, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_label_set_long_mode(this->media_title_, LV_LABEL_LONG_DOT);
  lv_obj_set_pos(this->media_title_, 17, 72);

  this->artist_ = lv_label_create(parent);
  lv_obj_set_width(this->artist_, 286);
  lv_obj_set_style_text_align(this->artist_, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->artist_, lv_color_hex(visual_theme::TEXT_MUTED), LV_PART_MAIN);
  lv_label_set_long_mode(this->artist_, LV_LABEL_LONG_DOT);
  lv_obj_set_pos(this->artist_, 17, 99);

  this->station_ = lv_label_create(parent);
  lv_obj_set_width(this->station_, 286);
  lv_obj_set_style_text_align(this->station_, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->station_, lv_color_hex(visual_theme::TEXT_MUTED), LV_PART_MAIN);
  lv_label_set_long_mode(this->station_, LV_LABEL_LONG_DOT);
  lv_obj_set_pos(this->station_, 17, 119);

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
  make_button("previous", 42, 140, 64, 43);
  make_button("play_pause", 128, 140, 64, 43);
  make_button("next", 214, 140, 64, 43);
  make_button("volume_down", 54, 194, 52, 36);
  make_button("volume_up", 214, 194, 52, 36);

  this->volume_ = lv_label_create(parent);
  lv_obj_set_width(this->volume_, 96);
  lv_obj_set_style_text_align(this->volume_, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_pos(this->volume_, 112, 204);
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
}

bool MediaPage::update_control(const std::string &id, bool active, const std::string &value, ControlState state) {
  for (const auto &item : this->ids_) {
    if (item.second != id) continue;
    this->values_[item.first] = value;
    this->states_[item.first] = state;
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
  const std::set<std::string> value_roles = {"player", "title", "artist", "station", "volume"};
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
    *error = "Media requiere sus diez roles completos";
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
void MediaPage::previous_player_callback(lv_event_t *event) {
  auto *page = static_cast<MediaPage *>(lv_event_get_user_data(event));
  page->emit(page->ids_["player"], "previous_player");
}
void MediaPage::next_player_callback(lv_event_t *event) {
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
}

}  // namespace ui_engine
}  // namespace esphome
