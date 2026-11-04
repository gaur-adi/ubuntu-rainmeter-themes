# Credits and third-party licensing

- **Desktop Widgets (Desktop Clock)** by Andrew Z / azclock contributors: [GNOME Extensions](https://extensions.gnome.org/extension/5156/desktop-clock/) · [upstream source](https://gitlab.com/AndrewZaech/azclock). Release 21 (version-name 16.1), extension UUID `azclock@azclock.gitlab.com`. Downloaded from the official extension marketplace; its own bundled license applies. No extension source is vendored here.
- **Solo Leveling wallpaper:** [WallpaperSafari listing](https://wallpapersafari.com/w/8NpjeV). Credit visible in the artwork: **Joshua Cayetano**. Anime/manhwa characters and artwork remain the property of their respective owners. This project does not claim ownership or grant redistribution rights. The documentation layout preview contains a reduced-resolution copy of the artwork. The installer fetches the original wallpaper from the linked source for the user's chosen desktop theme; check that source and the rights holder's terms for your use.
- **Open-Meteo:** [weather](https://open-meteo.com/) and [geocoding](https://open-meteo.com/en/docs/geocoding-api). Weather data attribution is displayed in the widget. See the provider's terms for its free non-commercial API and data licensing.
- **ipwho.is:** [IP geolocation API](https://ipwhois.io/documentation), used only when `--auto-location` is selected.
- **Lato:** Łukasz Dziedzic / Lato contributors, installed through Ubuntu's `fonts-lato` package (SIL Open Font License). Font files are not bundled here.

The project's MIT license applies only to original installer, runtime, test, and documentation code. It does not replace any third-party license or confer rights to third-party artwork or trademarks.

## New original wallpapers and independent native widgets

The eleven `wallpaper.png` backgrounds were generated specifically for this repository with the built-in OpenAI image_gen tool. Prompts are recorded in [docs/wallpaper-prompts.md](docs/wallpaper-prompts.md). These new assets replace the originally linked Solo Leveling wallpaper. The documentation previews combine these backgrounds with illustrative renderings of our widget layouts, not the original Rainmeter screenshots.

The ten new layouts are independent GNOME implementations inspired by the named reference projects. Authors, source links, selected compositions and concrete differences are recorded in [docs/2026-research.md](docs/2026-research.md) and each theme's README. Original Windows `.ini` files, DLLs, paid extensions and proprietary icons are not bundled.

- **CAVA**, Karl Stavestrand and contributors: [source and MIT license](https://github.com/karlstav/cava). Installed through Ubuntu packages; supplies real FFT frames from the system playback monitor.
- **MPRIS**, freedesktop.org: [specification](https://specifications.freedesktop.org/mpris-spec/latest/). Used through the local session D-Bus for player information and controls.
- **Natural Earth**, Tom Patterson, Nathaniel Vaughn Kelso and contributors: [public-domain terms](https://www.naturalearthdata.com/about/terms-of-use/). `world-map.json` is derived from the 110m country polygons for an approximate decorative world/day-night map.
- **Roboto Thin**, Google/Christian Robertson: Apache-2.0; pinned font download referenced by the Sonder theme.
- **Allura**, TypeSETit: SIL Open Font License; pinned download referenced by Sonder.
- **Anurati**, Emmeran Richard: separately downloaded for Mond; see the font author's terms. No font files are vendored.
- **BBC News**: public RSS feed used for optional headlines; news text is not redistributed in the repository.

The original code license does not relicense third-party reference themes, fonts or characters. Generated wallpaper asset terms are in [LICENSE-ASSETS.md](LICENSE-ASSETS.md).
