#pragma once

#include <functional>
#include <map>
#include <memory>
#include <string>

#include "page_template.h"

namespace esphome {
namespace ui_engine {

class TemplateRegistry {
 public:
  using Factory = std::function<std::unique_ptr<PageTemplate>()>;

  void register_template(const std::string &name, Factory factory) {
    this->factories_[name] = std::move(factory);
  }

  std::unique_ptr<PageTemplate> create(const std::string &name) const {
    auto iterator = this->factories_.find(name);
    if (iterator == this->factories_.end()) {
      return nullptr;
    }
    return iterator->second();
  }

 private:
  std::map<std::string, Factory> factories_;
};

}  // namespace ui_engine
}  // namespace esphome

