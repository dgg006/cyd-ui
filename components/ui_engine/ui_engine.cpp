#include "ui_engine.h"

#include <algorithm>
#include <cmath>

#include "esphome/core/log.h"
#include "visual_theme.h"

namespace esphome {
namespace ui_engine {

static const char *const TAG = "ui_engine";

void UiEngineComponent::setup() {
  this->registry_.register_template("button_grid", []() { return std::make_unique<ButtonGrid>(); });
  this->registry_.register_template("climate", []() { return std::make_unique<ClimatePage>(); });
  this->registry_.register_template("clock_weather", [this]() {
    return std::make_unique<ClockWeatherPage>(this->clock_, this->clock_time_font_, this->clock_date_font_);
  });
  this->registry_.register_template("sensor_grid", []() { return std::make_unique<SensorGrid>(); });
  this->registry_.register_template("cover", []() { return std::make_unique<CoverPage>(); });
  this->registry_.register_template("media", []() { return std::make_unique<MediaPage>(); });
  this->last_activity_ms_ = millis();
  this->flash_storage_.begin();
  auto embedded_provider = std::make_unique<EmbeddedConfigProvider>(this->initial_config_);
  if (this->http_client_ != nullptr && !this->config_url_.empty()) {
    this->config_provider_ = std::make_unique<HttpConfigProvider>(this->http_client_, this->config_url_);
  } else {
    this->config_provider_ = std::make_unique<EmbeddedConfigProvider>(this->initial_config_);
  }

  std::string raw_json;
  std::string error;
  bool applied = false;
  FlashConfigProvider flash_provider(&this->flash_storage_);
  if (flash_provider.fetch(&raw_json, &error)) {
    applied = this->try_apply_config(raw_json);
    if (!applied) {
      ESP_LOGW(TAG, "Cache flash invalida; se usara la configuracion embebida");
    }
  } else {
    ESP_LOGW(TAG, "Cache flash no disponible: %s", error.c_str());
  }

  if (!applied) {
    if (!embedded_provider->fetch(&raw_json, &error) || !this->try_apply_config(raw_json)) {
      ESP_LOGE(TAG, "No se pudo aplicar la configuracion embebida: %s", error.c_str());
      this->mark_failed();
      return;
    }
    ESP_LOGI(TAG, "Configuracion embebida aplicada como respaldo seguro");
  }
  this->show_startup_overlay_();
  ESP_LOGI(TAG, "UI Engine inicializado");
}

void UiEngineComponent::loop() {
  if (this->active_page_ != nullptr) {
    this->active_page_->loop();
  }

  if (!this->startup_finished_ && this->startup_overlay_ != nullptr &&
      static_cast<int32_t>(millis() - this->startup_overlay_hide_at_ms_) >= 0) {
    lv_obj_add_flag(this->startup_overlay_, LV_OBJ_FLAG_HIDDEN);
    this->startup_finished_ = true;
  }

  if (this->calibration_active_ &&
      static_cast<int32_t>(millis() - this->calibration_timeout_at_ms_) >= 0) {
    ESP_LOGW(TAG, "Calibracion tactil cancelada por tiempo agotado");
    this->close_touch_calibration(false);
  }
  if (this->calibration_overlay_ != nullptr && !this->calibration_active_ && this->calibration_close_at_ms_ != 0 &&
      static_cast<int32_t>(millis() - this->calibration_close_at_ms_) >= 0) {
    lv_obj_delete(this->calibration_overlay_);
    this->calibration_overlay_ = nullptr;
    this->calibration_target_ = nullptr;
    this->calibration_label_ = nullptr;
    this->calibration_close_at_ms_ = 0;
  }

  if (this->sound_preview_active_ &&
      static_cast<int32_t>(millis() - this->sound_preview_restore_at_ms_) >= 0) {
    this->sound_preview_active_ = false;
    this->apply_sound_settings();
  }

  if (this->reminder_alarm_active_) {
    const uint32_t now = millis();
    if (static_cast<int32_t>(now - this->reminder_alarm_until_ms_) >= 0) {
      this->stop_reminder_alarm_();
    } else if (static_cast<int32_t>(now - this->reminder_alarm_next_ms_) >= 0) {
      this->play_notification_sound("warning");
      this->reminder_alarm_next_ms_ = now + 4000U;
    }
  }

  if (this->reminder_snooze_until_ms_ != 0 &&
      static_cast<int32_t>(millis() - this->reminder_snooze_until_ms_) >= 0) {
    this->reminder_snooze_until_ms_ = 0;
    this->show_alarm_reminder(this->reminder_id_, this->reminder_title_, this->reminder_message_,
                              this->reminder_level_, this->reminder_alarm_duration_seconds_,
                              this->reminder_snooze_minutes_);
  }

  if (this->wake_pending_) {
    this->wake_pending_ = false;
    const bool was_screensaver = this->screensaver_active_;
    this->idle_active_ = false;
    this->screensaver_active_ = false;
    this->active_idle_mode_ = IdleMode::NONE;
    if (was_screensaver) {
      this->show_page(this->page_before_screensaver_);
    }
    this->apply_backlight();
  }

  if (!this->idle_active_ && this->screensaver_timeout_ms_ > 0 &&
      millis() - this->last_activity_ms_ >= this->screensaver_timeout_ms_) {
    this->enter_idle();
  }

  if (millis() - this->last_display_update_ms_ >= 1000U) {
    this->last_display_update_ms_ = millis();
    this->refresh_idle_mode();
    this->apply_backlight();
  }

  if (this->page_delta_pending_ != 0 && !this->active_config_.pages.empty()) {
    const int page_count = static_cast<int>(this->active_config_.pages.size());
    int next = static_cast<int>(this->active_page_index_);
    for (int attempt = 0; attempt < page_count; attempt++) {
      next = (next + this->page_delta_pending_ + page_count) % page_count;
      if (!this->active_config_.pages[static_cast<size_t>(next)].screensaver) break;
    }
    this->page_delta_pending_ = 0;
    if (this->show_page(static_cast<size_t>(next))) {
      this->navigation_trigger_.trigger(next);
    }
  }

  if (!this->reload_pending_) {
    return;
  }
  this->reload_pending_ = false;

  std::string raw_json;
  std::string error;
  if (!this->config_provider_->fetch(&raw_json, &error)) {
    ESP_LOGE(TAG, "Recarga rechazada: %s", error.c_str());
    return;
  }
  if (!this->try_apply_config(raw_json)) {
    ESP_LOGE(TAG, "La UI activa se conserva porque la recarga fallo");
    return;
  }
  if (this->config_provider_->fetched_from_remote()) {
    if (this->flash_storage_.save(raw_json, &error)) {
      ESP_LOGI(TAG, "Configuracion HTTP guardada en cache flash");
    } else {
      ESP_LOGW(TAG, "No se pudo guardar cache flash: %s", error.c_str());
    }
  }
  ESP_LOGI(TAG, "Configuracion recargada");
}

bool UiEngineComponent::apply_config(const std::string &raw_json) {
  if (!this->try_apply_config(raw_json)) {
    ESP_LOGE(TAG, "Configuracion recibida por API rechazada; se conserva la UI activa");
    return false;
  }

  std::string error;
  if (!this->flash_storage_.save(raw_json, &error)) {
    ESP_LOGW(TAG, "Configuracion aplicada, pero no se pudo guardar en flash: %s", error.c_str());
  } else {
    ESP_LOGI(TAG, "Configuracion recibida por API aplicada y guardada en flash");
  }
  return true;
}

bool UiEngineComponent::try_apply_config(const std::string &raw_json) {
  UiConfig candidate;
  std::string error;
  if (!this->parser_.parse(raw_json, &candidate, &error)) {
    ESP_LOGE(TAG, "Configuracion rechazada: %s", error.c_str());
    return false;
  }

  for (const auto &page_config : candidate.pages) {
    auto validator = this->registry_.create(page_config.template_name);
    if (validator == nullptr) {
      ESP_LOGE(TAG, "Template no registrado: %s", page_config.template_name.c_str());
      return false;
    }
    if (!validator->validate(page_config, &error)) {
      ESP_LOGE(TAG, "Configuracion rechazada: %s", error.c_str());
      return false;
    }
  }

  int screensaver_index = -1;
  for (size_t index = 0; index < candidate.pages.size(); index++) {
    if (!candidate.pages[index].screensaver) continue;
    if (screensaver_index >= 0) {
      ESP_LOGE(TAG, "Solo puede existir una pagina screensaver");
      return false;
    }
    screensaver_index = static_cast<int>(index);
  }

  this->active_config_ = std::move(candidate);
  visual_theme::configure(this->active_config_.settings.appearance.light_mode,
                           this->active_config_.settings.appearance.accent);
  const int32_t configured_timeout = this->active_config_.settings.inactivity.timeout_seconds;
  this->screensaver_timeout_ms_ = configured_timeout >= 0
                                     ? static_cast<uint32_t>(configured_timeout) * 1000U
                                     : this->default_screensaver_timeout_ms_;
  this->screensaver_page_index_ = screensaver_index;
  this->idle_active_ = false;
  this->active_idle_mode_ = IdleMode::NONE;
  this->screensaver_active_ = false;
  this->wake_pending_ = false;
  this->wake_guard_until_ms_ = 0;
  this->last_activity_ms_ = millis();
  const bool restore_startup_overlay = !this->startup_finished_ && this->startup_overlay_ != nullptr;
  if (restore_startup_overlay) {
    lv_obj_delete(this->startup_overlay_);
    this->startup_overlay_ = nullptr;
    this->startup_status_label_ = nullptr;
  }
  this->active_page_.reset();
  this->active_template_name_.clear();
  this->connection_indicator_ = nullptr;
  this->connection_status_label_ = nullptr;
  if (!this->show_page(0)) {
    return false;
  }
  this->apply_device_settings();
  if (restore_startup_overlay) this->show_startup_overlay_();
  ESP_LOGI(TAG, "Configuracion JSON aplicada atomicamente");
  return true;
}

bool UiEngineComponent::show_page(size_t index) {
  if (index >= this->active_config_.pages.size()) {
    return false;
  }
  const PageConfig &page_config = this->active_config_.pages[index];

  if (this->active_page_ == nullptr || this->active_template_name_ != page_config.template_name) {
    auto page = this->registry_.create(page_config.template_name);
    if (page == nullptr) {
      return false;
    }
    this->connection_indicator_ = nullptr;
    this->connection_status_label_ = nullptr;
    page->set_action_callback([this](const std::string &control_id, const std::string &action) {
      const bool waking = this->idle_active_ || this->wake_pending_ || this->wake_guard_active() ||
                          this->applied_backlight_level_ <= 0.001f;
      this->notify_activity();
      if (waking) return;
      ESP_LOGI(TAG, "action: control_id=%s action=%s", control_id.c_str(), action.c_str());
      this->action_trigger_.trigger(control_id, action);
    });
    page->set_navigation_callback([this](int delta) { this->request_page_delta(delta); });
    page->set_icon_font(this->icon_font_);
    page->set_text_font(this->clock_date_font_);
    page->create(lv_screen_active());
    this->active_page_ = std::move(page);
    this->active_template_name_ = page_config.template_name;
  }

  this->active_page_->apply(page_config);
  this->active_page_->set_navigation_enabled(this->active_config_.pages.size() > 1 && !page_config.screensaver);
  for (const auto &control : page_config.controls) {
    const auto state = this->control_states_.find(control.id);
    if (state != this->control_states_.end()) {
      this->active_page_->update_control(control.id, state->second.active, state->second.value,
                                         state->second.reliability);
    }
  }
  this->active_page_index_ = index;
  this->update_connection_indicator_();
  ESP_LOGI(TAG, "Pagina activa: %u/%u (%s)", static_cast<unsigned>(index + 1),
           static_cast<unsigned>(this->active_config_.pages.size()), page_config.title.c_str());
  return true;
}

void UiEngineComponent::notify_activity() {
  this->last_activity_ms_ = millis();
  if (this->idle_active_) {
    this->wake_pending_ = true;
    // LVGL emits CLICKED after the physical touch has already woken the panel.
    // Keep a short guard so that same touch cannot reach the control underneath.
    this->wake_guard_until_ms_ = millis() + 10000U;
  }
}

void UiEngineComponent::notify_touch_released() {
  if (this->wake_guard_active()) this->wake_guard_until_ms_ = millis() + 250U;
}

void UiEngineComponent::request_page_delta(int delta) {
  const bool waking = this->idle_active_ || this->wake_pending_ || this->wake_guard_active();
  this->notify_activity();
  if (!waking) {
    this->page_delta_pending_ = delta;
  }
}

bool UiEngineComponent::wake_guard_active() const {
  return static_cast<int32_t>(this->wake_guard_until_ms_ - millis()) > 0;
}

void UiEngineComponent::enter_idle() {
  const IdleMode mode = this->effective_idle_mode();
  if (mode == IdleMode::NONE) return;

  this->page_before_screensaver_ = this->active_page_index_;
  this->idle_active_ = true;
  this->active_idle_mode_ = mode;
  if (mode == IdleMode::CLOCK_WEATHER && this->screensaver_page_index_ >= 0) {
    this->screensaver_active_ = true;
    this->show_page(static_cast<size_t>(this->screensaver_page_index_));
  } else if (mode == IdleMode::CLOCK_WEATHER) {
    this->active_idle_mode_ = IdleMode::SCREEN_OFF;
  }
  this->apply_backlight();
}

void UiEngineComponent::refresh_idle_mode() {
  if (!this->idle_active_) return;
  IdleMode desired = this->effective_idle_mode();
  if (desired == IdleMode::CLOCK_WEATHER && this->screensaver_page_index_ < 0) desired = IdleMode::SCREEN_OFF;
  if (desired == this->active_idle_mode_) return;

  if (desired == IdleMode::CLOCK_WEATHER) {
    this->screensaver_active_ = true;
    this->show_page(static_cast<size_t>(this->screensaver_page_index_));
  } else if (this->screensaver_active_) {
    this->screensaver_active_ = false;
    this->show_page(this->page_before_screensaver_);
  }
  this->active_idle_mode_ = desired;
  ESP_LOGI(TAG, "Modo de reposo actualizado por horario: %s", this->runtime_mode().c_str());
}

void UiEngineComponent::apply_device_settings() {
  this->apply_sound_settings();
  this->apply_touch_settings();
  this->applied_backlight_level_ = -1.0f;
  this->apply_backlight();
}

void UiEngineComponent::apply_touch_settings() {
  if (this->touchscreen_ == nullptr) return;
  const auto &touch = this->active_config_.settings.touchscreen;
  this->touchscreen_->set_calibration(touch.x_min, touch.x_max, touch.y_min, touch.y_max);
  ESP_LOGI(TAG, "Calibracion tactil aplicada: x=%d..%d y=%d..%d", touch.x_min, touch.x_max, touch.y_min,
           touch.y_max);
}

void UiEngineComponent::start_touch_calibration() {
  if (this->touchscreen_ == nullptr) {
    ESP_LOGE(TAG, "No se puede calibrar: touchscreen no configurado");
    this->calibration_trigger_.trigger(false, 0, 0, 0, 0);
    return;
  }
  if (this->calibration_overlay_ != nullptr) {
    lv_obj_delete(this->calibration_overlay_);
  }

  this->notify_activity();
  this->calibration_active_ = true;
  this->calibration_target_index_ = 0;
  this->calibration_press_x_.clear();
  this->calibration_press_y_.clear();
  this->calibration_timeout_at_ms_ = millis() + 90000U;
  this->calibration_close_at_ms_ = 0;

  this->calibration_overlay_ = lv_obj_create(lv_layer_top());
  lv_obj_set_pos(this->calibration_overlay_, 0, 0);
  lv_obj_set_size(this->calibration_overlay_, 320, 240);
  lv_obj_set_style_radius(this->calibration_overlay_, 0, 0);
  lv_obj_set_style_border_width(this->calibration_overlay_, 0, 0);
  lv_obj_set_style_pad_all(this->calibration_overlay_, 0, 0);
  lv_obj_set_style_bg_color(this->calibration_overlay_, lv_color_hex(0x071015), 0);
  lv_obj_set_style_bg_opa(this->calibration_overlay_, LV_OPA_COVER, 0);
  lv_obj_add_flag(this->calibration_overlay_, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_clear_flag(this->calibration_overlay_, LV_OBJ_FLAG_SCROLLABLE);

  this->calibration_label_ = lv_label_create(this->calibration_overlay_);
  lv_obj_set_width(this->calibration_label_, 250);
  lv_obj_set_style_text_align(this->calibration_label_, LV_TEXT_ALIGN_CENTER, 0);
  lv_obj_set_style_text_color(this->calibration_label_, lv_color_hex(0xDDE8ED), 0);
  lv_obj_set_pos(this->calibration_label_, 35, 96);

  this->calibration_target_ = lv_obj_create(this->calibration_overlay_);
  lv_obj_set_size(this->calibration_target_, 28, 28);
  lv_obj_set_style_radius(this->calibration_target_, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_border_width(this->calibration_target_, 3, 0);
  lv_obj_set_style_border_color(this->calibration_target_, lv_color_hex(0x50D5AD), 0);
  lv_obj_set_style_bg_color(this->calibration_target_, lv_color_hex(0x50D5AD), 0);
  lv_obj_set_style_bg_opa(this->calibration_target_, LV_OPA_40, 0);
  lv_obj_clear_flag(this->calibration_target_, LV_OBJ_FLAG_SCROLLABLE);

  lv_obj_t *dot = lv_obj_create(this->calibration_target_);
  lv_obj_set_size(dot, 6, 6);
  lv_obj_set_style_radius(dot, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_border_width(dot, 0, 0);
  lv_obj_set_style_bg_color(dot, lv_color_hex(0xFFFFFF), 0);
  lv_obj_center(dot);

  this->update_calibration_target();
  ESP_LOGI(TAG, "Calibracion tactil iniciada");
}

void UiEngineComponent::update_calibration_target() {
  static constexpr int16_t TARGET_X[4] = {20, 299, 299, 20};
  static constexpr int16_t TARGET_Y[4] = {20, 20, 219, 219};
  if (this->calibration_target_ == nullptr || this->calibration_label_ == nullptr ||
      this->calibration_target_index_ >= 4)
    return;
  lv_obj_set_pos(this->calibration_target_, TARGET_X[this->calibration_target_index_] - 14,
                 TARGET_Y[this->calibration_target_index_] - 14);
  lv_label_set_text_fmt(this->calibration_label_, "Calibracion tactil\nToca el punto %u de 4",
                        static_cast<unsigned>(this->calibration_target_index_ + 1));
}

bool UiEngineComponent::handle_calibration_touch(const touchscreen::TouchPoint &touch) {
  if (this->calibration_overlay_ == nullptr) return false;
  if (!this->calibration_active_) return true;
  this->calibration_press_x_.clear();
  this->calibration_press_y_.clear();
  this->calibration_press_x_.push_back(touch.x_raw);
  this->calibration_press_y_.push_back(touch.y_raw);
  return true;
}

bool UiEngineComponent::handle_calibration_update(const touchscreen::TouchPoints_t &touches) {
  if (this->calibration_overlay_ == nullptr) return false;
  if (!this->calibration_active_) return true;
  for (const auto &touch : touches) {
    if (touch.state == touchscreen::STATE_PRESSED || touch.state == touchscreen::STATE_UPDATED) {
      this->calibration_press_x_.push_back(touch.x_raw);
      this->calibration_press_y_.push_back(touch.y_raw);
      break;
    }
  }
  return true;
}

bool UiEngineComponent::handle_calibration_release() {
  if (this->calibration_overlay_ == nullptr) return false;
  if (!this->calibration_active_) return true;
  if (this->calibration_press_x_.empty() || this->calibration_press_y_.empty()) return true;

  auto median = [](std::vector<int16_t> values) -> int16_t {
    std::sort(values.begin(), values.end());
    return values[values.size() / 2];
  };
  this->calibration_corner_x_[this->calibration_target_index_] = median(this->calibration_press_x_);
  this->calibration_corner_y_[this->calibration_target_index_] = median(this->calibration_press_y_);
  this->calibration_target_index_++;
  this->calibration_press_x_.clear();
  this->calibration_press_y_.clear();
  if (this->calibration_target_index_ >= 4) {
    this->finish_touch_calibration();
  } else {
    this->update_calibration_target();
  }
  return true;
}

int16_t UiEngineComponent::extrapolate_touch_edge(float first_raw, float last_raw, int first_position,
                                                   int last_position, int edge_position) const {
  if (first_position == last_position) return static_cast<int16_t>(std::round(first_raw));
  const float slope = (last_raw - first_raw) / static_cast<float>(last_position - first_position);
  const int value = static_cast<int>(std::round(first_raw + slope * (edge_position - first_position)));
  return static_cast<int16_t>(std::max(0, std::min(4095, value)));
}

void UiEngineComponent::finish_touch_calibration() {
  static constexpr int H_MARGIN = 20;
  static constexpr int V_MARGIN = 20;
  const float x_left = (this->calibration_corner_x_[0] + this->calibration_corner_x_[3]) / 2.0f;
  const float x_right = (this->calibration_corner_x_[1] + this->calibration_corner_x_[2]) / 2.0f;
  const float x_top = (this->calibration_corner_x_[0] + this->calibration_corner_x_[1]) / 2.0f;
  const float x_bottom = (this->calibration_corner_x_[3] + this->calibration_corner_x_[2]) / 2.0f;
  const bool raw_x_is_horizontal = std::fabs(x_right - x_left) >= std::fabs(x_bottom - x_top);
  const int16_t raw_x_first = raw_x_is_horizontal
                                  ? this->extrapolate_touch_edge(x_left, x_right, H_MARGIN, 319 - H_MARGIN, 0)
                                  : this->extrapolate_touch_edge(x_top, x_bottom, V_MARGIN, 239 - V_MARGIN, 0);
  const int16_t raw_x_last = raw_x_is_horizontal
                                 ? this->extrapolate_touch_edge(x_left, x_right, H_MARGIN, 319 - H_MARGIN, 319)
                                 : this->extrapolate_touch_edge(x_top, x_bottom, V_MARGIN, 239 - V_MARGIN, 239);

  const float y_left = (this->calibration_corner_y_[0] + this->calibration_corner_y_[3]) / 2.0f;
  const float y_right = (this->calibration_corner_y_[1] + this->calibration_corner_y_[2]) / 2.0f;
  const float y_top = (this->calibration_corner_y_[0] + this->calibration_corner_y_[1]) / 2.0f;
  const float y_bottom = (this->calibration_corner_y_[3] + this->calibration_corner_y_[2]) / 2.0f;
  const bool raw_y_is_horizontal = std::fabs(y_right - y_left) >= std::fabs(y_bottom - y_top);
  const int16_t raw_y_first = raw_y_is_horizontal
                                  ? this->extrapolate_touch_edge(y_left, y_right, H_MARGIN, 319 - H_MARGIN, 0)
                                  : this->extrapolate_touch_edge(y_top, y_bottom, V_MARGIN, 239 - V_MARGIN, 0);
  const int16_t raw_y_last = raw_y_is_horizontal
                                 ? this->extrapolate_touch_edge(y_left, y_right, H_MARGIN, 319 - H_MARGIN, 319)
                                 : this->extrapolate_touch_edge(y_top, y_bottom, V_MARGIN, 239 - V_MARGIN, 239);

  auto &touch = this->active_config_.settings.touchscreen;
  touch.x_min = std::min(raw_x_first, raw_x_last);
  touch.x_max = std::max(raw_x_first, raw_x_last);
  touch.y_min = std::min(raw_y_first, raw_y_last);
  touch.y_max = std::max(raw_y_first, raw_y_last);
  if (touch.x_max - touch.x_min < 1000 || touch.y_max - touch.y_min < 1000) {
    ESP_LOGE(TAG, "Calibracion tactil rechazada: rango insuficiente");
    this->close_touch_calibration(false);
    return;
  }

  this->apply_touch_settings();
  ESP_LOGI(TAG, "Calibracion tactil completada: x=%d..%d y=%d..%d", touch.x_min, touch.x_max, touch.y_min,
           touch.y_max);
  this->close_touch_calibration(true);
}

void UiEngineComponent::close_touch_calibration(bool success) {
  this->calibration_active_ = false;
  this->calibration_timeout_at_ms_ = 0;
  this->calibration_close_at_ms_ = millis() + 1200U;
  if (this->calibration_target_ != nullptr) lv_obj_add_flag(this->calibration_target_, LV_OBJ_FLAG_HIDDEN);
  if (this->calibration_label_ != nullptr)
    lv_label_set_text(this->calibration_label_, success ? "Calibracion completada" : "Calibracion cancelada");
  const auto &touch = this->active_config_.settings.touchscreen;
  this->calibration_trigger_.trigger(success, touch.x_min, touch.x_max, touch.y_min, touch.y_max);
}

float UiEngineComponent::sound_gain_for_volume(uint8_t volume) const {
  // Perceptual curve for the CYD speaker. Volume 5 remains the reference level
  // already validated on hardware, while the extremes are clearly separated.
  static constexpr float GAINS[11] = {0.0f, 0.008f, 0.020f, 0.045f, 0.090f, 0.180f,
                                      0.240f, 0.305f, 0.375f, 0.445f, 0.520f};
  return GAINS[std::min<uint8_t>(volume, 10)];
}

void UiEngineComponent::apply_sound_settings() {
  if (this->sound_player_ == nullptr) return;
  this->sound_player_->set_gain(0.0f);
}

void UiEngineComponent::preview_notification_sound(uint8_t volume) {
  if (this->sound_player_ == nullptr || volume == 0) return;
  this->sound_player_->set_gain(this->sound_gain_for_volume(volume));
  this->sound_player_->play("preview:d=32,o=6,b=180:c,e");
  this->sound_preview_active_ = true;
  this->sound_preview_restore_at_ms_ = millis() + 500U;
}

void UiEngineComponent::show_reminder(const std::string &reminder_id, const std::string &title,
                                      const std::string &message, const std::string &level) {
  this->show_reminder_(reminder_id, title, message, level, false, 0, 0);
}

void UiEngineComponent::show_alarm_reminder(const std::string &reminder_id, const std::string &title,
                                            const std::string &message, const std::string &level,
                                            uint16_t alarm_duration_seconds, uint16_t snooze_minutes) {
  this->show_reminder_(reminder_id, title, message, level, true, alarm_duration_seconds, snooze_minutes);
}

void UiEngineComponent::show_reminder_(const std::string &reminder_id, const std::string &title,
                                       const std::string &message, const std::string &level, bool alarm,
                                       uint16_t alarm_duration_seconds, uint16_t snooze_minutes) {
  this->stop_reminder_alarm_();
  this->reminder_snooze_until_ms_ = 0;
  if (this->reminder_overlay_ != nullptr) {
    lv_obj_delete(this->reminder_overlay_);
    this->reminder_overlay_ = nullptr;
  }

  // A reminder always wakes the display and takes priority over the
  // screensaver, but it does not change the page the user was viewing.
  this->last_activity_ms_ = millis();
  if (this->idle_active_) {
    const bool was_screensaver = this->screensaver_active_;
    this->idle_active_ = false;
    this->screensaver_active_ = false;
    this->active_idle_mode_ = IdleMode::NONE;
    this->wake_pending_ = false;
    if (was_screensaver) this->show_page(this->page_before_screensaver_);
  }
  this->applied_backlight_level_ = -1.0f;
  this->apply_backlight();

  uint32_t accent = 0x42A5F5;
  if (level == "reminder") accent = 0x50D5AD;
  else if (level == "warning") accent = 0xFFB300;
  else if (level == "urgent") accent = 0xEF5350;

  this->reminder_id_ = reminder_id.empty() ? "reminder" : reminder_id;
  this->reminder_title_ = title;
  this->reminder_message_ = message;
  this->reminder_level_ = level;
  this->reminder_alarm_duration_seconds_ = std::max<uint16_t>(10, std::min<uint16_t>(alarm_duration_seconds, 120));
  this->reminder_snooze_minutes_ = std::min<uint16_t>(snooze_minutes, 60);
  this->reminder_overlay_ = lv_obj_create(lv_layer_top());
  lv_obj_set_size(this->reminder_overlay_, 320, 240);
  lv_obj_set_pos(this->reminder_overlay_, 0, 0);
  lv_obj_set_style_radius(this->reminder_overlay_, 0, 0);
  lv_obj_set_style_border_width(this->reminder_overlay_, 0, 0);
  lv_obj_set_style_pad_all(this->reminder_overlay_, 0, 0);
  lv_obj_set_style_bg_color(this->reminder_overlay_, lv_color_hex(0x020609), 0);
  lv_obj_set_style_bg_opa(this->reminder_overlay_, LV_OPA_80, 0);
  lv_obj_add_flag(this->reminder_overlay_, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_clear_flag(this->reminder_overlay_, LV_OBJ_FLAG_SCROLLABLE);

  lv_obj_t *card = lv_obj_create(this->reminder_overlay_);
  lv_obj_set_size(card, 292, 210);
  lv_obj_align(card, LV_ALIGN_CENTER, 0, 0);
  lv_obj_set_style_radius(card, 14, 0);
  lv_obj_set_style_border_width(card, 2, 0);
  lv_obj_set_style_border_color(card, lv_color_hex(accent), 0);
  lv_obj_set_style_bg_color(card, lv_color_hex(0x101820), 0);
  lv_obj_set_style_bg_opa(card, LV_OPA_COVER, 0);
  lv_obj_set_style_pad_all(card, 0, 0);
  lv_obj_clear_flag(card, LV_OBJ_FLAG_SCROLLABLE);

  lv_obj_t *marker = lv_obj_create(card);
  lv_obj_set_size(marker, 5, 166);
  lv_obj_align(marker, LV_ALIGN_LEFT_MID, 10, -10);
  lv_obj_set_style_radius(marker, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_border_width(marker, 0, 0);
  lv_obj_set_style_bg_color(marker, lv_color_hex(accent), 0);

  lv_obj_t *title_label = lv_label_create(card);
  lv_obj_set_width(title_label, 244);
  lv_label_set_long_mode(title_label, LV_LABEL_LONG_DOT);
  lv_label_set_text(title_label, title.empty() ? "Recordatorio" : title.c_str());
  if (this->clock_date_font_ != nullptr) {
    // Reuse the 18 px Spanish-capable font so reminder titles can contain
    // accented characters and ñ without adding another font to flash.
    lv_obj_set_style_text_font(title_label, this->clock_date_font_->get_lv_font(), 0);
  }
  lv_obj_set_style_text_color(title_label, lv_color_hex(accent), 0);
  lv_obj_set_pos(title_label, 28, 16);

  lv_obj_t *message_label = lv_label_create(card);
  lv_obj_set_size(message_label, 244, 86);
  lv_label_set_long_mode(message_label, LV_LABEL_LONG_WRAP);
  lv_label_set_text(message_label, message.empty() ? "Tienes un aviso pendiente." : message.c_str());
  lv_obj_set_style_text_color(message_label, lv_color_hex(0xE8F0F4), 0);
  lv_obj_set_style_text_line_space(message_label, 3, 0);
  lv_obj_set_pos(message_label, 28, 53);

  lv_obj_t *accept = lv_button_create(card);
  lv_obj_set_size(accept, this->reminder_snooze_minutes_ > 0 ? 112 : 164, 46);
  lv_obj_align(accept, LV_ALIGN_BOTTOM_MID, this->reminder_snooze_minutes_ > 0 ? 62 : 0, -12);
  lv_obj_set_style_radius(accept, 10, 0);
  lv_obj_set_style_bg_color(accept, lv_color_hex(accent), 0);
  lv_obj_set_style_bg_color(accept, lv_color_hex(0xFFFFFF), LV_STATE_PRESSED);
  lv_obj_add_event_cb(
      accept,
      [](lv_event_t *event) {
        auto *engine = static_cast<UiEngineComponent *>(lv_event_get_user_data(event));
        if (engine != nullptr) engine->dismiss_reminder();
      },
      LV_EVENT_CLICKED, this);

  lv_obj_t *accept_label = lv_label_create(accept);
  lv_label_set_text(accept_label, "ACEPTAR");
  lv_obj_set_style_text_color(accept_label, lv_color_hex(0x071015), 0);
  lv_obj_center(accept_label);

  if (this->reminder_snooze_minutes_ > 0) {
    lv_obj_t *snooze = lv_button_create(card);
    lv_obj_set_size(snooze, 112, 46);
    lv_obj_align(snooze, LV_ALIGN_BOTTOM_MID, -62, -12);
    lv_obj_set_style_radius(snooze, 10, 0);
    lv_obj_set_style_bg_color(snooze, lv_color_hex(0x32434D), 0);
    lv_obj_set_style_bg_color(snooze, lv_color_hex(0xFFFFFF), LV_STATE_PRESSED);
    lv_obj_add_event_cb(
        snooze,
        [](lv_event_t *event) {
          auto *engine = static_cast<UiEngineComponent *>(lv_event_get_user_data(event));
          if (engine != nullptr) engine->snooze_reminder_();
        },
        LV_EVENT_CLICKED, this);
    lv_obj_t *snooze_label = lv_label_create(snooze);
    lv_label_set_text(snooze_label, "APLAZAR");
    lv_obj_set_style_text_color(snooze_label, lv_color_hex(0xE8F0F4), 0);
    lv_obj_center(snooze_label);
  }

  lv_obj_move_foreground(this->reminder_overlay_);
  if (alarm) {
    const uint32_t now = millis();
    this->reminder_alarm_active_ = true;
    this->reminder_alarm_until_ms_ = now + static_cast<uint32_t>(this->reminder_alarm_duration_seconds_) * 1000U;
    this->reminder_alarm_next_ms_ = now;
  }
  ESP_LOGI(TAG, "Recordatorio mostrado: id=%s level=%s", this->reminder_id_.c_str(), level.c_str());
}

void UiEngineComponent::stop_reminder_alarm_() {
  this->reminder_alarm_active_ = false;
  this->reminder_alarm_until_ms_ = 0;
  this->reminder_alarm_next_ms_ = 0;
  if (this->sound_player_ != nullptr && this->sound_player_->is_playing()) this->sound_player_->stop();
  this->apply_sound_settings();
}

void UiEngineComponent::snooze_reminder_() {
  if (this->reminder_overlay_ == nullptr || this->reminder_snooze_minutes_ == 0) return;
  this->stop_reminder_alarm_();
  lv_obj_delete_async(this->reminder_overlay_);
  this->reminder_overlay_ = nullptr;
  this->reminder_snooze_until_ms_ = millis() + static_cast<uint32_t>(this->reminder_snooze_minutes_) * 60000U;
  this->last_activity_ms_ = millis();
  this->action_trigger_.trigger(this->reminder_id_, "snooze");
  ESP_LOGI(TAG, "Recordatorio aplazado %u minutos: id=%s", this->reminder_snooze_minutes_,
           this->reminder_id_.c_str());
}

bool UiEngineComponent::dismiss_reminder(const std::string &reminder_id) {
  if (this->reminder_overlay_ == nullptr && this->reminder_snooze_until_ms_ == 0) return false;
  if (!reminder_id.empty() && reminder_id != this->reminder_id_) return false;

  const std::string acknowledged_id = this->reminder_id_;
  this->stop_reminder_alarm_();
  this->reminder_snooze_until_ms_ = 0;
  if (this->reminder_overlay_ != nullptr) {
    lv_obj_delete_async(this->reminder_overlay_);
    this->reminder_overlay_ = nullptr;
  }
  this->reminder_id_.clear();
  this->reminder_title_.clear();
  this->reminder_message_.clear();
  this->reminder_level_.clear();
  this->last_activity_ms_ = millis();
  this->action_trigger_.trigger(acknowledged_id, "acknowledge");
  ESP_LOGI(TAG, "Recordatorio aceptado: id=%s", acknowledged_id.c_str());
  return true;
}

bool UiEngineComponent::play_notification_sound(const std::string &sound) {
  if (this->sound_player_ == nullptr || !this->prepare_notification_sound()) return false;
  if (sound == "attention") {
    this->sound_player_->play("attention:d=32,o=6,b=220:g,p,g");
  } else if (sound == "notification") {
    this->sound_player_->play("notification:d=32,o=6,b=180:c,e");
  } else if (sound == "success") {
    this->sound_player_->play("success:d=32,o=6,b=180:c,e,g");
  } else if (sound == "warning") {
    this->sound_player_->play("warning:d=16,o=5,b=180:a,p,a");
  } else if (sound == "error") {
    this->sound_player_->play("error:d=16,o=4,b=160:g");
  } else {
    ESP_LOGW(TAG, "Sonido desconocido: %s", sound.c_str());
    return false;
  }
  return true;
}

float UiEngineComponent::ambient_light_percent() const {
  if (std::isnan(this->ambient_light_voltage_)) return NAN;
  const auto &display = this->active_config_.settings.display;
  const float span = display.ldr_bright_voltage - display.ldr_dark_voltage;
  if (std::fabs(span) < 0.001f) return NAN;
  float ratio = (this->ambient_light_voltage_ - display.ldr_dark_voltage) / span;
  ratio = std::max(0.0f, std::min(1.0f, ratio));
  return ratio * 100.0f;
}

void UiEngineComponent::set_wifi_setup_visible(bool visible, const std::string &ssid,
                                               const std::string &password) {
  if (!visible) {
    if (this->wifi_setup_overlay_ != nullptr) lv_obj_add_flag(this->wifi_setup_overlay_, LV_OBJ_FLAG_HIDDEN);
    return;
  }

  this->notify_activity();
  if (this->wifi_setup_overlay_ == nullptr) {
    this->wifi_setup_overlay_ = lv_obj_create(lv_screen_active());
    lv_obj_set_size(this->wifi_setup_overlay_, LV_PCT(100), LV_PCT(100));
    lv_obj_align(this->wifi_setup_overlay_, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_bg_color(this->wifi_setup_overlay_, lv_color_hex(0x101820), 0);
    lv_obj_set_style_bg_opa(this->wifi_setup_overlay_, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(this->wifi_setup_overlay_, 0, 0);
    lv_obj_set_style_radius(this->wifi_setup_overlay_, 0, 0);
    lv_obj_remove_flag(this->wifi_setup_overlay_, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *title = lv_label_create(this->wifi_setup_overlay_);
    lv_label_set_text(title, "CONFIGURAR WI-FI");
    lv_obj_set_style_text_color(title, lv_color_hex(0x55C8FF), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 18);

    lv_obj_t *network = lv_label_create(this->wifi_setup_overlay_);
    lv_label_set_text_fmt(network, "Red: %s", ssid.c_str());
    lv_obj_set_style_text_color(network, lv_color_hex(0xFFFFFF), 0);
    lv_obj_align(network, LV_ALIGN_TOP_MID, 0, 62);

    lv_obj_t *key = lv_label_create(this->wifi_setup_overlay_);
    lv_label_set_text_fmt(key, "Clave: %s", password.c_str());
    lv_obj_set_style_text_color(key, lv_color_hex(0xFFD166), 0);
    lv_obj_align(key, LV_ALIGN_TOP_MID, 0, 92);

    lv_obj_t *help = lv_label_create(this->wifi_setup_overlay_);
    lv_label_set_text(help, "Abrir en el telefono:");
    lv_obj_set_style_text_color(help, lv_color_hex(0xB8C4CC), 0);
    lv_obj_align(help, LV_ALIGN_TOP_MID, 0, 137);

    lv_obj_t *address = lv_label_create(this->wifi_setup_overlay_);
    lv_label_set_text(address, "192.168.4.1");
    lv_obj_set_style_text_color(address, lv_color_hex(0xFFFFFF), 0);
    lv_obj_align(address, LV_ALIGN_TOP_MID, 0, 166);
  }

  lv_obj_remove_flag(this->wifi_setup_overlay_, LV_OBJ_FLAG_HIDDEN);
  lv_obj_move_foreground(this->wifi_setup_overlay_);
}

void UiEngineComponent::set_startup_status(const std::string &status) {
  if (this->startup_finished_) return;
  this->startup_status_ = status;
  if (this->startup_status_label_ != nullptr) {
    lv_label_set_text(this->startup_status_label_, status.c_str());
  }
  this->startup_overlay_hide_at_ms_ = millis() + 3500U;
}

void UiEngineComponent::set_connection_state(uint8_t state) {
  this->connection_state_ = state;
  this->update_connection_indicator_();
}

void UiEngineComponent::update_connection_indicator_() {
  if (this->active_page_ == nullptr) return;
  if (this->connection_indicator_ == nullptr) {
    this->connection_indicator_ = lv_obj_create(lv_screen_active());
    lv_obj_set_size(this->connection_indicator_, 4, 4);
    lv_obj_align(this->connection_indicator_, LV_ALIGN_BOTTOM_RIGHT, -4, -4);
    lv_obj_set_style_radius(this->connection_indicator_, LV_RADIUS_CIRCLE, LV_PART_MAIN);
    lv_obj_set_style_border_width(this->connection_indicator_, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(this->connection_indicator_, 0, LV_PART_MAIN);
    lv_obj_remove_flag(this->connection_indicator_, LV_OBJ_FLAG_CLICKABLE);
  }
  if (this->connection_status_label_ == nullptr) {
    this->connection_status_label_ = lv_label_create(lv_screen_active());
    lv_obj_remove_flag(this->connection_status_label_, LV_OBJ_FLAG_CLICKABLE);
  }
  uint32_t color = 0xEF5350;  // sin Wi-Fi
  const char *status = "Sin Wi-Fi";
  if (this->connection_state_ == 1) color = 0xFFD600;       // Wi-Fi, sin HA
  if (this->connection_state_ == 1) status = "Sin Home Assistant";
  else if (this->connection_state_ == 2) {                  // Wi-Fi y HA
    color = 0x66BB6A;
    status = nullptr;
  } else if (this->connection_state_ == 3) {                // portal de configuración
    color = 0x42A5F5;
    status = "Configurar Wi-Fi";
  }
  lv_obj_set_style_bg_color(this->connection_indicator_, lv_color_hex(color), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(this->connection_indicator_, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_move_foreground(this->connection_indicator_);
  if (status == nullptr) {
    lv_obj_add_flag(this->connection_status_label_, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_label_set_text(this->connection_status_label_, status);
    lv_obj_set_style_text_color(this->connection_status_label_, lv_color_hex(color), LV_PART_MAIN);
    lv_obj_align(this->connection_status_label_, LV_ALIGN_BOTTOM_RIGHT, -12, -3);
    lv_obj_remove_flag(this->connection_status_label_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(this->connection_status_label_);
  }
}

void UiEngineComponent::show_startup_overlay_() {
  lv_obj_t *screen = lv_screen_active();
  this->startup_overlay_ = lv_obj_create(screen);
  lv_obj_set_size(this->startup_overlay_, 320, 240);
  lv_obj_set_pos(this->startup_overlay_, 0, 0);
  lv_obj_set_style_bg_color(this->startup_overlay_, lv_color_hex(0x071521), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(this->startup_overlay_, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_border_width(this->startup_overlay_, 0, LV_PART_MAIN);
  lv_obj_set_style_radius(this->startup_overlay_, 0, LV_PART_MAIN);
  lv_obj_set_style_pad_all(this->startup_overlay_, 0, LV_PART_MAIN);

  lv_obj_t *title = lv_label_create(this->startup_overlay_);
  lv_label_set_text(title, "CYD UI");
  lv_obj_set_style_text_font(title, &lv_font_montserrat_32, LV_PART_MAIN);
  lv_obj_set_style_text_color(title, lv_color_hex(0x50D5AD), LV_PART_MAIN);
  lv_obj_align(title, LV_ALIGN_CENTER, 0, -34);

  this->startup_status_label_ = lv_label_create(this->startup_overlay_);
  lv_label_set_text(this->startup_status_label_, this->startup_status_.c_str());
  lv_obj_set_style_text_color(this->startup_status_label_, lv_color_hex(0xC7D6DE), LV_PART_MAIN);
  lv_obj_align(this->startup_status_label_, LV_ALIGN_CENTER, 0, 12);

  lv_obj_t *subtitle = lv_label_create(this->startup_overlay_);
  lv_label_set_text(subtitle, "Preparando tu panel");
  lv_obj_set_style_text_color(subtitle, lv_color_hex(0x6F8796), LV_PART_MAIN);
  lv_obj_align(subtitle, LV_ALIGN_CENTER, 0, 42);
  lv_obj_move_foreground(this->startup_overlay_);
  this->startup_overlay_hide_at_ms_ = millis() + 3500U;
}

float UiEngineComponent::base_brightness_percent() const {
  const auto &display = this->active_config_.settings.display;
  float brightness = static_cast<float>(display.brightness);
  if (display.auto_brightness && !std::isnan(this->ambient_light_voltage_)) {
    const float span = display.ldr_bright_voltage - display.ldr_dark_voltage;
    float ratio = (this->ambient_light_voltage_ - display.ldr_dark_voltage) / span;
    ratio = std::max(0.0f, std::min(1.0f, ratio));
    brightness = display.minimum_brightness + ratio * (display.maximum_brightness - display.minimum_brightness);
  }
  if (this->is_night()) brightness = this->active_config_.settings.night.brightness;
  return brightness;
}

void UiEngineComponent::apply_backlight() {
  if (this->backlight_output_ == nullptr) return;
  float brightness = this->base_brightness_percent();
  if (this->idle_active_) {
    if (this->active_idle_mode_ == IdleMode::SCREEN_OFF) {
      brightness = 0.0f;
    } else if (this->active_idle_mode_ == IdleMode::DIM) {
      brightness = std::min(brightness, static_cast<float>(this->active_config_.settings.inactivity.dim_brightness));
    }
  }
  const float level = std::max(0.0f, std::min(1.0f, brightness / 100.0f));
  if (std::fabs(level - this->applied_backlight_level_) < 0.005f) return;
  this->backlight_output_->set_level(level);
  this->applied_backlight_level_ = level;
}

float UiEngineComponent::applied_brightness_percent() const {
  return std::max(0.0f, this->applied_backlight_level_) * 100.0f;
}

std::string UiEngineComponent::runtime_mode() const {
  if (!this->idle_active_) return this->is_night() ? "night" : "normal";
  switch (this->active_idle_mode_) {
    case IdleMode::CLOCK_WEATHER:
      return "clock_weather";
    case IdleMode::SCREEN_OFF:
      return "screen_off";
    case IdleMode::DIM:
      return "dim";
    default:
      return "idle";
  }
}

bool UiEngineComponent::is_night() const {
  const auto &night = this->active_config_.settings.night;
  if (!night.enabled || this->clock_ == nullptr) return false;
  const auto now = this->clock_->now();
  if (!now.is_valid()) return false;
  const uint16_t minutes = static_cast<uint16_t>(now.hour * 60 + now.minute);
  if (night.start_minutes == night.end_minutes) return true;
  if (night.start_minutes < night.end_minutes)
    return minutes >= night.start_minutes && minutes < night.end_minutes;
  return minutes >= night.start_minutes || minutes < night.end_minutes;
}

IdleMode UiEngineComponent::effective_idle_mode() const {
  if (this->is_night()) return this->active_config_.settings.night.mode;
  return this->active_config_.settings.inactivity.mode;
}

bool UiEngineComponent::prepare_sound(bool event_enabled, uint8_t volume) {
  const auto &sound = this->active_config_.settings.sound;
  const bool allowed = sound.enabled && event_enabled && volume > 0 && !(sound.mute_at_night && this->is_night());
  if (allowed && this->sound_player_ != nullptr) {
    this->sound_preview_active_ = false;
    this->sound_player_->set_gain(this->sound_gain_for_volume(volume));
  }
  return allowed;
}

bool UiEngineComponent::prepare_touch_sound() {
  const auto &sound = this->active_config_.settings.sound;
  return this->prepare_sound(sound.touch, sound.touch_volume);
}

bool UiEngineComponent::prepare_navigation_sound() {
  const auto &sound = this->active_config_.settings.sound;
  return this->prepare_sound(sound.navigation, sound.navigation_volume);
}

bool UiEngineComponent::prepare_notification_sound() {
  const auto &sound = this->active_config_.settings.sound;
  // Las notificaciones de Home Assistant son independientes de los sonidos de
  // interacción local. El horario nocturno sigue siendo la política común.
  const bool allowed = sound.notifications && sound.notification_volume > 0 &&
                       !(sound.mute_at_night && this->is_night());
  if (allowed && this->sound_player_ != nullptr) {
    this->sound_preview_active_ = false;
    this->sound_player_->set_gain(this->sound_gain_for_volume(sound.notification_volume));
  }
  return allowed;
}

bool UiEngineComponent::update_control(const std::string &id, bool active, const std::string &value,
                                       const std::string &reliability) {
  if (this->active_page_ == nullptr) {
    ESP_LOGW(TAG, "Actualizacion ignorada: no hay pagina activa");
    return false;
  }

  ControlState state = ControlState::VALID;
  if (reliability == "unknown") {
    state = ControlState::UNKNOWN;
  } else if (reliability == "stale" || reliability == "disconnected" || reliability == "unavailable") {
    state = ControlState::STALE_OR_DISCONNECTED;
  } else if (reliability != "valid") {
    ESP_LOGW(TAG, "Confiabilidad desconocida para %s: %s", id.c_str(), reliability.c_str());
    return false;
  }

  this->control_states_[id] = RuntimeControlState{active, value, state};
  this->active_page_->update_control(id, active, value, state);
  ESP_LOGI(TAG, "control_changed: id=%s active=%s value=%s reliability=%s", id.c_str(), YESNO(active),
           value.c_str(), reliability.c_str());
  return true;
}

void UiEngineComponent::set_backend_connected(bool connected) {
  this->backend_connected_ = connected;
  if (this->active_page_ == nullptr) {
    return;
  }
  this->active_page_->set_all_states(connected ? ControlState::UNKNOWN : ControlState::STALE_OR_DISCONNECTED);
  for (auto &entry : this->control_states_) {
    entry.second.reliability = connected ? ControlState::UNKNOWN : ControlState::STALE_OR_DISCONNECTED;
  }
  ESP_LOGI(TAG, "Backend %s", connected ? "conectado; esperando sincronizacion" : "desconectado");
}

void UiEngineComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "UI Engine:");
  ESP_LOGCONFIG(TAG, "  Paginas: %u", static_cast<unsigned>(this->active_config_.pages.size()));
}

float UiEngineComponent::get_setup_priority() const { return setup_priority::LATE; }

}  // namespace ui_engine
}  // namespace esphome
