#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

#include "config_limits.h"
#include "esphome/core/preferences.h"

namespace esphome {
namespace ui_engine {

class FlashStorage {
 public:
  void begin();
  bool load(std::string *raw_json, std::string *error);
  bool save(const std::string &raw_json, std::string *error);

 private:
  static constexpr size_t CACHE_BANK_COUNT = 2;
  static constexpr size_t CACHE_CHUNK_SIZE = 1024;
  static constexpr size_t CACHE_CHUNK_COUNT = (UI_CONFIG_MAX_SIZE + CACHE_CHUNK_SIZE - 1) / CACHE_CHUNK_SIZE;

  struct CacheMetadata {
    uint32_t magic;
    uint16_t schema_version;
    uint8_t active_bank;
    uint8_t reserved;
    uint16_t length;
    uint16_t reserved_2;
    uint32_t checksum;
    uint32_t generation;
  };

  struct CacheChunk {
    std::array<uint8_t, CACHE_CHUNK_SIZE> data;
  };

  ESPPreferenceObject metadata_preference_;
  std::array<std::array<ESPPreferenceObject, CACHE_CHUNK_COUNT>, CACHE_BANK_COUNT> chunk_preferences_{};
  uint32_t saved_checksum_{0};
  size_t saved_length_{0};
  uint32_t generation_{0};
  uint8_t active_bank_{0};
  bool metadata_valid_{false};
};

}  // namespace ui_engine
}  // namespace esphome
