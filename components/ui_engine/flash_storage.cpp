#include "flash_storage.h"

#include <array>
#include <cstdlib>
#include <cstring>
#include <memory>

#include "config_limits.h"

namespace esphome {
namespace ui_engine {

namespace {

static constexpr uint32_t CACHE_MAGIC = 0x55494531;  // "UIE1"
// Version 2 invalidates configurations cached by firmware releases that did
// not yet support the media template. Wi-Fi and touchscreen preferences use
// independent keys and remain untouched.
static constexpr uint16_t CACHE_SCHEMA_VERSION = 2;
static constexpr uint32_t CACHE_PREFERENCE_KEY = 0xC7D00101;
struct CacheRecord {
  uint32_t magic;
  uint16_t schema_version;
  uint16_t length;
  uint32_t checksum;
  std::array<char, UI_CONFIG_MAX_SIZE> json;
};

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
  this->preference_ = global_preferences->make_preference<CacheRecord>(CACHE_PREFERENCE_KEY, true);
}

bool FlashStorage::load(std::string *raw_json, std::string *error) {
  std::unique_ptr<CacheRecord, decltype(&std::free)> record(
      static_cast<CacheRecord *>(std::calloc(1, sizeof(CacheRecord))), &std::free);
  if (record == nullptr) {
    *error = "memoria insuficiente para leer cache flash";
    return false;
  }
  if (!this->preference_.load(record.get())) {
    *error = "cache flash no disponible";
    return false;
  }
  if (record->magic != CACHE_MAGIC || record->schema_version != CACHE_SCHEMA_VERSION) {
    *error = "cache flash incompatible";
    return false;
  }
  if (record->length == 0 || record->length > UI_CONFIG_MAX_SIZE) {
    *error = "longitud de cache flash invalida";
    return false;
  }
  if (fnv1a(record->json.data(), record->length) != record->checksum) {
    *error = "checksum de cache flash invalido";
    return false;
  }

  raw_json->assign(record->json.data(), record->length);
  this->saved_checksum_ = record->checksum;
  this->saved_length_ = record->length;
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

  std::unique_ptr<CacheRecord, decltype(&std::free)> record(
      static_cast<CacheRecord *>(std::calloc(1, sizeof(CacheRecord))), &std::free);
  if (record == nullptr) {
    *error = "memoria insuficiente para guardar cache flash";
    return false;
  }
  record->magic = CACHE_MAGIC;
  record->schema_version = CACHE_SCHEMA_VERSION;
  record->length = static_cast<uint16_t>(raw_json.size());
  record->checksum = checksum;
  std::memcpy(record->json.data(), raw_json.data(), raw_json.size());

  // ESPHome flushes pending preferences from its normal loop. Forcing a full
  // NVS sync here causes extra temporary allocations exactly when a new UI
  // and an online image can coexist in memory.
  if (!this->preference_.save(record.get())) {
    *error = "no se pudo guardar cache flash";
    return false;
  }
  this->saved_checksum_ = checksum;
  this->saved_length_ = raw_json.size();
  return true;
}

}  // namespace ui_engine
}  // namespace esphome
