# Enigma

![Enigma complete Ubuntu layout preview](preview.png)

*Reference-based Ubuntu adaptation with an original generated wallpaper. Preview values are examples; installed widgets use live readings.*

```bash
./install.sh enigma --auto-location --install-deps
```

Original design: **Kaelri and contributors**. [Creator/source](https://github.com/Kaelri/Enigma) · [Reference preview](https://static.beebom.com/wp-content/uploads/2019/01/enigma-theme.jpg)

## Included composition and differences

- Includes information sidebars, an analog clock, calendar, notes, current system/network readings, weather, media, headlines and application shortcuts.
- The source suite’s process-specific charts, image-gallery slideshow and Windows tray integration are not implemented.

All eleven wallpapers are bundled locally. No wallpaper API or image-generation account is required to install. [Generation prompts](../../docs/wallpaper-prompts.md).

The native engine targets GNOME 46–50; collectors and the CAVA pipeline were tested on Ubuntu 26.04 / GNOME 50. Native Shell interaction needs a first-login smoke test before merging. First installation requires one logout/login. Existing Solo Leveling continues to support the wider Desktop Widgets compatibility range.

Use `--city "Your city"` for weather without IP lookup, `--wallpaper /path/to/image.jpg` for your own background, or omit weather flags to disable weather. For news widgets, `--rss-url https://example.com/feed.xml` overrides the default BBC feed.

Audio visualizers capture the default system playback monitor via CAVA; no audio is recorded. Media controls require a running MPRIS-compatible player. Unsupported GPU readings are labeled unavailable.

Undo: `./uninstall.sh`. Other user widgets, notes, backups and shared packages are preserved.
