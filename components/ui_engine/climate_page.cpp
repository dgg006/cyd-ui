#include "climate_page.h"

#include <set>

#include "esphome/core/hal.h"

namespace esphome {
namespace ui_engine {

void ClimatePage::loop() {
  if (this->power_confirmation_pending_ &&
      static_cast<int32_t>(millis() - this->power_confirmation_deadline_ms_) >= 0) {
    this->power_confirmation_pending_ = false;
    this->apply_power_state();
  }
}

void ClimatePage::create(lv_obj_t *parent) {
  lv_obj_clean(parent);
  lv_obj_set_style_bg_color(parent, lv_color_hex(0x101820), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(parent, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_pad_all(parent, 0, LV_PART_MAIN);

  this->title_ = lv_label_create(parent);
  lv_obj_set_style_text_color(this->title_, lv_color_hex(0xFFFFFF), LV_PART_MAIN);
  lv_obj_align(this->title_, LV_ALIGN_TOP_MID, 0, 10);

  this->previous_button_ = lv_button_create(parent);
  lv_obj_set_size(this->previous_button_, 34, 32);
  lv_obj_set_pos(this->previous_button_, 5, 4);
  lv_obj_t *previous_label = lv_label_create(this->previous_button_);
  lv_label_set_text(previous_label, "<");
  lv_obj_center(previous_label);
  lv_obj_add_event_cb(this->previous_button_, previous_callback, LV_EVENT_CLICKED, this);

  this->next_button_ = lv_button_create(parent);
  lv_obj_set_size(this->next_button_, 34, 32);
  lv_obj_set_pos(this->next_button_, 281, 4);
  lv_obj_t *next_label = lv_label_create(this->next_button_);
  lv_label_set_text(next_label, ">");
  lv_obj_center(next_label);
  lv_obj_add_event_cb(this->next_button_, next_callback, LV_EVENT_CLICKED, this);

  this->current_label_ = lv_label_create(parent);
  lv_label_set_text(this->current_label_, "Actual: --.- C");
  lv_obj_set_style_text_color(this->current_label_, lv_color_hex(0xFFFFFF), LV_PART_MAIN);
  lv_obj_align(this->current_label_, LV_ALIGN_TOP_MID, 0, 58);

  this->target_label_ = lv_label_create(parent);
  lv_label_set_text(this->target_label_, "Objetivo: --.- C");
  lv_obj_set_style_text_color(this->target_label_, lv_color_hex(0x9FD3FF), LV_PART_MAIN);
  lv_obj_align(this->target_label_, LV_ALIGN_TOP_MID, 0, 102);

  this->decrease_button_ = lv_button_create(parent);
  lv_obj_set_size(this->decrease_button_, 88, 62);
  lv_obj_set_pos(this->decrease_button_, 8, 158);
  this->decrease_label_ = lv_label_create(this->decrease_button_);
  lv_label_set_text(this->decrease_label_, "-");
  lv_obj_center(this->decrease_label_);
  lv_obj_add_event_cb(this->decrease_button_, decrease_callback, LV_EVENT_CLICKED, this);

  this->power_button_ = lv_button_create(parent);
  lv_obj_set_size(this->power_button_, 112, 62);
  lv_obj_set_pos(this->power_button_, 104, 158);
  this->power_label_ = lv_label_create(this->power_button_);
  lv_label_set_text(this->power_label_, "Encender");
  lv_obj_center(this->power_label_);
  lv_obj_add_event_cb(this->power_button_, power_callback, LV_EVENT_CLICKED, this);

  this->increase_button_ = lv_button_create(parent);
  lv_obj_set_size(this->increase_button_, 88, 62);
  lv_obj_set_pos(this->increase_button_, 224, 158);
  this->increase_label_ = lv_label_create(this->increase_button_);
  lv_label_set_text(this->increase_label_, "+");
  lv_obj_center(this->increase_label_);
  lv_obj_add_event_cb(this->increase_button_, increase_callback, LV_EVENT_CLICKED, this);
}

void ClimatePage::apply(const PageConfig &config) {
  lv_label_set_text(this->title_, config.title.c_str());
  for (const auto &control : config.controls) {
    if (control.role == "current_temperature") {
      this->current_id_ = control.id;
    } else if (control.role == "target_temperature") {
      this->target_id_ = control.id;
    } else if (control.role == "decrease") {
      this->decrease_id_ = control.id;
      this->decrease_action_ = control.action.empty() ? "decrement" : control.action;
      lv_label_set_text(this->decrease_label_, control.caption.c_str());
    } else if (control.role == "power") {
      this->power_id_ = control.id;
      this->power_action_ = control.action.empty() ? "toggle" : control.action;
      this->power_color_ = control.color;
      lv_label_set_text(this->power_label_, control.caption.c_str());
    } else if (control.role == "increase") {
      this->increase_id_ = control.id;
      this->increase_action_ = control.action.empty() ? "increment" : control.action;
      lv_label_set_text(this->increase_label_, control.caption.c_str());
    }
  }
  this->apply_power_state();
}

bool ClimatePage::update_control(const std::string &id, bool active, const std::string &value, ControlState state) {
  if (id == this->current_id_) {
    const std::string text = state == ControlState::VALID ? "Actual: " + value + " C" : "Actual: --.- C";
    lv_label_set_text(this->current_label_, text.c_str());
    return true;
  }
  if (id == this->target_id_) {
    const std::string text = state == ControlState::VALID ? "Objetivo: " + value + " C" : "Objetivo: --.- C";
    lv_label_set_text(this->target_label_, text.c_str());
    return true;
  }
  if (id == this->power_id_) {
    this->power_confirmation_pending_ = false;
    this->power_active_ = active;
    this->power_state_ = state;
    this->apply_power_state();
    return true;
  }
  return id == this->decrease_id_ || id == this->increase_id_;
}

void ClimatePage::set_all_states(ControlState state) {
  this->power_confirmation_pending_ = false;
  this->power_state_ = state;
  this->apply_power_state();
  if (state != ControlState::VALID) {
    lv_label_set_text(this->current_label_, "Actual: --.- C");
    lv_label_set_text(this->target_label_, "Objetivo: --.- C");
  }
}

bool ClimatePage::validate(const PageConfig &config, std::string *error) const {
  if (config.template_name != "climate" || config.variant != "thermostat") {
    *error = "Climate requiere template=climate y variant=thermostat";
    return false;
  }
  const std::set<std::string> required = {"current_temperature", "target_temperature", "decrease", "power", "increase"};
  std::set<std::string> found;
  for (const auto &control : config.controls) {
    found.insert(control.role);
    const bool value_role = control.role == "current_temperature" || control.role == "target_temperature";
    if ((value_role && control.type != "value") || (!value_role && control.type != "button")) {
      *error = "Los roles de temperatura requieren value y los controles requieren button";
      return false;
    }
  }
  if (found != required) {
    *error = "Climate requiere los cinco roles del thermostat";
    return false;
  }
  return true;
}

void ClimatePage::set_navigation_enabled(bool enabled) {
  if (enabled) {
    lv_obj_remove_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_remove_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_obj_add_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  }
}

void ClimatePage::previous_callback(lv_event_t *event) {
  auto *page = static_cast<ClimatePage *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(-1);
}
void ClimatePage::next_callback(lv_event_t *event) {
  auto *page = static_cast<ClimatePage *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(1);
}
void ClimatePage::decrease_callback(lv_event_t *event) {
  auto *page = static_cast<ClimatePage *>(lv_event_get_user_data(event));
  page->emit_action(page->decrease_id_, page->decrease_action_);
}
void ClimatePage::power_callback(lv_event_t *event) {
  auto *page = static_cast<ClimatePage *>(lv_event_get_user_data(event));
  if (page->power_state_ != ControlState::VALID) return;

  if (page->power_active_) {
    page->power_confirmation_pending_ = false;
    page->emit_action(page->power_id_, page->power_action_);
    return;
  }

  if (page->power_confirmation_pending_ &&
      static_cast<int32_t>(page->power_confirmation_deadline_ms_ - millis()) > 0) {
    page->power_confirmation_pending_ = false;
    page->emit_action(page->power_id_, page->power_action_);
    return;
  }

  page->power_confirmation_pending_ = true;
  page->power_confirmation_deadline_ms_ = millis() + 3000U;
  page->apply_power_state();
}
void ClimatePage::increase_callback(lv_event_t *event) {
  auto *page = static_cast<ClimatePage *>(lv_event_get_user_data(event));
  page->emit_action(page->increase_id_, page->increase_action_);
}

void ClimatePage::emit_action(const std::string &id, const std::string &action) {
  if (!id.empty() && this->action_callback_) this->action_callback_(id, action);
}

void ClimatePage::apply_power_state() {
  uint32_t color = 0x3B4652;
  lv_opa_t opacity = LV_OPA_70;
  if (this->power_state_ == ControlState::VALID) {
    color = this->power_active_ ? this->power_color_ : 0x27313B;
    opacity = LV_OPA_COVER;
  } else if (this->power_state_ == ControlState::STALE_OR_DISCONNECTED) {
    color = 0x7A4E00;
    opacity = LV_OPA_80;
  }
  lv_obj_set_style_bg_color(this->power_button_, lv_color_hex(color), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(this->power_button_, opacity, LV_PART_MAIN);

  const char *label = "Estado";
  if (this->power_confirmation_pending_) {
    label = "Confirmar";
    lv_obj_set_style_bg_color(this->power_button_, lv_color_hex(0xD84315), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(this->power_button_, LV_OPA_COVER, LV_PART_MAIN);
  } else if (this->power_state_ == ControlState::VALID) {
    label = this->power_active_ ? "Apagar" : "Encender";
  } else if (this->power_state_ == ControlState::STALE_OR_DISCONNECTED) {
    label = "Sin red";
  }
  lv_label_set_text(this->power_label_, label);
}

}  // namespace ui_engine
}  // namespace esphome
