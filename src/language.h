#ifndef ML_LANGUAGE_H
#define ML_LANGUAGE_H

/* Called once after config_load(), before the normal ML tasks are started.
 * A selected language owns immutable resources for this boot. */
void language_init(void);
const char *language_translate(const char *source);

#endif
