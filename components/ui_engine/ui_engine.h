#pragma once

#include <map>

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "button_grid.h"
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
  void request_reload() { this->reload_pending_ = true; }
  bool update_control(const std::string &id, bool active, const std::string &reliability);
  void set_backend_connected(bool connected);

 private:
  bool try_apply_config(const std::string &raw_json);
  bool show_page(size_t index);
  void request_page_delta(int delta) { this->page_delta_pending_ = delta; }

  struct RuntimeControlState {
    bool active{false};
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
  bool reload_pending_{false};
  int page_delta_pending_{0};
  http_request::HttpRequestComponent *http_client_{nullptr};
  std::string config_url_;
};

template<typename... Ts> class ReloadAction final : public Action<Ts...>, public Parented<UiEngineComponent> {
 public:
  void play(const Ts &...x) override { this->parent_->request_reload(); }
};

}  // namespace ui_engine
}  // namespace esphome
