# Solo Leveling

![Solo Leveling complete theme layout](preview.png)

*Illustrative preview rendered from the theme settings. Readings are examples; installed widgets update live. Font rendering and spacing depend on display scaling.*

```bash
./install.sh solo-leveling --auto-location --install-deps
```

Run from the repository root. The theme adds a left-side day/date/time/weather stack and red-accent CPU/RAM/GPU statistics to every connected display.

- Wallpaper: [source and download listing](https://wallpapersafari.com/w/8NpjeV).
- Artist credit visible in wallpaper: Joshua Cayetano.
- Original artwork is downloaded during installation. The documentation preview contains credited artwork, which is not included under the project's MIT license. All character and artwork rights belong to their respective owners.
- Font: Lato (falls back to an installed system font when unavailable).
- GPU measurements depend on your GPU and driver. The indicators are decorative rings with live numeric readings.

Use `./install.sh solo-leveling --city "Your city"` for weather without an IP lookup, or omit weather flags to keep it off.

Edit `theme.json` to change colors and normalized clock/statistics positions, then rerun the command. To undo: `./uninstall.sh`.
