#include "sensor_grid.h"

namespace esphome {
namespace ui_engine {

void SensorGrid::create(lv_obj_t *parent) {
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

  for (size_t index = 0; index < this->cards_.size(); index++) {
    const int column = index % 2;
    const int row = index / 2;
    lv_obj_t *card = lv_obj_create(parent);
    lv_obj_set_size(card, 148, 82);
    lv_obj_set_pos(card, 8 + column * 156, 46 + row * 92);
    lv_obj_set_style_radius(card, 10, LV_PART_MAIN);
    lv_obj_set_style_border_width(card, 2, LV_PART_MAIN);
    lv_obj_set_style_pad_all(card, 7, LV_PART_MAIN);
    lv_obj_remove_flag(card, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *caption = lv_label_create(card);
    lv_obj_set_style_text_color(caption, lv_color_hex(0x9FB6C5), LV_PART_MAIN);
    lv_obj_align(caption, LV_ALIGN_TOP_MID, 0, 0);

    lv_obj_t *value = lv_label_create(card);
    lv_obj_set_style_text_font(value, &lv_font_montserrat_32, LV_PART_MAIN);
    lv_obj_align(value, LV_ALIGN_BOTTOM_MID, 0, -1);

    lv_obj_t *icon_label = lv_label_create(card);
    if (this->icon_font_ != nullptr) {
      lv_obj_set_style_text_font(icon_label, this->icon_font_->get_lv_font(), LV_PART_MAIN);
    }
    lv_obj_add_flag(icon_label, LV_OBJ_FLAG_HIDDEN);

    this->cards_[index] = card;
    this->captions_[index] = caption;
    this->icon_labels_[index] = icon_label;
    this->values_[index] = value;
    this->states_[index] = ControlState::UNKNOWN;
  }
}

void SensorGrid::apply(const PageConfig &config) {
  lv_label_set_text(this->title_, config.title.c_str());
  for (size_t index = 0; index < this->cards_.size(); index++) {
    if (index >= config.controls.size()) {
      lv_obj_add_flag(this->cards_[index], LV_OBJ_FLAG_HIDDEN);
      this->ids_[index].clear();
      continue;
    }
    const auto &control = config.controls[index];
    lv_obj_remove_flag(this->cards_[index], LV_OBJ_FLAG_HIDDEN);
    this->ids_[index] = control.id;
    this->units_[index] = control.unit;
    this->colors_[index] = control.color;
    this->icons_[index] = control.resolved_icon;
    this->icons_on_[index] = control.resolved_icon_on;
    this->icons_off_[index] = control.resolved_icon_off;
    this->raw_values_[index].clear();
    this->states_[index] = ControlState::UNKNOWN;
    this->active_[index] = false;
    lv_label_set_text(this->captions_[index], control.caption.c_str());
    this->apply_state_(index);
  }
}

bool SensorGrid::update_control(const std::string &id, bool active, const std::string &value, ControlState state) {
  for (size_t index = 0; index < this->ids_.size(); index++) {
    if (this->ids_[index] == id) {
      this->raw_values_[index] = value;
      this->states_[index] = state;
      this->active_[index] = active;
      this->apply_state_(index);
      return true;
    }
  }
  return false;
}

void SensorGrid::set_all_states(ControlState state) {
  for (size_t index = 0; index < this->ids_.size(); index++) {
    if (!this->ids_[index].empty()) {
      this->states_[index] = state;
      this->apply_state_(index);
    }
  }
}

bool SensorGrid::validate(const PageConfig &config, std::string *error) const {
  if (config.template_name != "sensor_grid" || config.variant != "four_values") {
    *error = "SensorGrid requiere template=sensor_grid y variant=four_values";
    return false;
  }
  if (config.controls.empty() || config.controls.size() > 4) {
    *error = "SensorGrid requiere entre uno y cuatro valores";
    return false;
  }
  for (const auto &control : config.controls) {
    if (control.type != "value") {
      *error = "SensorGrid solo admite controles type=value";
      return false;
    }
  }
  return true;
}

void SensorGrid::set_navigation_enabled(bool enabled) {
  if (enabled) {
    lv_obj_remove_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_remove_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_obj_add_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  }
}

void SensorGrid::previous_callback(lv_event_t *event) {
  auto *page = static_cast<SensorGrid *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(-1);
}

void SensorGrid::next_callback(lv_event_t *event) {
  auto *page = static_cast<SensorGrid *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(1);
}

void SensorGrid::apply_state_(size_t index) {
  const bool valid = this->states_[index] == ControlState::VALID;
  const std::string text = valid ? this->raw_values_[index] + (this->units_[index].empty() ? "" : " " + this->units_[index]) : "--";
  lv_label_set_text(this->values_[index], text.c_str());
  const uint32_t color = valid ? this->colors_[index] :
      (this->states_[index] == ControlState::STALE_OR_DISCONNECTED ? 0xD08A00 : 0x6B7C8F);
  lv_obj_set_style_text_color(this->values_[index], lv_color_hex(color), LV_PART_MAIN);
  lv_obj_set_style_border_color(this->cards_[index], lv_color_hex(color), LV_PART_MAIN);
  lv_obj_set_style_bg_color(this->cards_[index], lv_color_hex(0x182631), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(this->cards_[index], valid ? LV_OPA_COVER : LV_OPA_70, LV_PART_MAIN);

  const char *glyph = this->active_[index] ? this->icons_on_[index] : this->icons_off_[index];
  if (glyph == nullptr) {
    glyph = this->icons_[index];
  }
  if (glyph != nullptr && this->icon_font_ != nullptr) {
    lv_label_set_text(this->icon_labels_[index], glyph);
    lv_obj_set_style_text_color(this->icon_labels_[index], lv_color_hex(color), LV_PART_MAIN);
    lv_obj_remove_flag(this->icon_labels_[index], LV_OBJ_FLAG_HIDDEN);
    lv_obj_align(this->icon_labels_[index], LV_ALIGN_BOTTOM_LEFT, 1, -1);
    lv_obj_set_style_text_font(this->values_[index], &lv_font_montserrat_20, LV_PART_MAIN);
    lv_obj_align(this->values_[index], LV_ALIGN_BOTTOM_RIGHT, -1, -3);
  } else {
    lv_obj_add_flag(this->icon_labels_[index], LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_text_font(this->values_[index], &lv_font_montserrat_32, LV_PART_MAIN);
    lv_obj_align(this->values_[index], LV_ALIGN_BOTTOM_MID, 0, -1);
  }
}

}  // namespace ui_engine
}  // namespace esphome
