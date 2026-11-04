# 2026 Rainmeter reference research

Inspected in Chrome on **3 November 2026**. This is a curated shortlist of recognizable, repeatedly recommended projects, not an official 1–10 download chart. Some are long-running projects popular in current recommendations rather than new releases from 2026.

Discovery sources: [Beebom's 2026 roundup](https://beebom.com/rainmeter-skins/), [RankRed's 2026 roundup](https://www.rankred.com/rainmeter-skins/), and original creator/source pages linked in each theme's README. Creator pages were used to identify compositions, widgets, fonts and platform dependencies; promotional ranking alone was not treated as proof of compatibility.

| Folder | Reference inspected | Composition selected |
| --- | --- | --- |
| `mond` | [ApexXx-SenSei](https://www.deviantart.com/apexxx-sensei/art/Mond-762455575) · [preview](https://visualskins.com/media/p/565/mond-rainmeter.jpg) | Anurati day heading, centered date/time, lower media/weather, corner trash |
| `sonder` | [upstream source and screenshot](https://github.com/mpurses/Sonder) | Thin split-color clock, world map, right-hand forecast/calendar/meters |
| `droptop-four` | [official site](https://www.droptopfour.com/) · [preview](https://www.droptopfour.com/img/Home-min.webp) | Dark full-width menu bar above an ocean wallpaper |
| `jaxcore` | [ModularClocks](https://github.com/Jax-Core/Modularclocks) · [ModularPlayers](https://github.com/Jax-Core/ModularPlayers) | Large stacked clock plus weather/player modules; JaxCore has no single fixed layout |
| `monterey` | [reference composition](https://www.deviantart.com/legend0804/art/MacOS-Monterey-for-Windows-952714758) · [widget source](https://github.com/creewick/MontereyRainmeter) | Right-hand dark cards: time, calendar, weather, meters, player, timer, volume and notes |
| `big-sur` | [current Big Sur 26 creator page](https://www.deviantart.com/fediafedia/art/Big-Sur-BETA-3-for-Rainmeter-846882462) | Central translucent card grid over a green botanical background |
| `omnimo` | [Omnimo source](https://github.com/fediaFedia/Omnimo) · [module previews](https://visualskins.com/skin/omnimo-10) | Large clock/date plus white system-information tiles, news and shortcuts |
| `enigma` | [source](https://github.com/Kaelri/Enigma) · [suite preview](https://static.beebom.com/wp-content/uploads/2019/01/enigma-theme.jpg) | Left/right information sidebars, central analog clock and edge launchers |
| `monstercat` | [official source](https://github.com/marcopixel/monstercat-visualizer) | White audio spectrum with media metadata and controls |
| `fountain-of-colors` | [creator](https://www.deviantart.com/alatsombath/art/Fountain-of-Colors-desktop-music-visualizer-518894563) | 80 magenta/purple FFT bars and fading peaks over a starry sky |

Examples of public popularity signals observed during research: Mond's creator page showed approximately **2.9 million views**, Big Sur approximately **2.9 million**, and Fountain of Colors approximately **3.1 million**. These are cumulative creator-page views, not 2026-only downloads, and should not be compared as a formal ranking.

## Fidelity and licensing decisions

The user requested an original generated wallpaper for **every theme**, including the existing Solo Leveling theme. The backgrounds are therefore new artwork matched to each reference's mood and composition. They are intentionally not the source screenshots' original wallpapers.

The native widgets are independent Ubuntu implementations. They recreate the selected composition, but do not claim pixel-identical rendering or the entire Windows suite/framework. Original Windows plug-ins, proprietary blur, paid Droptop features, and JaxCore's complete module hub are not bundled. Each theme's README lists included functionality and concrete differences.

No Rainmeter `.ini` code, DLLs, proprietary application icons, or original wallpaper assets are vendored. Font downloads are separately attributed and pinned. The world map is built from public-domain Natural Earth geographic data.

The native engine targets GNOME 46–50. JavaScript parsing, collector/CAVA checks, isolated installer tests and Chrome-rendered illustrative previews are automated or reproducible. A fresh-login GNOME Shell interaction check remains a manual pre-merge step; rendered HTML previews are not presented as real Shell screenshots.
