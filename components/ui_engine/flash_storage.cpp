#include "flash_storage.h"

#include <algorithm>
#include <array>
#include <cstring>

#include "config_limits.h"

namespace esphome {
namespace ui_engine {

namespace {

static constexpr uint32_t CACHE_MAGIC = 0x55494531;  // "UIE1"
static constexpr uint16_t CACHE_SCHEMA_VERSION = 3;
static constexpr uint32_t CACHE_METADATA_KEY = 0xC7D00110;
static constexpr uint32_t CACHE_CHUNK_KEY_BASE = 0xC7D00200;

uint32_t fnv1a(const char *data, size_t length) {
  uint32_t hash = 2166136261UL;
  for (size_t index = 0; index < length; index++) {
    hash ^= static_cast<uint8_t>(data[index]);
    hash *= 16777619UL;
  }
  return hash;
}

}  // namespace

void FlashStorage::begin() {
  this->metadata_preference_ = global_preferences->make_preference<CacheMetadata>(CACHE_METADATA_KEY, true);
  for (size_t bank = 0; bank < CACHE_BANK_COUNT; bank++) {
    for (size_t chunk = 0; chunk < CACHE_CHUNK_COUNT; chunk++) {
      const uint32_t key = CACHE_CHUNK_KEY_BASE + static_cast<uint32_t>(bank * CACHE_CHUNK_COUNT + chunk);
      this->chunk_preferences_[bank][chunk] = global_preferences->make_preference<CacheChunk>(key, true);
    }
  }
}

bool FlashStorage::load(std::string *raw_json, std::string *error) {
  CacheMetadata metadata{};
  if (!this->metadata_preference_.load(&metadata)) {
    *error = "cache flash no disponible";
    return false;
  }
  if (metadata.magic != CACHE_MAGIC || metadata.schema_version != CACHE_SCHEMA_VERSION ||
      metadata.active_bank >= CACHE_BANK_COUNT) {
    *error = "cache flash incompatible";
    return false;
  }
  if (metadata.length == 0 || metadata.length > UI_CONFIG_MAX_SIZE) {
    *error = "longitud de cache flash invalida";
    return false;
  }

  raw_json->clear();
  raw_json->reserve(metadata.length);
  size_t remaining = metadata.length;
  for (size_t chunk_index = 0; remaining > 0; chunk_index++) {
    CacheChunk chunk{};
    if (!this->chunk_preferences_[metadata.active_bank][chunk_index].load(&chunk)) {
      raw_json->clear();
      *error = "cache flash incompleta";
      return false;
    }
    const size_t copy_length = std::min(remaining, CACHE_CHUNK_SIZE);
    raw_json->append(reinterpret_cast<const char *>(chunk.data.data()), copy_length);
    remaining -= copy_length;
  }

  if (fnv1a(raw_json->data(), raw_json->size()) != metadata.checksum) {
    raw_json->clear();
    *error = "checksum de cache flash invalido";
    return false;
  }

  this->active_bank_ = metadata.active_bank;
  this->generation_ = metadata.generation;
  this->saved_checksum_ = metadata.checksum;
  this->saved_length_ = metadata.length;
  this->metadata_valid_ = true;
  return true;
}

bool FlashStorage::save(const std::string &raw_json, std::string *error) {
  if (raw_json.empty() || raw_json.size() > UI_CONFIG_MAX_SIZE) {
    *error = "configuracion fuera del limite de cache flash";
    return false;
  }

  const uint32_t checksum = fnv1a(raw_json.data(), raw_json.size());
  if (this->saved_length_ == raw_json.size() && this->saved_checksum_ == checksum) {
    return true;
  }

  // Write the complete configuration to the inactive bank in small blocks.
  // ESPHome copies preference values before persisting them; keeping each copy
  // at 1 KiB prevents the large contiguous allocation that used to reboot the
  // ESP32 when a full 16 KiB CacheRecord was saved after rebuilding the UI.
  const uint8_t target_bank = this->metadata_valid_ ? static_cast<uint8_t>(1U - this->active_bank_) : 0U;
  size_t offset = 0;
  size_t chunk_index = 0;
  while (offset < raw_json.size()) {
    CacheChunk chunk{};
    const size_t copy_length = std::min(raw_json.size() - offset, CACHE_CHUNK_SIZE);
    std::memcpy(chunk.data.data(), raw_json.data() + offset, copy_length);
    if (!this->chunk_preferences_[target_bank][chunk_index].save(&chunk)) {
      *error = "no se pudo guardar un bloque de cache flash";
      return false;
    }
    offset += copy_length;
    chunk_index++;
  }

  // Commit the new bank last. Until this small record is saved, an interrupted
  // write leaves the previous bank selected and fully usable.
  CacheMetadata metadata{};
  metadata.magic = CACHE_MAGIC;
  metadata.schema_version = CACHE_SCHEMA_VERSION;
  metadata.active_bank = target_bank;
  metadata.length = static_cast<uint16_t>(raw_json.size());
  metadata.checksum = checksum;
  metadata.generation = this->generation_ + 1;
  if (!this->metadata_preference_.save(&metadata)) {
    *error = "no se pudo confirmar cache flash";
    return false;
  }

  this->active_bank_ = target_bank;
  this->generation_ = metadata.generation;
  this->saved_checksum_ = checksum;
  this->saved_length_ = raw_json.size();
  this->metadata_valid_ = true;
  return true;
}

}  // namespace ui_engine
}  // namespace esphome
