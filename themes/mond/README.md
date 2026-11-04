# Mond

![Mond complete Ubuntu layout preview](preview.png)

*Reference-based Ubuntu adaptation with an original generated wallpaper. Preview values are examples; installed widgets use live readings.*

```bash
./install.sh mond --auto-location --install-deps
```

Original design: **ApexXx-SenSei**. [Creator/source](https://www.deviantart.com/apexxx-sensei/art/Mond-762455575) · [Reference preview](https://visualskins.com/media/p/565/mond-rainmeter.jpg)

## Included composition and differences

- Independent recreation of the day/date/time, weather, media and trash composition.
- The creator’s wallpaper link is offline; the included wallpaper is newly generated.
- Anurati is fetched separately; the Windows settings skin and legacy Spotify plug-in are replaced by native GNOME/MPRIS controls.

All eleven wallpapers are bundled locally. No wallpaper API or image-generation account is required to install. [Generation prompts](../../docs/wallpaper-prompts.md).

The native engine targets GNOME 46–50; collectors and the CAVA pipeline were tested on Ubuntu 26.04 / GNOME 50. Native Shell interaction needs a first-login smoke test before merging. First installation requires one logout/login. Existing Solo Leveling continues to support the wider Desktop Widgets compatibility range.

Use `--city "Your city"` for weather without IP lookup, `--wallpaper /path/to/image.jpg` for your own background, or omit weather flags to disable weather. For news widgets, `--rss-url https://example.com/feed.xml` overrides the default BBC feed.

Audio visualizers capture the default system playback monitor via CAVA; no audio is recorded. Media controls require a running MPRIS-compatible player. Unsupported GPU readings are labeled unavailable.

Undo: `./uninstall.sh`. Other user widgets, notes, backups and shared packages are preserved.
