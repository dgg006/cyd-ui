#include "config_provider.h"

#include "esphome/core/application.h"
#include "esphome/core/helpers.h"

namespace esphome {
namespace ui_engine {

bool HttpConfigProvider::fetch(std::string *raw_json, std::string *error) {
  this->last_fetch_succeeded_ = false;
  auto response = this->client_->get(this->url_);
  if (response == nullptr) {
    *error = "no se pudo iniciar GET " + this->url_;
    return false;
  }

  if (!http_request::is_success(response->status_code)) {
    *error = "HTTP respondio " + std::to_string(response->status_code);
    response->end();
    return false;
  }
  if (response->content_length > UI_CONFIG_MAX_SIZE) {
    *error = "configuracion HTTP supera " + std::to_string(UI_CONFIG_MAX_SIZE) + " bytes";
    response->end();
    return false;
  }

  raw_json->clear();
  if (response->content_length > 0) {
    raw_json->reserve(response->content_length);
  }

  uint8_t buffer[512];
  uint32_t last_data_time = millis();
  while (!response->is_read_complete()) {
    const int read_result = response->read(buffer, sizeof(buffer));
    App.feed_wdt();
    yield();

    auto result = http_request::http_read_loop_result(read_result, last_data_time, this->client_->get_timeout(),
                                                      response->is_read_complete());
    if (result == http_request::HttpReadLoopResult::RETRY) {
      continue;
    }
    if (result == http_request::HttpReadLoopResult::COMPLETE) {
      break;
    }
    if (result == http_request::HttpReadLoopResult::ERROR) {
      *error = "error leyendo respuesta HTTP";
      response->end();
      return false;
    }
    if (result == http_request::HttpReadLoopResult::TIMEOUT) {
      *error = "timeout leyendo respuesta HTTP";
      response->end();
      return false;
    }

    raw_json->append(reinterpret_cast<const char *>(buffer), static_cast<size_t>(read_result));
    if (raw_json->size() > UI_CONFIG_MAX_SIZE) {
      *error = "configuracion HTTP supera " + std::to_string(UI_CONFIG_MAX_SIZE) + " bytes";
      response->end();
      return false;
    }
  }
  response->end();

  if (raw_json->empty()) {
    *error = "respuesta HTTP vacia";
    return false;
  }
  this->last_fetch_succeeded_ = true;
  return true;
}

bool FallbackConfigProvider::fetch(std::string *raw_json, std::string *error) {
  this->used_primary_ = false;
  std::string primary_error;
  if (this->primary_->fetch(raw_json, &primary_error)) {
    this->used_primary_ = true;
    return true;
  }
  if (this->fallback_->fetch(raw_json, error)) {
    return true;
  }
  *error = "primario: " + primary_error + "; respaldo: " + *error;
  return false;
}

bool FallbackConfigProvider::fetched_from_remote() const {
  return this->used_primary_ ? this->primary_->fetched_from_remote() : this->fallback_->fetched_from_remote();
}

}  // namespace ui_engine
}  // namespace esphome
