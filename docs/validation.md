# Validation record

Checked on Ubuntu 26.04 / GNOME 50.1 on 4 November 2026.

- 13 Python tests passed, including all 11 wallpaper checksums, input validation, unique layouts, safe downloads, extension archive traversal rejection, cached weather failures, and both engines' install/switch/uninstall paths.
- Settings integration used `GSETTINGS_BACKEND=memory`. External dconf/extension commands were replaced by test doubles; these tests do not validate actual Shell rendering.
- Python compilation, shell syntax, native JavaScript GJS module parsing and whitespace checks passed.
- Live local collectors returned hardware, MPRIS status, trash count, city weather with a five-day forecast, and public BBC headlines under temporary XDG data/cache directories.
- CAVA emitted 80 FFT bins from the default playback monitor during a silent-input test, then terminated cleanly. Reactive playback appearance still needs a manual check.
- Chrome-rendered illustrative previews were inspected for all eleven compositions. Sample readings/spectrum are clearly marked.

## Before release

The new native extension has not yet been enabled in a real login session. Install on an Ubuntu GNOME test session, log out/in, inspect extension errors, then check every composition, app dropdown/launchers, MPRIS controls, volume, notes, timers, audio with playback, window overlap, lock/unlock and display hotplug. GNOME 46–49 are declared compatibility targets and still need independent machine testing. Do not treat the HTML previews as proof of native Shell behavior.

Solo Leveling retains the existing Desktop Widgets engine. Its newly bundled wallpaper changes the artwork, while its day/date/time/weather/CPU/GPU/RAM layout remains the existing implementation.
