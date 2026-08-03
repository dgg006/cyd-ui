#include "clock_weather_page.h"

#include <cstdio>
#include <set>

namespace esphome {
namespace ui_engine {

void ClockWeatherPage::create(lv_obj_t *parent) {
  lv_obj_clean(parent);
  lv_obj_set_style_bg_color(parent, lv_color_hex(0x071521), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(parent, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_pad_all(parent, 0, LV_PART_MAIN);

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

  this->time_label_ = lv_label_create(parent);
  lv_label_set_text(this->time_label_, "--:--");
  lv_obj_set_style_text_font(this->time_label_, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->time_label_, lv_color_hex(0xFFFFFF), LV_PART_MAIN);
  lv_obj_align(this->time_label_, LV_ALIGN_TOP_MID, 0, 32);

  this->date_label_ = lv_label_create(parent);
  lv_label_set_text(this->date_label_, "Esperando hora...");
  lv_obj_set_style_text_color(this->date_label_, lv_color_hex(0x9FB6C5), LV_PART_MAIN);
  lv_obj_align(this->date_label_, LV_ALIGN_TOP_MID, 0, 94);

  this->condition_label_ = lv_label_create(parent);
  lv_label_set_text(this->condition_label_, "Sin clima");
  lv_obj_set_style_text_color(this->condition_label_, lv_color_hex(0x90CAF9), LV_PART_MAIN);
  lv_obj_align(this->condition_label_, LV_ALIGN_TOP_MID, 0, 124);

  this->temperature_label_ = lv_label_create(parent);
  lv_label_set_text(this->temperature_label_, "--.- C");
  lv_obj_set_style_text_font(this->temperature_label_, &lv_font_montserrat_32, LV_PART_MAIN);
  lv_obj_set_style_text_color(this->temperature_label_, lv_color_hex(0xFFFFFF), LV_PART_MAIN);
  lv_obj_align(this->temperature_label_, LV_ALIGN_TOP_MID, 0, 146);

  this->humidity_label_ = lv_label_create(parent);
  lv_label_set_text(this->humidity_label_, "Humedad -- %");
  lv_obj_set_style_text_color(this->humidity_label_, lv_color_hex(0x80CBC4), LV_PART_MAIN);
  lv_obj_align(this->humidity_label_, LV_ALIGN_BOTTOM_MID, 0, -30);

  lv_obj_t *hint = lv_label_create(parent);
  lv_label_set_text(hint, "Toca para volver");
  lv_obj_set_style_text_color(hint, lv_color_hex(0x526A79), LV_PART_MAIN);
  lv_obj_align(hint, LV_ALIGN_BOTTOM_MID, 0, -8);
}

void ClockWeatherPage::loop() {
  if (millis() - this->last_clock_update_ >= 1000) {
    this->last_clock_update_ = millis();
    this->update_clock_();
  }
}

void ClockWeatherPage::apply(const PageConfig &config) {
  for (const auto &control : config.controls) {
    if (control.role == "condition") this->condition_id_ = control.id;
    else if (control.role == "outside_temperature") this->temperature_id_ = control.id;
    else if (control.role == "humidity") this->humidity_id_ = control.id;
  }
  this->update_clock_();
}

bool ClockWeatherPage::update_control(const std::string &id, bool active, const std::string &value,
                                      ControlState state) {
  if (id == this->condition_id_) {
    lv_label_set_text(this->condition_label_, state == ControlState::VALID ? translate_condition_(value) : "Sin clima");
    return true;
  }
  if (id == this->temperature_id_) {
    const std::string text = state == ControlState::VALID ? value + " C" : "--.- C";
    lv_label_set_text(this->temperature_label_, text.c_str());
    return true;
  }
  if (id == this->humidity_id_) {
    const std::string text = state == ControlState::VALID ? "Humedad " + value + " %" : "Humedad -- %";
    lv_label_set_text(this->humidity_label_, text.c_str());
    return true;
  }
  return false;
}

void ClockWeatherPage::set_all_states(ControlState state) {
  if (state != ControlState::VALID) {
    lv_label_set_text(this->condition_label_, "Sin clima");
    lv_label_set_text(this->temperature_label_, "--.- C");
    lv_label_set_text(this->humidity_label_, "Humedad -- %");
  }
}

bool ClockWeatherPage::validate(const PageConfig &config, std::string *error) const {
  if (config.template_name != "clock_weather" || config.variant != "screensaver") {
    *error = "ClockWeather requiere template=clock_weather y variant=screensaver";
    return false;
  }
  const std::set<std::string> required = {"condition", "outside_temperature", "humidity"};
  std::set<std::string> found;
  for (const auto &control : config.controls) {
    if (control.type != "value") {
      *error = "ClockWeather solo admite controles type=value";
      return false;
    }
    found.insert(control.role);
  }
  if (found != required) {
    *error = "ClockWeather requiere condition, outside_temperature y humidity";
    return false;
  }
  return true;
}

void ClockWeatherPage::set_navigation_enabled(bool enabled) {
  if (enabled) {
    lv_obj_remove_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_remove_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_obj_add_flag(this->previous_button_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(this->next_button_, LV_OBJ_FLAG_HIDDEN);
  }
}

void ClockWeatherPage::previous_callback(lv_event_t *event) {
  auto *page = static_cast<ClockWeatherPage *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(-1);
}

void ClockWeatherPage::next_callback(lv_event_t *event) {
  auto *page = static_cast<ClockWeatherPage *>(lv_event_get_user_data(event));
  if (page->navigation_callback_) page->navigation_callback_(1);
}

void ClockWeatherPage::update_clock_() {
  if (this->clock_ == nullptr) return;
  const ESPTime now = this->clock_->now();
  if (!now.is_valid()) return;

  char time_text[6];
  std::snprintf(time_text, sizeof(time_text), "%02u:%02u", now.hour, now.minute);
  lv_label_set_text(this->time_label_, time_text);

  static const char *const DAYS[] = {"", "Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"};
  static const char *const MONTHS[] = {"", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                                      "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"};
  char date_text[48];
  std::snprintf(date_text, sizeof(date_text), "%s %u de %s", DAYS[now.day_of_week], now.day_of_month,
                MONTHS[now.month]);
  lv_label_set_text(this->date_label_, date_text);
}

const char *ClockWeatherPage::translate_condition_(const std::string &condition) {
  if (condition == "sunny" || condition == "clear-night") return "Despejado";
  if (condition == "cloudy") return "Nublado";
  if (condition == "partlycloudy") return "Parcial nublado";
  if (condition == "rainy" || condition == "pouring") return "Lluvia";
  if (condition == "lightning" || condition == "lightning-rainy") return "Tormenta";
  if (condition == "fog") return "Niebla";
  if (condition == "windy" || condition == "windy-variant") return "Ventoso";
  if (condition == "snowy" || condition == "snowy-rainy") return "Nieve";
  return condition.empty() ? "Sin clima" : condition.c_str();
}

}  // namespace ui_engine
}  // namespace esphome
