#include "ui_engine.h"

#include "esphome/core/log.h"

namespace esphome {
namespace ui_engine {

static const char *const TAG = "ui_engine";

void UiEngineComponent::setup() {
  this->registry_.register_template("button_grid", []() { return std::make_unique<ButtonGrid>(); });
  this->registry_.register_template("climate", []() { return std::make_unique<ClimatePage>(); });
  this->registry_.register_template("clock_weather", [this]() { return std::make_unique<ClockWeatherPage>(this->clock_); });
  this->registry_.register_template("sensor_grid", []() { return std::make_unique<SensorGrid>(); });
  this->last_activity_ms_ = millis();
  this->flash_storage_.begin();
  auto embedded_provider = std::make_unique<EmbeddedConfigProvider>(std::move(this->initial_config_));
  auto flash_provider = std::make_unique<FlashConfigProvider>(&this->flash_storage_);
  auto local_fallback =
      std::make_unique<FallbackConfigProvider>(std::move(flash_provider), std::move(embedded_provider));
  if (this->http_client_ != nullptr && !this->config_url_.empty()) {
    auto http_provider = std::make_unique<HttpConfigProvider>(this->http_client_, this->config_url_);
    this->config_provider_ =
        std::make_unique<FallbackConfigProvider>(std::move(http_provider), std::move(local_fallback));
  } else {
    this->config_provider_ = std::move(local_fallback);
  }

  std::string raw_json;
  std::string error;
  if (!this->config_provider_->fetch(&raw_json, &error)) {
    ESP_LOGE(TAG, "No se pudo obtener configuracion: %s", error.c_str());
    this->mark_failed();
    return;
  }
  if (!this->try_apply_config(raw_json)) {
    this->mark_failed();
    return;
  }
  if (this->config_provider_->fetched_from_remote()) {
    if (this->flash_storage_.save(raw_json, &error)) {
      ESP_LOGI(TAG, "Configuracion HTTP guardada en cache flash");
    } else {
      ESP_LOGW(TAG, "No se pudo guardar cache flash: %s", error.c_str());
    }
  }
  ESP_LOGI(TAG, "UI Engine inicializado con ButtonGrid de 6 controles");
}

void UiEngineComponent::loop() {
  if (this->active_page_ != nullptr) {
    this->active_page_->loop();
  }

  if (this->wake_pending_) {
    this->wake_pending_ = false;
    this->screensaver_active_ = false;
    this->show_page(this->page_before_screensaver_);
  }

  if (!this->screensaver_active_ && this->screensaver_page_index_ >= 0 && this->screensaver_timeout_ms_ > 0 &&
      this->active_page_index_ != static_cast<size_t>(this->screensaver_page_index_) &&
      millis() - this->last_activity_ms_ >= this->screensaver_timeout_ms_) {
    this->page_before_screensaver_ = this->active_page_index_;
    this->screensaver_active_ = true;
    this->show_page(static_cast<size_t>(this->screensaver_page_index_));
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
  this->screensaver_page_index_ = screensaver_index;
  this->screensaver_active_ = false;
  this->wake_pending_ = false;
  this->last_activity_ms_ = millis();
  if (!this->show_page(0)) {
    return false;
  }
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
      this->notify_activity();
      ESP_LOGI(TAG, "action: control_id=%s action=%s", control_id.c_str(), action.c_str());
      this->action_trigger_.trigger(control_id, action);
    });
    page->set_navigation_callback([this](int delta) { this->request_page_delta(delta); });
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
  if (this->screensaver_active_) {
    this->wake_pending_ = true;
  }
}

void UiEngineComponent::request_page_delta(int delta) {
  this->notify_activity();
  if (!this->screensaver_active_) {
    this->page_delta_pending_ = delta;
  }
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
