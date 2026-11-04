# Fountain of Colors

![Fountain of Colors complete Ubuntu layout preview](preview.png)

*Reference-based Ubuntu adaptation with an original generated wallpaper. Preview values are examples; installed widgets use live readings.*

```bash
./install.sh fountain-of-colors --auto-location --install-deps
```

Original design: **alatsombath**. [Creator/source](https://www.deviantart.com/alatsombath/art/Fountain-of-Colors-desktop-music-visualizer-518894563) · [Reference preview](https://www.deviantart.com/alatsombath/art/Fountain-of-Colors-desktop-music-visualizer-518894563)

## Included composition and differences

- The 80 live FFT bars and fading peaks use CAVA’s system-playback monitor.
- Default palette follows the current creator preview. Rainmeter’s full settings skin and wallpaper-color extraction are replaced by editable theme data.

All eleven wallpapers are bundled locally. No wallpaper API or image-generation account is required to install. [Generation prompts](../../docs/wallpaper-prompts.md).

The native engine targets GNOME 46–50; collectors and the CAVA pipeline were tested on Ubuntu 26.04 / GNOME 50. Native Shell interaction needs a first-login smoke test before merging. First installation requires one logout/login. Existing Solo Leveling continues to support the wider Desktop Widgets compatibility range.

Use `--city "Your city"` for weather without IP lookup, `--wallpaper /path/to/image.jpg` for your own background, or omit weather flags to disable weather. For news widgets, `--rss-url https://example.com/feed.xml` overrides the default BBC feed.

Audio visualizers capture the default system playback monitor via CAVA; no audio is recorded. Media controls require a running MPRIS-compatible player. Unsupported GPU readings are labeled unavailable.

Undo: `./uninstall.sh`. Other user widgets, notes, backups and shared packages are preserved.
