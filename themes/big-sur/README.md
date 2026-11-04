# Big Sur 26

![Big Sur 26 complete Ubuntu layout preview](preview.png)

*Reference-based Ubuntu adaptation with an original generated wallpaper. Preview values are examples; installed widgets use live readings.*

```bash
./install.sh big-sur --auto-location --install-deps
```

Original design: **fediaFedia**. [Creator/source](https://www.deviantart.com/fediafedia/art/Big-Sur-BETA-3-for-Rainmeter-846882462) · [Reference preview](https://www.deviantart.com/fediafedia/art/Big-Sur-BETA-3-for-Rainmeter-846882462)

## Included composition and differences

- Includes the Big Sur 26-style centered glass-card grid, analog/digital clocks, calendar, weather, launcher, media, meters, timer, volume, notes and news.
- Cards have translucent backgrounds; proprietary Windows blur and full application-specific panels are not ported. App icons come from programs installed on Ubuntu.

All eleven wallpapers are bundled locally. No wallpaper API or image-generation account is required to install. [Generation prompts](../../docs/wallpaper-prompts.md).

The native engine targets GNOME 46–50; collectors and the CAVA pipeline were tested on Ubuntu 26.04 / GNOME 50. Native Shell interaction needs a first-login smoke test before merging. First installation requires one logout/login. Existing Solo Leveling continues to support the wider Desktop Widgets compatibility range.

Use `--city "Your city"` for weather without IP lookup, `--wallpaper /path/to/image.jpg` for your own background, or omit weather flags to disable weather. For news widgets, `--rss-url https://example.com/feed.xml` overrides the default BBC feed.

Audio visualizers capture the default system playback monitor via CAVA; no audio is recorded. Media controls require a running MPRIS-compatible player. Unsupported GPU readings are labeled unavailable.

Undo: `./uninstall.sh`. Other user widgets, notes, backups and shared packages are preserved.
