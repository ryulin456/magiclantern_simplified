/* Language-neutral MLLG v2 catalog reader. See tools/localization/README.md.
 * GPL v2 or later, following the surrounding Magic Lantern source. */
#include "language_file.h"

static uint32_t read_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint32_t text_hash(const char *text)
{
    uint32_t hash = 0x811c9dc5;
    while (*text)
    {
        hash ^= (uint8_t)*text++;
        hash *= 0x01000193;
    }
    return hash;
}

/* Validate the string without reading past the declared pool. */
static int valid_text(const uint8_t *p, uint32_t remaining)
{
    while (remaining)
    {
        unsigned c = *p++;
        remaining--;
        if (!c) return 1;
        if (c < 0x80) continue;
        unsigned extra, value, minimum;
        if (c >= 0xc2 && c <= 0xdf) { extra = 1; value = c & 31; minimum = 0x80; }
        else if (c >= 0xe0 && c <= 0xef) { extra = 2; value = c & 15; minimum = 0x800; }
        else if (c >= 0xf0 && c <= 0xf4) { extra = 3; value = c & 7; minimum = 0x10000; }
        else return 0;
        if (remaining < extra) return 0;
        for (unsigned i = 0; i < extra; i++)
        {
            c = *p++;
            remaining--;
            if ((c & 0xc0) != 0x80) return 0;
            value = value * 64 + (c & 63);
        }
        if (value < minimum || value > 0x10ffff ||
            (value >= 0xd800 && value <= 0xdfff)) return 0;
    }
    return 0;
}

int language_file_validate(const uint8_t *data, uint32_t size)
{
    if (!data || size < 20 || size > LANGUAGE_FILE_MAX_SIZE) return 0;
    if (read_u32(data) != 0x474c4c4d || read_u32(data + 4) != 2) return 0;
    uint32_t count = read_u32(data + 8);
    uint32_t offset = read_u32(data + 12);
    uint32_t pool_size = read_u32(data + 16);
    if (count > LANGUAGE_FILE_MAX_ENTRIES || offset != 20 + count * 12 ||
        offset > size || pool_size != size - offset) return 0;
    uint32_t previous = 0;
    for (uint32_t i = 0; i < count; i++)
    {
        const uint8_t *entry = data + 20 + i * 12;
        uint32_t hash = read_u32(entry);
        uint32_t key = read_u32(entry + 4);
        uint32_t value = read_u32(entry + 8);
        if ((i && hash < previous) || key >= pool_size || value >= pool_size ||
            !valid_text(data + offset + key, pool_size - key) ||
            !valid_text(data + offset + value, pool_size - value) ||
            !data[offset + key] ||
            text_hash((const char *)data + offset + key) != hash) return 0;
        previous = hash;
    }
    return 1;
}

const char *language_file_lookup(const uint8_t *data, const char *source)
{
    if (!data || !source || !*source) return source;
    uint32_t count = read_u32(data + 8), lo = 0, hi = count;
    uint32_t hash = text_hash(source), pool = read_u32(data + 12);
    while (lo < hi)
    {
        uint32_t mid = lo + (hi - lo) / 2;
        if (read_u32(data + 20 + mid * 12) < hash) lo = mid + 1;
        else hi = mid;
    }
    for (; lo < count; lo++)
    {
        const uint8_t *entry = data + 20 + lo * 12;
        if (read_u32(entry) != hash) break;
        const char *key = (const char *)data + pool + read_u32(entry + 4);
        const char *a = source, *b = key;
        while (*a && *a == *b) { a++; b++; }
        if (*a == *b) return (const char *)data + pool + read_u32(entry + 8);
    }
    return source;
}

/* Return the next exact printf directive. Unsupported formats use English. */
static const char *next_format(const char *s, const char **end)
{
    while (*s && *s != '%') s++;
    const char *start = s;
    if (!*s) { *end = s; return s; }
    s++;
    while (*s == '-' || *s == '+' || *s == ' ' || *s == '#' || *s == '0') s++;
    while (*s >= '0' && *s <= '9') s++;
    if (*s == '.') { s++; while (*s >= '0' && *s <= '9') s++; }
    if (*s == 'h' || *s == 'l')
    {
        char length = *s++;
        if (*s == length) s++;
    }
    else if (*s == 'j' || *s == 'z' || *s == 't' || *s == 'L') s++;
    const char *allowed = "diouxXfFeEgGaAcsp%";
    if (!*s) return 0;
    while (*allowed && *allowed != *s) allowed++;
    if (!*allowed) return 0;
    *end = s + 1;
    return start;
}

int language_format_compatible(const char *source, const char *translation)
{
    if (!source || !translation) return 0;
    while (1)
    {
        const char *a_end, *b_end;
        const char *a = next_format(source, &a_end);
        const char *b = next_format(translation, &b_end);
        if (!a || !b) return 0;
        if (!*a || !*b) return !*a && !*b;
        while (a < a_end && b < b_end)
            if (*a++ != *b++) return 0;
        if (a != a_end || b != b_end) return 0;
        source = a_end;
        translation = b_end;
    }
}
