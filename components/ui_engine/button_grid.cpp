#include "button_grid.h"
#include "visual_theme.h"

namespace esphome {
namespace ui_engine {

void ButtonGrid::create(lv_obj_t *parent) {
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

  for (size_t index = 0; index < this->buttons_.size(); index++) {
    const int column = index % 3;
    const int row = index / 3;

    lv_obj_t *button = lv_button_create(parent);
    lv_obj_set_size(button, 96, 82);
    lv_obj_set_pos(button, 8 + column * 104, 46 + row * 92);
    visual_theme::card(button);

    lv_obj_t *label = lv_label_create(button);
    lv_obj_center(label);

    lv_obj_t *icon_label = lv_label_create(button);
    if (this->icon_font_ != nullptr) {
      lv_obj_set_style_text_font(icon_label, this->icon_font_->get_lv_font(), LV_PART_MAIN);
    }
    lv_obj_add_flag(icon_label, LV_OBJ_FLAG_HIDDEN);

    this->bindings_[index] = {this, index};
    lv_obj_add_event_cb(button, event_callback, LV_EVENT_CLICKED, &this->bindings_[index]);

    this->buttons_[index] = button;
    this->labels_[index] = label;
    this->icon_labels_[index] = icon_label;
    this->states_[index] = ControlState::UNKNOWN;
    this->active_[index] = false;
  }
}

void ButtonGrid::apply(const PageConfig &config) {
  lv_label_set_text(this->title_, config.title.c_str());
  this->apply_layout(config.variant);

  for (size_t index = 0; index < this->buttons_.size(); index++) {
    if (index >= config.controls.size()) {
      lv_obj_add_flag(this->buttons_[index], LV_OBJ_FLAG_HIDDEN);
      this->ids_[index].clear();
      continue;
    }
    const auto &control = config.controls[index];
    lv_obj_remove_flag(this->buttons_[index], LV_OBJ_FLAG_HIDDEN);
    this->ids_[index] = control.id;
    this->actions_[index] = control.action.empty() ? "toggle" : control.action;
    this->icons_[index] = control.resolved_icon;
    this->icons_on_[index] = control.resolved_icon_on;
    this->icons_off_[index] = control.resolved_icon_off;
    this->colors_[index] = control.color;
    this->states_[index] = ControlState::UNKNOWN;
    this->active_[index] = false;
    lv_label_set_text(this->labels_[index], control.caption.c_str());
    this->apply_state(index);
  }
}

bool ButtonGrid::validate(const PageConfig &config, std::string *error) const {
  if (config.template_name != "button_grid") {
    *error = "ButtonGrid requiere template=button_grid";
    return false;
  }
  size_t maximum = 0;
  if (config.variant == "two_buttons") {
    maximum = 2;
  } else if (config.variant == "four_buttons") {
    maximum = 4;
  } else if (config.variant == "six_buttons") {
    maximum = 6;
  } else {
    *error = "ButtonGrid requiere variant=two_buttons, four_buttons o six_buttons";
    return false;
  }
  if (config.controls.empty() || config.controls.size() > maximum) {
    *error = "La cantidad de controles supera la capacidad de la variante";
    return false;
  }
  for (const auto &control : config.controls) {
    if (control.type != "button") {
      *error = "ButtonGrid solo admite controles type=button";
      return false;
    }
  }
  return true;
}

void ButtonGrid::apply_layout(const std::string &variant) {
  if (variant == "two_buttons") {
    for (size_t index = 0; index < 2; index++) {
      lv_obj_set_size(this->buttons_[index], 148, 174);
      lv_obj_set_pos(this->buttons_[index], 8 + static_cast<int>(index) * 156, 46);
    }
    return;
  }

  if (variant == "four_buttons") {
    for (size_t index = 0; index < 4; index++) {
      const int column = index % 2;
      const int row = index / 2;
      lv_obj_set_size(this->buttons_[index], 148, 82);
      lv_obj_set_pos(this->buttons_[index], 8 + column * 156, 46 + row * 92);
    }
    return;
  }

  for (size_t index = 0; index < 6; index++) {
    const int column = index % 3;
    const int row = index / 3;
    lv_obj_set_size(this->buttons_[index], 96, 82);
    lv_obj_set_pos(this->buttons_[index], 8 + column * 104, 46 + row * 92);
  }
}

bool ButtonGrid::update_control(const std::string &id, bool active, const std::string &value, ControlState state) {
  for (size_t index = 0; index < this->ids_.size(); index++) {
    if (this->ids_[index] == id) {
      this->active_[index] = active;
      this->states_[index] = state;
      this->apply_state(index);
      return true;
    }
  }
  return false;
}

void ButtonGrid::set_all_states(ControlState state) {
  for (size_t index = 0; index < this->ids_.size(); index++) {
    if (!this->ids_[index].empty()) {
      this->states_[index] = state;
      this->apply_state(index);
    }
  }
}

void ButtonGrid::event_callback(lv_event_t *event) {
  auto *binding = static_cast<EventBinding *>(lv_event_get_user_data(event));
  binding->grid->handle_click(binding->index);
}

void ButtonGrid::previous_callback(lv_event_t *event) {
  auto *grid = static_cast<ButtonGrid *>(lv_event_get_user_data(event));
  if (grid->navigation_callback_) {
    grid->navigation_callback_(-1);
  }
}

void ButtonGrid::next_callback(lv_event_t *event) {
  auto *grid = static_cast<ButtonGrid *>(lv_event_get_user_data(event));
  if (grid->navigation_callback_) {
    grid->navigation_callback_(1);
  }
}

void ButtonGrid::set_navigation_enabled(bool enabled) {
  if (this->previous_button_ == nullptr || this->next_button_ == nullptr) {
    return;
  }
  if (enabled) {
    lv_obj_remove_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_remove_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_obj_add_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  }
}

void ButtonGrid::handle_click(size_t index) {
  if (this->ids_[index].empty()) {
    return;
  }
  if (this->action_callback_) {
    this->action_callback_(this->ids_[index], this->actions_[index]);
  }
}

void ButtonGrid::apply_state(size_t index) {
  lv_color_t color;
  lv_opa_t opacity;

  switch (this->states_[index]) {
    case ControlState::VALID:
      color = this->active_[index] ? lv_color_hex(this->colors_[index]) : lv_color_hex(0x27313B);
      opacity = LV_OPA_COVER;
      break;
    case ControlState::STALE_OR_DISCONNECTED:
      color = lv_color_hex(0x7A4E00);
      opacity = LV_OPA_80;
      break;
    case ControlState::UNKNOWN:
    default:
      color = lv_color_hex(0x3B4652);
      opacity = LV_OPA_70;
      break;
  }

  lv_obj_set_style_bg_color(this->buttons_[index], color, LV_PART_MAIN);
  lv_obj_set_style_bg_opa(this->buttons_[index], opacity, LV_PART_MAIN);
  lv_obj_set_style_border_color(this->buttons_[index],
                                lv_color_hex(this->states_[index] == ControlState::VALID && this->active_[index]
                                                 ? this->colors_[index]
                                                 : visual_theme::BORDER),
                                LV_PART_MAIN);

  const char *glyph = this->active_[index] ? this->icons_on_[index] : this->icons_off_[index];
  if (glyph == nullptr) {
    glyph = this->icons_[index];
  }
  if (glyph != nullptr && this->icon_font_ != nullptr) {
    lv_label_set_text(this->icon_labels_[index], glyph);
    lv_obj_set_style_text_color(this->icon_labels_[index], lv_color_hex(0xFFFFFF), LV_PART_MAIN);
    lv_obj_remove_flag(this->icon_labels_[index], LV_OBJ_FLAG_HIDDEN);
    lv_obj_align(this->icon_labels_[index], LV_ALIGN_CENTER, 0, -12);
    lv_obj_align(this->labels_[index], LV_ALIGN_BOTTOM_MID, 0, -5);
  } else {
    lv_obj_add_flag(this->icon_labels_[index], LV_OBJ_FLAG_HIDDEN);
    lv_obj_center(this->labels_[index]);
  }
  lv_obj_set_style_text_color(this->labels_[index], lv_color_hex(visual_theme::TEXT), LV_PART_MAIN);
}

}  // namespace ui_engine
}  // namespace esphome
