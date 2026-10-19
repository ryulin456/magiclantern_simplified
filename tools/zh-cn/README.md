# Preserved localization tools

These are the original project's supporting translation, extraction, audit and packaging scripts. They were reconstructed as a separate commit so they can be reviewed independently of the firmware changes.

Several historical packaging tools expect the old multi-tree workspace layout (including a directory named magiclantern-zh-src), external original camera ZIPs, symbols, or Noto font inputs. Moving them here does not assert they work without those inputs. See each command's argument parser; do not guess addresses or cross camera versions. Runtime generated resources are already included in data/fonts and src/zh_cn*.h.
