#include "cover_page.h"
#include "visual_theme.h"

#include <set>

namespace esphome {
namespace ui_engine {

void CoverPage::create(lv_obj_t *parent) {
  lv_obj_clean(parent);
  visual_theme::page(parent);

  this->title_ = lv_label_create(parent);
  visual_theme::title(this->title_);
  lv_obj_align(this->title_, LV_ALIGN_TOP_MID, 0, 10);

  this->previous_button_ = lv_button_create(parent);
  lv_obj_set_size(this->previous_button_, 34, 32);
  lv_obj_set_pos(this->previous_button_, 5, 4);
  visual_theme::navigation(this->previous_button_);
  lv_obj_t *previous_label = lv_label_create(this->previous_button_);
  lv_label_set_text(previous_label, "<");
  lv_obj_center(previous_label);
  lv_obj_add_event_cb(this->previous_button_, previous_callback, LV_EVENT_CLICKED, this);

  this->next_button_ = lv_button_create(parent);
  lv_obj_set_size(this->next_button_, 34, 32);
  lv_obj_set_pos(this->next_button_, 281, 4);
  visual_theme::navigation(this->next_button_);
  lv_obj_t *next_label = lv_label_create(this->next_button_);
  lv_label_set_text(next_label, ">");
  lv_obj_center(next_label);
  lv_obj_add_event_cb(this->next_button_, next_callback, LV_EVENT_CLICKED, this);

  this->position_label_ = lv_label_create(parent);
  lv_obj_set_style_text_font(this->position_label_, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(this->position_label_, LV_ALIGN_TOP_MID, 0, 43);

  this->state_label_ = lv_label_create(parent);
  lv_obj_set_style_text_color(this->state_label_, lv_color_hex(visual_theme::TEXT_MUTED), LV_PART_MAIN);
  lv_obj_align(this->state_label_, LV_ALIGN_TOP_MID, 0, 101);

  this->open_button_ = lv_button_create(parent);
  lv_obj_set_size(this->open_button_, 148, 42);
  lv_obj_set_pos(this->open_button_, 8, 128);
  visual_theme::card(this->open_button_);
  this->open_label_ = lv_label_create(this->open_button_);
  lv_obj_center(this->open_label_);
  lv_obj_add_event_cb(this->open_button_, open_callback, LV_EVENT_CLICKED, this);

  this->close_button_ = lv_button_create(parent);
  lv_obj_set_size(this->close_button_, 148, 42);
  lv_obj_set_pos(this->close_button_, 164, 128);
  visual_theme::card(this->close_button_);
  this->close_label_ = lv_label_create(this->close_button_);
  lv_obj_center(this->close_label_);
  lv_obj_add_event_cb(this->close_button_, close_callback, LV_EVENT_CLICKED, this);

  this->close_step_button_ = lv_button_create(parent);
  lv_obj_set_size(this->close_step_button_, 148, 42);
  lv_obj_set_pos(this->close_step_button_, 8, 180);
  visual_theme::card(this->close_step_button_);
  this->close_step_label_ = lv_label_create(this->close_step_button_);
  lv_obj_center(this->close_step_label_);
  lv_obj_add_event_cb(this->close_step_button_, close_step_callback, LV_EVENT_CLICKED, this);

  this->open_step_button_ = lv_button_create(parent);
  lv_obj_set_size(this->open_step_button_, 148, 42);
  lv_obj_set_pos(this->open_step_button_, 164, 180);
  visual_theme::card(this->open_step_button_);
  this->open_step_label_ = lv_label_create(this->open_step_button_);
  lv_obj_center(this->open_step_label_);
  lv_obj_add_event_cb(this->open_step_button_, open_step_callback, LV_EVENT_CLICKED, this);
}

void CoverPage::apply(const PageConfig &config) {
  lv_label_set_text(this->title_, config.title.c_str());
  for (const auto &control : config.controls) {
    if (control.role == "position") {
      this->position_id_ = control.id;
      this->position_color_ = control.color;
    } else if (control.role == "state") {
      this->state_id_ = control.id;
    } else if (control.role == "open") {
      this->open_id_ = control.id;
      this->open_action_ = control.action.empty() ? "open" : control.action;
      lv_label_set_text(this->open_label_, control.caption.c_str());
      lv_obj_set_style_bg_color(this->open_button_, lv_color_hex(control.color), LV_PART_MAIN);
    } else if (control.role == "close") {
      this->close_id_ = control.id;
      this->close_action_ = control.action.empty() ? "close" : control.action;
      lv_label_set_text(this->close_label_, control.caption.c_str());
      lv_obj_set_style_bg_color(this->close_button_, lv_color_hex(control.color), LV_PART_MAIN);
    } else if (control.role == "close_step") {
      this->close_step_id_ = control.id;
      this->close_step_action_ = control.action.empty() ? "close_step" : control.action;
      lv_label_set_text(this->close_step_label_, control.caption.c_str());
      lv_obj_set_style_bg_color(this->close_step_button_, lv_color_hex(control.color), LV_PART_MAIN);
    } else if (control.role == "open_step") {
      this->open_step_id_ = control.id;
      this->open_step_action_ = control.action.empty() ? "open_step" : control.action;
      lv_label_set_text(this->open_step_label_, control.caption.c_str());
      lv_obj_set_style_bg_color(this->open_step_button_, lv_color_hex(control.color), LV_PART_MAIN);
    }
  }
  this->position_value_.clear();
  this->state_value_.clear();
  this->position_state_ = ControlState::UNKNOWN;
  this->state_state_ = ControlState::UNKNOWN;
  this->apply_value_state();
}

bool CoverPage::update_control(const std::string &id, bool active, const std::string &value, ControlState state) {
  if (id == this->position_id_) {
    this->position_value_ = value;
    this->position_state_ = state;
    this->apply_value_state();
    return true;
  }
  if (id == this->state_id_) {
    this->state_value_ = value;
    this->state_state_ = state;
    this->apply_value_state();
    return true;
  }
  return id == this->open_id_ || id == this->close_id_ || id == this->close_step_id_ || id == this->open_step_id_;
}

void CoverPage::set_all_states(ControlState state) {
  this->position_state_ = state;
  this->state_state_ = state;
  this->apply_value_state();
}

bool CoverPage::validate(const PageConfig &config, std::string *error) const {
  if (config.template_name != "cover" || config.variant != "position_controls") {
    *error = "Cover requiere template=cover y variant=position_controls";
    return false;
  }
  const std::set<std::string> required = {"position", "state", "open", "close", "close_step", "open_step"};
  const std::set<std::string> legacy = {"position", "state", "open", "stop", "close"};
  std::set<std::string> found;
  for (const auto &control : config.controls) {
    found.insert(control.role);
    const bool value_role = control.role == "position" || control.role == "state";
    if ((value_role && control.type != "value") || (!value_role && control.type != "button")) {
      *error = "Cover requiere value para estado/posicion y button para acciones";
      return false;
    }
  }
  if (found != required && found != legacy) {
    *error = "Cover requiere los seis roles o el formato anterior compatible";
    return false;
  }
  return true;
}

void CoverPage::set_navigation_enabled(bool enabled) {
  if (enabled) {
    lv_obj_remove_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_remove_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_obj_add_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  }
}

void CoverPage::previous_callback(lv_event_t *event) {
  auto *page = static_cast<CoverPage *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(-1);
}

void CoverPage::next_callback(lv_event_t *event) {
  auto *page = static_cast<CoverPage *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(1);
}

void CoverPage::open_callback(lv_event_t *event) {
  auto *page = static_cast<CoverPage *>(lv_event_get_user_data(event));
  page->emit_action(page->open_id_, page->open_action_);
}

void CoverPage::close_callback(lv_event_t *event) {
  auto *page = static_cast<CoverPage *>(lv_event_get_user_data(event));
  page->emit_action(page->close_id_, page->close_action_);
}

void CoverPage::close_step_callback(lv_event_t *event) {
  auto *page = static_cast<CoverPage *>(lv_event_get_user_data(event));
  page->emit_action(page->close_step_id_, page->close_step_action_);
}

void CoverPage::open_step_callback(lv_event_t *event) {
  auto *page = static_cast<CoverPage *>(lv_event_get_user_data(event));
  page->emit_action(page->open_step_id_, page->open_step_action_);
}

void CoverPage::emit_action(const std::string &id, const std::string &action) {
  if (!id.empty() && this->action_callback_) this->action_callback_(id, action);
}

void CoverPage::apply_value_state() {
  const bool position_valid = this->position_state_ == ControlState::VALID;
  const bool state_valid = this->state_state_ == ControlState::VALID;
  const std::string position = position_valid ? this->position_value_ + " %" : "-- %";
  const std::string state = state_valid ? this->state_value_ : "Sin datos";
  lv_label_set_text(this->position_label_, position.c_str());
  lv_label_set_text(this->state_label_, state.c_str());
  const uint32_t color = position_valid ? this->position_color_ :
      (this->position_state_ == ControlState::STALE_OR_DISCONNECTED ? 0xD08A00 : 0x6B7C8F);
  lv_obj_set_style_text_color(this->position_label_, lv_color_hex(color), LV_PART_MAIN);
}

}  // namespace ui_engine
}  // namespace esphome
