#pragma once

#include <map>

#include "esphome/components/font/font.h"
#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "button_grid.h"
#include "climate_page.h"
#include "clock_weather_page.h"
#include "cover_page.h"
#include "sensor_grid.h"
#include "config_parser.h"
#include "config_provider.h"
#include "flash_storage.h"
#include "page_template.h"
#include "template_registry.h"

namespace esphome {
namespace ui_engine {

class UiEngineComponent : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override;
  void set_initial_config(const std::string &config) { this->initial_config_ = config; }
  void set_http_config(http_request::HttpRequestComponent *client, const std::string &url) {
    this->http_client_ = client;
    this->config_url_ = url;
  }
  Trigger<std::string, std::string> *get_action_trigger() { return &this->action_trigger_; }
  Trigger<int> *get_navigation_trigger() { return &this->navigation_trigger_; }
  void request_reload() { this->reload_pending_ = true; }
  void notify_activity();
  void set_clock(time::RealTimeClock *clock) { this->clock_ = clock; }
  void set_icon_font(font::Font *font) { this->icon_font_ = font; }
  void set_screensaver_timeout(uint32_t timeout_ms) { this->screensaver_timeout_ms_ = timeout_ms; }
  bool update_control(const std::string &id, bool active, const std::string &value, const std::string &reliability);
  void set_backend_connected(bool connected);

 private:
  bool try_apply_config(const std::string &raw_json);
  bool show_page(size_t index);
  void request_page_delta(int delta);

  struct RuntimeControlState {
    bool active{false};
    std::string value;
    ControlState reliability{ControlState::UNKNOWN};
  };

  ConfigParser parser_;
  std::unique_ptr<ConfigProvider> config_provider_;
  FlashStorage flash_storage_;
  std::string initial_config_;
  TemplateRegistry registry_;
  std::unique_ptr<PageTemplate> active_page_;
  UiConfig active_config_;
  std::string active_template_name_;
  size_t active_page_index_{0};
  std::map<std::string, RuntimeControlState> control_states_;
  Trigger<std::string, std::string> action_trigger_;
  Trigger<int> navigation_trigger_;
  bool reload_pending_{false};
  int page_delta_pending_{0};
  http_request::HttpRequestComponent *http_client_{nullptr};
  std::string config_url_;
  time::RealTimeClock *clock_{nullptr};
  font::Font *icon_font_{nullptr};
  uint32_t screensaver_timeout_ms_{0};
  uint32_t last_activity_ms_{0};
  int screensaver_page_index_{-1};
  size_t page_before_screensaver_{0};
  bool screensaver_active_{false};
  bool wake_pending_{false};
};

template<typename... Ts> class ReloadAction final : public Action<Ts...>, public Parented<UiEngineComponent> {
 public:
  void play(const Ts &...x) override { this->parent_->request_reload(); }
};

}  // namespace ui_engine
}  // namespace esphome
