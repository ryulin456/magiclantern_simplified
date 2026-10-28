#ifndef ML_LANGUAGE_H
#define ML_LANGUAGE_H

/* Called once after config_load(), before the normal ML tasks are started. */
void language_init(void);

/* Apply a stable language ID immediately, retaining the current language on
 * failure. Successful resource loads remain cached until shutdown. Returned
 * translation pointers therefore remain valid across later switches. */
int language_select(int code);
const char *language_translate(const char *source);

#endif
