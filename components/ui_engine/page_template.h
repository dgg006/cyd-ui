#pragma once

#include <functional>
#include <string>

#include "lvgl.h"
#include "model.h"

namespace esphome {
namespace ui_engine {

using ActionCallback = std::function<void(const std::string &control_id, const std::string &action)>;
using NavigationCallback = std::function<void(int delta)>;

class PageTemplate {
 public:
  virtual ~PageTemplate() = default;
  virtual void loop() {}
  virtual void create(lv_obj_t *parent) = 0;
  virtual void apply(const PageConfig &config) = 0;
  virtual bool update_control(const std::string &id, bool active, const std::string &value, ControlState state) = 0;
  virtual void set_all_states(ControlState state) = 0;
  virtual bool validate(const PageConfig &config, std::string *error) const = 0;
  virtual void set_action_callback(ActionCallback callback) = 0;
  virtual void set_navigation_callback(NavigationCallback callback) = 0;
  virtual void set_navigation_enabled(bool enabled) = 0;
};

}  // namespace ui_engine
}  // namespace esphome
