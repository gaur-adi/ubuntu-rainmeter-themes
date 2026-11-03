# Ubuntu Rainmeter Themes

Rainmeter-style desktop themes for **Ubuntu's GNOME desktop**. Pick a theme folder and apply a coordinated wallpaper, clock, weather, and system statistics with one installer command.

**Personal project by [gaur-adi](https://github.com/gaur-adi).** Built using [Desktop Widgets](https://extensions.gnome.org/extension/5156/desktop-clock/), a GNOME extension; Windows Rainmeter skins are not required.

## Quick start

Run these commands in a Terminal inside your Ubuntu desktop, as your normal user:

```bash
git clone https://github.com/gaur-adi/ubuntu-rainmeter-themes.git
cd ubuntu-rainmeter-themes
./install.sh solo-leveling --auto-location --install-deps
```

`solo-leveling` is the theme folder name. `--install-deps` allows the installer to use `sudo apt` **only if required Ubuntu dependencies are missing**. Run the installer itself without `sudo`.

**First installation:** log out and sign back in once to load the new GNOME extension. Subsequent theme changes update immediately when Desktop Widgets is active. If you disabled user extensions globally, enable them in the Extensions app.

### Solo Leveling

[![Solo Leveling wallpaper](https://cdn.wallpapersafari.com/34/29/8NpjeV.jpg)](https://wallpapersafari.com/w/8NpjeV)

*Background artwork preview; the live widgets are added during installation.* Artwork credit appears in the image: Joshua Cayetano. [Wallpaper source](https://wallpapersafari.com/w/8NpjeV).

- Sung Jin-Woo wallpaper matching the reference design.
- Spaced day name, date, and a live clock with red separators.
- Weather: temperature, conditions, city, and humidity.
- Live CPU usage and RAM consumption.
- GPU utilization, GPU temperature, and VRAM when available.
- A clock/weather stack and statistics stack on each connected display.

The red ring symbols are decorative indicators; the numbers are live measurements. This version does not implement circular progress gauges, a music player, an app dock, or animated wallpapers.

## Choose how weather finds you

Automatic approximate location:

```bash
./install.sh solo-leveling --auto-location
```

This sends your public connection IP to [ipwho.is](https://ipwhois.io/documentation) to obtain approximate city coordinates, then requests weather from [Open-Meteo](https://open-meteo.com/). VPNs and ISP routing can select a nearby or different city. The local cache stores city/coordinates, not the full IP lookup response. Location refreshes approximately hourly; weather every 15 minutes. Offline weather is marked `cached` and expires after six hours.

Choose a city instead of an IP lookup:

```bash
./install.sh solo-leveling --city "Agra"
```

No weather/network location lookup:

```bash
./install.sh solo-leveling
```

Wallpaper and extension downloads still require internet on first installation. Weather is optional and requires no API key.

## Requirements and compatibility

| Item | Support |
| --- | --- |
| Desktop | Ubuntu GNOME, including Wayland; not KDE or XFCE |
| GNOME Shell | 45–51, as declared by the pinned Desktop Widgets release |
| Tested desktop | GNOME 50.1 on Ubuntu 26.04, with three displays |
| CPU / RAM | Linux `/proc`, without elevated permissions |
| NVIDIA GPU | Installed working NVIDIA driver and `nvidia-smi` |
| AMD GPU | Best effort using readable `gpu_busy_percent`, VRAM, and hwmon sysfs files |
| Intel / other GPU | CPU/RAM remain available; unsupported GPU readings are labeled unavailable |

Other supported GNOME releases and AMD hardware have **not** been validated on physical machines by this project. Drivers are not installed or replaced. If several GPUs are present, this version displays the first usable GPU, not separate statistics for every GPU.

The layout follows the reference on landscape displays. Portrait or very small displays may need adjustment in Desktop Widgets preferences. After adding/removing/rearranging displays, rerun the install command to rebuild one set per connected display. Display indexes, rather than connector-specific profiles, are used.

## Other commands

```bash
# List available theme folders
./install.sh --list

# Inspect the current display plan, without downloads or desktop changes
./install.sh solo-leveling --auto-location --dry-run

# Adjust widget size, placement, font, and colors manually
gnome-extensions prefs azclock@azclock.gitlab.com

# Undo the managed theme
./uninstall.sh
```

Rerunning installation regenerates this project's widgets from the theme file. Other Desktop Widgets entries are preserved. Existing widgets can overlap the theme; move or disable those in extension preferences.

## Undo and recovery

Before the first managed install, the installer saves your previous wallpaper and extension state under:

```text
~/.local/share/ubuntu-rainmeter-themes/
```

`./uninstall.sh` removes only this project's widgets. It restores your previous wallpaper if the managed wallpaper is still selected; a wallpaper you selected afterward is preserved. Other widgets and extensions are kept. Shared dependencies, Desktop Widgets itself, downloaded artwork, and recovery backups remain on disk.

`before-install.dconf` is an additional full snapshot of Desktop Widgets settings for manual recovery. Uninstall does not load this snapshot over your later edits. Data/cache paths respect `XDG_DATA_HOME` and `XDG_CACHE_HOME`.

If a download changes, checksum validation stops installation before desktop changes. If applying settings fails, the installer attempts to restore the pre-run widget settings and wallpaper. Inspect the printed error before retrying.

## Add a theme

Each theme has its own folder:

```text
themes/
└── solo-leveling/
    ├── theme.json
    └── README.md
```

Copy `themes/solo-leveling/` to a new kebab-case folder, then update `theme.json`:

- Set `id` to the folder name and set a display `name`.
- Supply an HTTPS wallpaper URL, its SHA-256 checksum, source, and artist credit.
- Choose font and hex colors; use an installed font.
- Set clock/statistics positions as fractions of the monitor dimensions, from `0` to `1`.

Use a wallpaper you may use and share, and document its license. This repository downloads the current example wallpaper to the user's machine rather than redistributing the image in Git. Link availability and third-party rights remain separate from the code license.

Check a wallpaper checksum with:

```bash
sha256sum your-wallpaper.jpg
```

Then run:

```bash
./install.sh your-theme --auto-location
```

## Development

Python standard library plus Ubuntu's PyGObject bindings; no pip environment is required.

```bash
/usr/bin/python3 -m unittest discover -s tests -v
```

The schema integration test runs only with an explicit isolated in-memory settings backend:

```bash
GSETTINGS_BACKEND=memory \
URT_TEST_EXTENSION="$HOME/.local/share/gnome-shell/extensions/azclock@azclock.gitlab.com" \
/usr/bin/python3 -m unittest discover -s tests -v
```

GitHub Actions verifies the pinned extension checksum and runs these tests in isolation. Tests cover unsafe downloads/archive paths, repeated installs in the schema layer, preserving existing widgets, display counts, weather failure caching, and missing GPU reporting.

## Credits and license

Installer and collector code: [MIT](LICENSE). [Credits and third-party licensing](CREDITS.md) cover Desktop Widgets, weather/location services, font, and wallpaper. The MIT license grants no rights to anime characters, wallpaper artwork, or third-party extension code.
