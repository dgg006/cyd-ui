#pragma once

#include <memory>
#include <string>

#include "esphome/components/http_request/http_request.h"
#include "config_limits.h"
#include "flash_storage.h"

namespace esphome {
namespace ui_engine {

class ConfigProvider {
 public:
  virtual ~ConfigProvider() = default;
  virtual bool fetch(std::string *raw_json, std::string *error) = 0;
  virtual bool fetched_from_remote() const { return false; }
};

class EmbeddedConfigProvider final : public ConfigProvider {
 public:
  explicit EmbeddedConfigProvider(std::string config) : config_(std::move(config)) {}

  bool fetch(std::string *raw_json, std::string *error) override {
    if (this->config_.empty()) {
      *error = "configuracion embebida vacia";
      return false;
    }
    *raw_json = this->config_;
    return true;
  }

 private:
  std::string config_;
};

class HttpConfigProvider final : public ConfigProvider {
 public:
  HttpConfigProvider(http_request::HttpRequestComponent *client, std::string url)
      : client_(client), url_(std::move(url)) {}

  bool fetch(std::string *raw_json, std::string *error) override;
  bool fetched_from_remote() const override { return this->last_fetch_succeeded_; }

 private:
  http_request::HttpRequestComponent *client_;
  std::string url_;
  bool last_fetch_succeeded_{false};
};

class FlashConfigProvider final : public ConfigProvider {
 public:
  explicit FlashConfigProvider(FlashStorage *storage) : storage_(storage) {}
  bool fetch(std::string *raw_json, std::string *error) override { return this->storage_->load(raw_json, error); }

 private:
  FlashStorage *storage_;
};

class FallbackConfigProvider final : public ConfigProvider {
 public:
  FallbackConfigProvider(std::unique_ptr<ConfigProvider> primary, std::unique_ptr<ConfigProvider> fallback)
      : primary_(std::move(primary)), fallback_(std::move(fallback)) {}

  bool fetch(std::string *raw_json, std::string *error) override;
  bool fetched_from_remote() const override;

 private:
  std::unique_ptr<ConfigProvider> primary_;
  std::unique_ptr<ConfigProvider> fallback_;
  bool used_primary_{false};
};

}  // namespace ui_engine
}  // namespace esphome
