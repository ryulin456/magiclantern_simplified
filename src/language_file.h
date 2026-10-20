#ifndef ML_LANGUAGE_FILE_H
#define ML_LANGUAGE_FILE_H

#include <stdint.h>

#define LANGUAGE_FILE_MAX_SIZE (1024u * 1024u)
#define LANGUAGE_FILE_MAX_ENTRIES 8192u

/* The buffer remains owned by the caller and must outlive lookups. */
int language_file_validate(const uint8_t *data, uint32_t size);
const char *language_file_lookup(const uint8_t *validated_data, const char *source);
int language_format_compatible(const char *source, const char *translation);

#endif
