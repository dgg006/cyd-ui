#include "ui_engine.h"

#include <algorithm>
#include <cmath>

#include "esphome/core/log.h"

namespace esphome {
namespace ui_engine {

static const char *const TAG = "ui_engine";

void UiEngineComponent::setup() {
  this->registry_.register_template("button_grid", []() { return std::make_unique<ButtonGrid>(); });
  this->registry_.register_template("climate", []() { return std::make_unique<ClimatePage>(); });
  this->registry_.register_template("clock_weather", [this]() { return std::make_unique<ClockWeatherPage>(this->clock_); });
  this->registry_.register_template("sensor_grid", []() { return std::make_unique<SensorGrid>(); });
  this->registry_.register_template("cover", []() { return std::make_unique<CoverPage>(); });
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
  ESP_LOGI(TAG, "UI Engine inicializado");
}

void UiEngineComponent::loop() {
  if (this->active_page_ != nullptr) {
    this->active_page_->loop();
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
  if (!this->show_page(0)) {
    return false;
  }
  this->apply_device_settings();
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
  if (this->sound_player_ != nullptr) {
    const auto &sound = this->active_config_.settings.sound;
    const float gain = sound.enabled ? static_cast<float>(sound.volume) * 0.036f : 0.0f;
    this->sound_player_->set_gain(gain);
  }
  this->applied_backlight_level_ = -1.0f;
  this->apply_backlight();
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

bool UiEngineComponent::touch_sound_enabled() const {
  const auto &sound = this->active_config_.settings.sound;
  return sound.enabled && sound.touch && sound.volume > 0;
}

bool UiEngineComponent::navigation_sound_enabled() const {
  const auto &sound = this->active_config_.settings.sound;
  return sound.enabled && sound.navigation && sound.volume > 0;
}

bool UiEngineComponent::notification_sound_enabled() const {
  const auto &sound = this->active_config_.settings.sound;
  return sound.enabled && sound.notifications && sound.volume > 0;
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
