/* File-backed language selection. GPL v2 or later. */
#include "dryos.h"
#include "config.h"
#include "menu.h"
#include "rbf_font.h"
#include "language.h"
#include "language_file.h"
#include "resource_barrier.h"

#define MAX_LANGUAGES 16
#define INDEX_MAX_SIZE 2048

typedef struct
{
    char id[16];
    char name[48];
    char font[16];
    int code;
} language_choice;

/* Only the small selector is in the core. Text and fonts remain on the card. */
static language_choice choices[MAX_LANGUAGES] = {{ "", "English", "", 0 }};
static int choice_count = 1;
static int active_code;
static uint8_t * volatile catalog;
static int initialized;
static int load_failed;
/* Preserve the failing operation for real-camera diagnosis.  File I/O in host
 * tests cannot reveal every camera/card-specific failure. */
static int load_error;
static char load_error_path[64];
static struct semaphore *switch_sem;

typedef struct
{
    uint8_t *catalog;
    bfnt_font *font;
    int loaded;
} language_resource;

/* Callers may retain a translated pointer. Successful loads stay immutable
 * until shutdown, so switching never frees a string or glyph still in use.
 * Each language is loaded at most once; languages sharing a font reuse it. */
static language_resource resources[MAX_LANGUAGES];
CONFIG_INT("menu.language", selected_language, 0);

static int identifier_ok(const char *s)
{
    /* Resource files use portable 8.3 names, including on older card APIs. */
    if (strlen(s) > 8) return 0;
    if (*s < 'a' || *s > 'z') return 0;
    for (; *s; s++)
        if (!(*s >= 'a' && *s <= 'z') && !(*s >= '0' && *s <= '9') && *s != '_') return 0;
    return 1;
}

static int language_code(const char *s)
{
    uint32_t h = 0x811c9dc5;
    while (*s) { h ^= (uint8_t)*s++; h *= 0x01000193; }
    return h & 0x7fffffff;
}

static void set_load_error(int error, const char *path)
{
    load_error = error;
    snprintf(load_error_path, sizeof(load_error_path), "%s", path ? path : "");
}

static uint8_t *load_bounded_file(const char *path, uint32_t maximum, int *size)
{
    uint32_t length;
    if (FIO_GetFileSize(path, &length))
    {
        set_load_error(2, path); /* path not found / stat failed */
        return 0;
    }
    if (length > maximum || !length)
    {
        set_load_error(3, path); /* invalid file size */
        return 0;
    }
    uint8_t *data = read_entire_file_persistent(path, size);
    if (!data)
    {
        set_load_error(4, path); /* open, read or allocation failed */
        return 0;
    }
    if ((uint32_t)*size != length)
    {
        free(data);
        set_load_error(3, path);
        return 0;
    }
    return data;
}

static void load_choices(void)
{
    int size = 0;
    char *data = (char *)load_bounded_file("ML/LANG/INDEX.TXT", INDEX_MAX_SIZE, &size);
    if (!data) return;
    char *line = data;
    while (line < data + size && choice_count < MAX_LANGUAGES)
    {
        char *end = strchr(line, '\n');
        if (!end) end = data + size;
        if (end > line && end[-1] == '\r') end[-1] = 0;
        *end = 0;
        if (*line && *line != '#')
        {
            char *name = strchr(line, '\t');
            if (name)
            {
                *name++ = 0;
                char *font = strchr(name, '\t');
                if (font) *font++ = 0;
                else font = "";
                int valid = strlen(line) < sizeof(choices[0].id) && identifier_ok(line) &&
                    *name && strlen(name) < sizeof(choices[0].name) &&
                    strlen(font) < sizeof(choices[0].font) && (!*font || identifier_ok(font));
                for (const char *s = name; *s; s++)
                    if ((uint8_t)*s < 32 || (uint8_t)*s > 126) valid = 0;
                int code = language_code(line);
                for (int i = 0; i < choice_count; i++)
                    if (choices[i].code == code) valid = 0;
                if (valid)
                {
                    language_choice *choice = &choices[choice_count++];
                    snprintf(choice->id, sizeof(choice->id), "%s", line);
                    snprintf(choice->name, sizeof(choice->name), "%s", name);
                    snprintf(choice->font, sizeof(choice->font), "%s", font);
                    choice->code = code;
                }
            }
        }
        line = end + 1;
    }
    free(data);
}

