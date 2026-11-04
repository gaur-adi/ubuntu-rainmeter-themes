# Monterey

![Monterey complete Ubuntu layout preview](preview.png)

*Reference-based Ubuntu adaptation with an original generated wallpaper. Preview values are examples; installed widgets use live readings.*

```bash
./install.sh monterey --auto-location --install-deps
```

Original design: **creewick; reference composition by Legend0804**. [Creator/source](https://github.com/creewick/MontereyRainmeter) · [Reference preview](https://www.deviantart.com/legend0804/art/MacOS-Monterey-for-Windows-952714758)

## Included composition and differences

- Includes clock, calendar, five-day weather, hardware meters, music controls, timer, volume and persistent notes.
- The cards use translucent fills; Windows blur plug-ins and OS styling are replaced with GNOME-native widgets.

All eleven wallpapers are bundled locally. No wallpaper API or image-generation account is required to install. [Generation prompts](../../docs/wallpaper-prompts.md).

The native engine targets GNOME 46–50; collectors and the CAVA pipeline were tested on Ubuntu 26.04 / GNOME 50. Native Shell interaction needs a first-login smoke test before merging. First installation requires one logout/login. Existing Solo Leveling continues to support the wider Desktop Widgets compatibility range.

Use `--city "Your city"` for weather without IP lookup, `--wallpaper /path/to/image.jpg` for your own background, or omit weather flags to disable weather. For news widgets, `--rss-url https://example.com/feed.xml` overrides the default BBC feed.

Audio visualizers capture the default system playback monitor via CAVA; no audio is recorded. Media controls require a running MPRIS-compatible player. Unsupported GPU readings are labeled unavailable.

Undo: `./uninstall.sh`. Other user widgets, notes, backups and shared packages are preserved.
