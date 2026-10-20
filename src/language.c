/* File-backed language selection. GPL v2 or later. */
#include "dryos.h"
#include "config.h"
#include "menu.h"
#include "rbf_font.h"
#include "language.h"
#include "language_file.h"

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
static int startup_code;
static uint8_t *catalog;
static int initialized;
CONFIG_INT("menu.language", selected_language, 0);

static int identifier_ok(const char *s)
{
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

static uint8_t *load_bounded_file(const char *path, uint32_t maximum, int *size)
{
    uint32_t length;
    if (FIO_GetFileSize(path, &length) || length > maximum || !length) return 0;
    uint8_t *data = read_entire_file_persistent(path, size);
    if (data && (uint32_t)*size > maximum) { free(data); return 0; }
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

static int selected_index(void)
{
    for (int i = 0; i < choice_count; i++)
        if (choices[i].code == selected_language) return i;
    return 0;
}

static MENU_SELECT_FUNC(select_language)
{
    int index = (selected_index() + delta) % choice_count;
    if (index < 0) index += choice_count;
    selected_language = choices[index].code;
}

static MENU_UPDATE_FUNC(update_language)
{
    MENU_SET_VALUE("%s", choices[selected_index()].name);
    if (selected_language == startup_code && startup_code != active_code)
        MENU_SET_WARNING(MENU_WARN_INFO, "Language resources unavailable. Using English.");
    else if (selected_language != active_code)
        MENU_SET_WARNING(MENU_WARN_INFO, "Save settings and restart to apply the language.");
    MENU_SET_HELP("Choose the menu language. Changes apply after saving settings and restarting.");
}

static struct menu_entry language_menu[] = {
    {
        .name = "Language",
        .priv = &selected_language,
        .select = select_language,
        .update = update_language,
        .help = "Choose the menu language. Changes apply after saving settings and restarting.",
    }
};

const char *language_translate(const char *source)
{
    return language_file_lookup(catalog, source);
}

void language_init(void)
{
    if (initialized) return;
    initialized = 1;
    startup_code = selected_language;
    load_choices();
    int index = selected_index();
    if (index)
    {
        char path[64];
        int size = 0;
        snprintf(path, sizeof(path), "ML/LANG/%s.lng", choices[index].id);
        uint8_t *data = load_bounded_file(path, LANGUAGE_FILE_MAX_SIZE, &size);
        if (data && language_file_validate(data, size))
        {
            int font_status = 0;
            if (choices[index].font[0])
            {
                snprintf(path, sizeof(path), "ML/FONTS/%s.bfn", choices[index].font);
                font_status = bfnt_load_alternate(path);
            }
            if (!font_status)
            {
                catalog = data;
                data = 0;
                active_code = choices[index].code;
            }
        }
        if (data) free(data);
    }
    menu_add("Prefs", language_menu, COUNT(language_menu));
}