static int index_for_code(int code)
{
    for (int i = 0; i < choice_count; i++)
        if (choices[i].code == code) return i;
    return -1;
}

/* Called with the switch semaphore held, or once during single-task startup. */
static int activate_language(int index)
{
    if (index < 0 || index >= choice_count)
    {
        set_load_error(1, "ML/LANG/INDEX.TXT");
        return 0;
    }
    language_resource *next = &resources[index];
    if (!next->loaded)
    {
        char path[64];
        int size = 0;
        snprintf(path, sizeof(path), "ML/LANG/%s.lng", choices[index].id);
        uint8_t *data = load_bounded_file(path, LANGUAGE_FILE_MAX_SIZE, &size);
        if (!data) return 0;
        if (!language_file_validate(data, size))
        {
            set_load_error(5, path); /* catalog header, table or text invalid */
            free(data);
            return 0;
        }
        bfnt_font *font = 0;
        if (choices[index].font[0])
        {
            for (int i = 1; i < choice_count; i++)
                if (resources[i].loaded && streq(choices[i].font, choices[index].font))
                {
                    font = resources[i].font;
                    break;
                }
            if (!font)
            {
                snprintf(path, sizeof(path), "ML/FONTS/%s.bfn", choices[index].font);
                int font_error = bfnt_prepare_alternate(path, &font);
                if (font_error)
                {
                    /* 7: font path/size; 8: read/allocation;
                     * 9: invalid header; 10: invalid glyph. */
                    set_load_error(6 + font_error, path);
                    free(data);
                    return 0;
                }
            }
        }
        next->catalog = data;
        next->font = font;
        next->loaded = 1;
    }

    /* Publish only after both resources are ready. Failed preparation above
     * cannot change the current font, catalog, preference or cache entry. */
    bfnt_activate_alternate(next->font);
    resource_publish_barrier();
    catalog = next->catalog;
    active_code = choices[index].code;
    selected_language = active_code;
    set_load_error(0, "");
    return 1;
}

int language_select(int code)
{
    if (!initialized || !switch_sem || take_semaphore(switch_sem, 100)) return 0;
    int ok = activate_language(index_for_code(code));
    load_failed = !ok;
    give_semaphore(switch_sem);
    menu_redraw();
    return ok;
}

static MENU_SELECT_FUNC(select_language)
{
    int current = index_for_code(active_code);
    int index = (MAX(current, 0) + delta) % choice_count;
    if (index < 0) index += choice_count;
    language_select(choices[index].code);
}

static MENU_UPDATE_FUNC(update_language)
{
    MENU_SET_VALUE("%s", choices[MAX(index_for_code(active_code), 0)].name);
    if (load_failed)
    {
        MENU_SET_WARNING(MENU_WARN_INFO, "%s [E%d]",
            menu_translate("Cannot load language. Current language kept."), load_error);
        MENU_SET_HELP("E%d: %s", load_error, load_error_path);
    }
    else MENU_SET_HELP("Press SET to switch language now. Save settings to remember it.");
}

static struct menu_entry language_menu[] = {
    {
        .name = "Language",
        .priv = &selected_language,
        .select = select_language,
        .update = update_language,
        .icon_type = IT_ACTION,
        .help = "Press SET to switch language now. Save settings to remember it.",
    }
};

const char *language_translate(const char *source)
{
    return language_file_lookup(catalog, source);
}

void language_init(void)
{
    if (initialized) return;
    int requested = selected_language;
    selected_language = 0;
    resources[0].loaded = 1; /* English needs no card resources. */
    load_choices();
    switch_sem = create_named_semaphore("ml_lang", SEM_CREATE_UNLOCKED);
    if (switch_sem) load_failed = !activate_language(index_for_code(requested));
    else
    {
        set_load_error(11, "ml_lang semaphore");
        load_failed = 1;
    }
    initialized = 1;
    menu_add("Prefs", language_menu, COUNT(language_menu));
}
