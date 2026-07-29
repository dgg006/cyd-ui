#pragma once

#include <string>

namespace esphome {
namespace ui_engine {

// Devuelve el glifo UTF-8 correspondiente a un nombre MDI admitido.
// El puntero retornado apunta a almacenamiento estático y no debe liberarse.
const char *resolve_mdi_icon(const std::string &name);

}  // namespace ui_engine
}  // namespace esphome
