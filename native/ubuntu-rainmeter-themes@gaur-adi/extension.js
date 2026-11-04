import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Pango from 'gi://Pango';
import St from 'gi://St';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import Cairo from 'cairo';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Slider from 'resource:///org/gnome/shell/ui/slider.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const DATA = GLib.build_filenamev([GLib.get_user_data_dir(), 'ubuntu-rainmeter-themes']);
const escape = value => GLib.markup_escape_text(String(value ?? ''), -1);
const percent = value => Number.isFinite(value) ? `${Math.round(value)}%` : 'Unavailable';
const bytes = value => value > 1048576 ? `${(value / 1048576).toFixed(1)} MB/s` : `${((value || 0) / 1024).toFixed(1)} KB/s`;
const clockNow = () => GLib.DateTime.new_now_local();

function color(hex, alpha = 1) {
    const text = hex.replace('#', '');
    return [parseInt(text.slice(0, 2), 16) / 255, parseInt(text.slice(2, 4), 16) / 255,
        parseInt(text.slice(4, 6), 16) / 255, alpha];
}

export default class ThemeExtension extends Extension {
    enable() {
        this._reloadSource = 0;
        this._actors = [];
        this._updates = [];
        this._menus = [];
        this._menuManagers = [];
        this._sources = new Set();
        this._jobs = new Map();
        this._cache = {};
        this._frames = Array(80).fill(0);
        this._audioDrawings = [];
        this._alive = true;
        this._cancellable = new Gio.Cancellable();
        this._configFile = Gio.File.new_for_path(GLib.build_filenamev([DATA, 'active.json']));
        this._watch = this._configFile.monitor_file(Gio.FileMonitorFlags.NONE, null);
        this._watch.connect('changed', () => {
            if (this._reloadSource)
                return;
            this._reloadSource = this._later(250, () => { this._reloadSource = 0; this._load(); });
        });
        this._monitorSignal = Main.layoutManager.connect('monitors-changed', () => this._load());
        this._restackSignal = global.display.connect('restacked', () => this._visibility());
        this._workspaceSignal = global.workspace_manager.connect('active-workspace-changed', () => this._visibility());
        this._overviewSignal = Main.overview.connect('showing', () => this._visibility());
        this._overviewHideSignal = Main.overview.connect('hidden', () => this._visibility());
        this._sessionSignal = Main.sessionMode.connect('updated', () => this._visibility());
        this._load();
        this._tick = this._later(1000, () => {
            for (const update of this._updates)
                update();
            this._visibility();
        }, true);
        this._poll = this._later(3000, () => this._collect('hardware'), true);
        this._mediaPoll = this._later(2000, () => this._collect('media'), true);
        this._slowPoll = this._later(60000, () => {
            this._collect('weather'); this._collect('trash'); this._collect('headlines');
        }, true);
    }

    _later(ms, callback, repeat = false) {
        const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            if (!this._alive) { this._sources.delete(id); return GLib.SOURCE_REMOVE; }
            try { callback(); } catch (error) { console.error(`[Ubuntu Rainmeter Themes] ${error.message}`); }
            if (!repeat) this._sources.delete(id);
            return repeat ? GLib.SOURCE_CONTINUE : GLib.SOURCE_REMOVE;
        });
        this._sources.add(id);
        return id;
    }

    _read(path) {
        const [success, contents] = GLib.file_get_contents(path);
        if (!success) throw new Error('Could not read theme configuration');
        return JSON.parse(new TextDecoder().decode(contents));
    }

    _clear() {
        this._stopAudio();
        for (const menu of this._menus) { menu.close(); menu.destroy(); }
        this._menus = [];
        this._menuManagers = [];
        for (const {actor} of this._actors) { Main.layoutManager.removeChrome(actor); actor.destroy(); }
        this._actors = [];
        this._updates = [];
        this._audioDrawings = [];
    }

    _load() {
        this._clear();
        this._cache = {};
        for (const process of this._jobs.values()) { try { process.force_exit(); } catch {} }
        this._jobs.clear();
        this._generation = (this._generation || 0) + 1;
        try {
            this._config = this._read(GLib.build_filenamev([DATA, 'active.json']));
            if (this._config.engine !== 'native') return;
            const theme = this._config.native;
            if (!Array.isArray(theme.widgets)) throw new Error('Missing widget layout');
            this._theme = theme;
            for (const monitor of Main.layoutManager.monitors) {
                const scale = Math.max(.35, Math.min(monitor.width / 1920, monitor.height / 1080));
                for (const spec of theme.widgets) this._build(spec, monitor, scale);
            }
            for (const kind of ['hardware', 'media', 'weather', 'trash', 'headlines']) this._collect(kind);
            if (theme.widgets.some(widget => widget.type === 'visualizer')) this._startAudio();
            this._visibility();
        } catch (error) {
            this._clear();
            console.error(`[Ubuntu Rainmeter Themes] ${error.stack || error.message}`);
            Main.notifyError('Ubuntu Rainmeter Themes', `Widgets could not load: ${error.message}`);
        }
    }

    _collect(kind) {
        if (!this._theme || this._config?.engine !== 'native' || this._jobs.has(kind)) return;
        if (kind === 'weather' && this._config.weather === 'off') { this._cache.weather = {available: false, reason: 'Weather disabled'}; return; }
        const needs = {hardware: ['stats','menubar','volume'], media: ['media'], weather: ['weather'], trash: ['trash'], headlines: ['headlines']};
        if (!this._theme.widgets.some(widget => needs[kind]?.includes(widget.type))) return;
        const generation = this._generation;
        try {
            const process = Gio.Subprocess.new(['/usr/bin/python3', GLib.build_filenamev([DATA, 'bridge.py']), kind],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            this._jobs.set(kind, process);
            process.communicate_utf8_async(null, this._cancellable, (proc, result) => {
                if (!this._alive || generation !== this._generation) return;
                this._jobs.delete(kind);
                try {
                    const [, output] = proc.communicate_utf8_finish(result);
                    if (proc.get_successful()) this._cache[kind] = JSON.parse(output);
                    for (const update of this._updates) update();
                } catch (error) {
                    if (!this._cancellable.is_cancelled()) console.error(`[Ubuntu Rainmeter Themes] ${kind}: ${error.message}`);
                }
            });
        } catch (error) { console.error(`[Ubuntu Rainmeter Themes] ${error.message}`); }
    }

    _box(vertical = true, style = '') {
        return new St.BoxLayout({vertical, style, x_expand: true});
    }

    _label(parent, text = '', size = 20, settings = {}) {
        const label = new St.Label({text: '', x_expand: true,
            x_align: settings.align === 'left' ? Clutter.ActorAlign.START : Clutter.ActorAlign.CENTER,
            style: `font-family: "${settings.font || this._theme.font || 'Sans'}"; font-size: ${size}px; ` +
                `font-weight: ${settings.weight || 400}; color: ${settings.color || this._theme.foreground}; ` +
                `text-align: ${settings.align || 'center'}; text-shadow: 0 1px 4px rgba(0,0,0,0.65);`});
        label.clutter_text.set({use_markup: true, ellipsize: Pango.EllipsizeMode.END});
        label.clutter_text.set_markup(text);
        parent.add_child(label);
        return label;
    }

    _text(label, text) { if (label.clutter_text) label.clutter_text.set_markup(text); }

    _button(parent, label, action, scale = 1) {
        const button = new St.Button({label, reactive: true, can_focus: true,
            style: `padding: ${6 * scale}px ${10 * scale}px; color: ${this._theme.foreground}; border-radius: ${6 * scale}px;`});
        button.connect('clicked', action);
        parent.add_child(button);
        return button;
    }

    _build(spec, monitor, scale) {
        const width = spec.width * scale;
        const height = spec.height * scale;
        const actor = this._box(true, `spacing: ${(spec.gap || 6) * scale}px; padding: ${(spec.padding || 0) * scale}px; ` +
            `background-color: ${spec.background || 'transparent'}; border-radius: ${(spec.radius || 0) * scale}px; ` +
            (spec.border ? `border: ${scale}px solid ${spec.border};` : ''));
        actor.set_size(width, height);
        const x = monitor.x + spec.x * monitor.width;
        const y = monitor.y + Math.max(spec.type === 'menubar' ? Main.panel.height : 0, spec.y * monitor.height);
        actor.set_position(Math.round(x), Math.round(y));
        const interactive = ['media', 'apps', 'menubar', 'notes', 'timer', 'volume', 'trash', 'search'].includes(spec.type);
        // GNOME 50 removed affectsInputRegion; reactive child actors handle input.
        // Keep only options shared by every supported GNOME version.
        this._actors.push({actor, spec, monitor, interactive});
        Main.layoutManager.addChrome(actor, {trackFullscreen: true});
        const font = spec.font || this._theme.font;
        const label = (text, size, options = {}) => this._label(actor, text, size * scale, {color: spec.foreground || this._theme.foreground, ...options, font: options.font || font});
        const track = callback => { this._updates.push(callback); callback(); };
        switch (spec.type) {
        case 'clock': {
            const main = label('', spec.size || 80, {weight: spec.weight || 300});
            const caption = spec.caption ? label('', spec.caption_size || 22, {color: spec.muted || this._theme.muted, font: spec.caption_font || this._theme.font}) : null;
            track(() => {
                this._text(main, clockNow().format(spec.format || '%H:%M'));
                if (caption) this._text(caption, clockNow().format(spec.caption));
            });
            break;
        }
        case 'analog':
        case 'worldmap':
        case 'visualizer': {
            const drawing = new St.DrawingArea({width, height, x_expand: true, y_expand: true});
            drawing.connect('repaint', area => this._paint(area, spec, scale));
            actor.add_child(drawing);
            if (spec.type === 'visualizer') this._audioDrawings.push(drawing);
            else track(() => drawing.queue_repaint());
            break;
        }
        case 'calendar': {
            const title = label('', spec.title_size || 32, {color: this._theme.accent, font: spec.title_font || font});
            const table = label('', spec.size || 19, {font: 'monospace'});
            track(() => {
                const date = new Date();
                this._text(title, clockNow().format(spec.month_format || '%B %Y'));
                const day = date.getDate();
                const first = new Date(date.getFullYear(), date.getMonth(), 1).getDay();
                const days = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
                const cells = Array(first).fill('  ');
                for (let n = 1; n <= days; n++) cells.push(n === day ? `<span foreground="${this._theme.accent}"><b>${String(n).padStart(2)}</b></span>` : String(n).padStart(2));
                const rows = [];
                while (cells.length) rows.push(cells.splice(0, 7).join(' '));
                this._text(table, 'Su Mo Tu We Th Fr Sa\n' + rows.join('\n'));
            });
            break;
        }
        case 'weather': {
            const city = label('', spec.city_size || 17, {align: spec.align || 'center'});
            const temperature = label('', spec.size || 48);
            const conditions = label('', spec.detail_size || 17);
            const forecast = spec.forecast ? label('', spec.forecast_size || 15, {font: 'monospace'}) : null;
            track(() => {
                const weather = this._cache.weather;
                if (!weather?.available) {
                    this._text(city, 'Weather'); this._text(temperature, '—');
                    this._text(conditions, escape(weather?.reason || 'Connecting…')); return;
                }
                this._text(city, escape(weather.city));
                this._text(temperature, `${weather.icon} ${Math.round(weather.temperature_2m)}°`);
                this._text(conditions, `${escape(weather.condition)} · ${weather.relative_humidity_2m}%${weather.stale ? ' · cached' : ''}`);
                if (forecast && weather.daily?.time) {
                    const daily = weather.daily;
                    this._text(forecast, daily.time.slice(0, 5).map((date, index) =>
                        `${escape(new Date(date + 'T12:00:00').toLocaleDateString('en', {weekday: 'short'}))}   ${Math.round(daily.temperature_2m_max[index])}° / ${Math.round(daily.temperature_2m_min[index])}°`).join('\n'));
                }
            });
            label('Open-Meteo', 10, {color: this._theme.muted});
            break;
        }
        case 'stats': {
            const rows = spec.rows || ['cpu', 'ram', 'gpu'];
            const labels = rows.map(name => label('', spec.size || 18, {align: spec.align || 'left'}));
            track(() => {
                const h = this._cache.hardware || {};
                const values = {
                    cpu: ['CPU', h.cpu, percent(h.cpu)], ram: ['Memory', h.ram, h.ramgb == null ? 'Unavailable' : `${h.ramgb.toFixed(1)} GB · ${percent(h.ram)}`],
                    gpu: ['GPU', h.gpu?.use, percent(h.gpu?.use)], temperature: ['GPU TEMP', null, h.gpu?.temp == null ? 'Unavailable' : `${Math.round(h.gpu.temp)}°C`],
                    disk: ['Disk', h.disk?.percent, h.disk ? `${h.disk.used.toFixed(0)} / ${h.disk.total.toFixed(0)} GB` : 'Unavailable'],
                    network: ['Network', null, h.network ? `↓ ${bytes(h.network.down)}  ↑ ${bytes(h.network.up)}` : 'Unavailable'],
                    battery: ['Battery', h.battery, percent(h.battery)], uptime: ['Uptime', null, h.uptime == null ? 'Unavailable' : `${Math.floor(h.uptime / 3600)}h ${Math.floor(h.uptime % 3600 / 60)}m`],
                };
                rows.forEach((name, index) => {
                    const [caption, value, text] = values[name];
                    const filled = Number.isFinite(value) ? Math.round(value / 10) : 0;
                    const bar = spec.bars && Number.isFinite(value) ? `\n<span foreground="${this._theme.accent}">${'━'.repeat(filled)}</span><span foreground="${this._theme.muted}">${'─'.repeat(10 - filled)}</span>` : '';
                    this._text(labels[index], `${escape(caption)}  <b>${escape(text)}</b>${bar}`);
                });
            });
            break;
        }
        case 'media': {
            const title = label('', spec.size || 24, {weight: 600});
            const artist = label('', spec.artist_size || 16, {color: this._theme.muted});
            const progress = label('', 12, {color: this._theme.muted});
            const controls = this._box(false, 'spacing: 8px;'); actor.add_child(controls);
            this._button(controls, '⏮', () => this._mediaAction('Previous'), scale);
            const play = this._button(controls, '▶', () => this._mediaAction('PlayPause'), scale);
            this._button(controls, '⏭', () => this._mediaAction('Next'), scale);
            track(() => {
                const media = this._cache.media;
                this._text(title, escape(media?.title || 'No player is active'));
                this._text(artist, escape(media?.artist || 'Start a MPRIS-compatible player'));
                play.label = media?.status === 'Playing' ? 'Ⅱ' : '▶';
                controls.reactive = !!media?.bus;
                if (media?.duration > 0) {
                    const ratio = Math.max(0, Math.min(1, media.position / media.duration));
                    this._text(progress, `${'━'.repeat(Math.round(ratio * 24))}${'─'.repeat(24 - Math.round(ratio * 24))}`);
                } else this._text(progress, '');
            });
            break;
        }
        case 'apps': {
            if (spec.title) label(escape(spec.title), spec.title_size || 18, {align: 'left'});
            const row = this._box(spec.vertical || false, `spacing: ${8 * scale}px;`); actor.add_child(row);
            for (const id of spec.apps || ['org.gnome.Nautilus.desktop', 'org.gnome.Terminal.desktop', 'org.gnome.Settings.desktop']) {
                const app = Shell.AppSystem.get_default().lookup_app(id);
                if (!app) continue;
                const button = new St.Button({reactive: true, can_focus: true, accessible_name: app.get_name(),
                    style: `padding: ${6 * scale}px; border-radius: ${8 * scale}px;`});
                const content = this._box(true);
                content.add_child(app.create_icon_texture((spec.icon_size || 36) * scale));
                if (spec.labels) this._label(content, escape(app.get_name()), 11 * scale);
                button.set_child(content);
                button.connect('clicked', () => app.activate());
                row.add_child(button);
            }
            this._button(row, 'All apps', () => Main.overview.showApps(), scale);
            break;
        }
        case 'menubar': this._menubar(actor, scale); break;
        case 'notes': {
            label('Notes', 18, {color: spec.title_color || this._theme.accent, align: 'left'});
            const path = GLib.build_filenamev([DATA, `notes-${this._config.id}.txt`]);
            const entry = new St.Entry({hint_text: 'Write a note…', can_focus: true,
                style: `font-size: ${15 * scale}px; color: ${this._theme.foreground}; background-color: transparent;`});
            try { const [, bytes] = GLib.file_get_contents(path); entry.set_text(new TextDecoder().decode(bytes)); } catch {}
            entry.clutter_text.connect('text-changed', () => {
                try { GLib.file_set_contents(path, entry.get_text().slice(0, 20000)); } catch {}
            });
            actor.add_child(entry);
            break;
        }
        case 'timer': {
            let remaining = spec.seconds || 180;
            let end = 0;
            const counter = label('', spec.size || 28);
            const controls = this._box(false); actor.add_child(controls);
            const toggle = this._button(controls, 'Start', () => {
                if (end) { remaining = Math.max(0, end - Date.now() / 1000); end = 0; toggle.label = 'Start'; }
                else { end = Date.now() / 1000 + remaining; toggle.label = 'Pause'; }
            }, scale);
            this._button(controls, 'Reset', () => { remaining = spec.seconds || 180; end = 0; toggle.label = 'Start'; }, scale);
            track(() => {
                const value = Math.max(0, Math.ceil(end ? end - Date.now() / 1000 : remaining));
                this._text(counter, `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`);
                if (end && value === 0) { end = 0; remaining = 0; toggle.label = 'Start'; Main.notify('Ubuntu Rainmeter Themes', 'Your timer has finished.'); }
            });
            break;
        }
        case 'volume': {
            label('Speakers', 16);
            const slider = new Slider.Slider(.5); actor.add_child(slider);
            let syncing = false;
            slider.connect('notify::value', () => {
                if (!syncing) this._run(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', slider.value.toFixed(3)]);
            });
            this._button(actor, 'Mute / unmute', () => this._run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle']), scale);
            track(() => {
                const value = this._cache.hardware?.volume;
                if (Number.isFinite(value)) { syncing = true; slider.value = Math.min(1, value); syncing = false; }
            });
            break;
        }
        case 'trash': {
            const button = this._button(actor, 'Trash', () => Gio.AppInfo.launch_default_for_uri('trash:///', global.create_app_launch_context(0, -1)), scale);
            track(() => { const trash = this._cache.trash; button.label = trash ? `♻  ${trash.count ?? 0} items` : '♻  Trash'; });
            break;
        }
        case 'headlines': {
            if (spec.title) label(escape(spec.title), 16, {align: 'left'});
            const content = label('', spec.size || 16, {align: 'left'});
            content.clutter_text.line_wrap = true;
            track(() => { const news = this._cache.headlines; this._text(content, escape(news?.items?.length ? news.items.slice(0, spec.count || 4).join('\n\n') : news?.message || 'Loading headlines…')); });
            break;
        }
        case 'search': {
            const entry = new St.Entry({hint_text: 'Search the web…', can_focus: true});
            entry.clutter_text.connect('activate', () => {
                const uri = `https://duckduckgo.com/?q=${encodeURIComponent(entry.get_text())}`;
                Gio.AppInfo.launch_default_for_uri(uri, global.create_app_launch_context(0, -1));
            }); actor.add_child(entry);
            break;
        }
        }
    }

    _mediaAction(method) {
        const name = this._cache.media?.bus;
        if (!name || !['Previous', 'PlayPause', 'Next'].includes(method)) return;
        Gio.DBus.session.call(name, '/org/mpris/MediaPlayer2', 'org.mpris.MediaPlayer2.Player', method,
            null, null, Gio.DBusCallFlags.NONE, 2000, this._cancellable, (connection, result) => {
                try { connection.call_finish(result); this._collect('media'); } catch {}
            });
    }

    _run(argv) {
        try { Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE); } catch (error) { Main.notify('Ubuntu Rainmeter Themes', error.message); }
    }

    _menubar(actor, scale) {
        const row = this._box(false, `spacing: ${8 * scale}px;`); actor.add_child(row);
        this._button(row, '●', () => Main.overview.showApps(), scale);
        const appButton = this._button(row, 'Applications ▾', () => menu.toggle(), scale);
        const menu = new PopupMenu.PopupMenu(appButton, .1, St.Side.TOP);
        Main.uiGroup.add_child(menu.actor); menu.actor.hide(); this._menus.push(menu);
        const manager = new PopupMenu.PopupMenuManager(appButton);
        manager.addMenu(menu); this._menuManagers.push(manager);
        const apps = Shell.AppSystem.get_default().get_installed().filter(app => !app.get_nodisplay()).sort((a, b) => a.get_name().localeCompare(b.get_name()));
        for (const app of apps.slice(0, 200)) {
            const item = new PopupMenu.PopupMenuItem(app.get_name());
            item.connect('activate', () => app.launch([], global.create_app_launch_context(0, -1)));
            menu.addMenuItem(item);
        }
        this._button(row, 'Files', () => Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(GLib.get_home_dir(), null), global.create_app_launch_context(0, -1)), scale);
        this._button(row, 'Settings', () => Shell.AppSystem.get_default().lookup_app('org.gnome.Settings.desktop')?.activate(), scale);
        this._button(row, 'Search', () => Main.overview.show(), scale);
        const spacer = new St.Widget({x_expand: true}); row.add_child(spacer);
        const hardware = this._label(row, '', 14 * scale);
        const time = this._label(row, '', 14 * scale);
        this._updates.push(() => {
            const h = this._cache.hardware;
            this._text(hardware, h ? `CPU ${percent(h.cpu)}   RAM ${percent(h.ram)}   ${h.battery == null ? '' : `⚡ ${h.battery}%`}` : '');
            this._text(time, clockNow().format('%a %H:%M'));
        });
    }

    _paint(area, spec, scale) {
        const [width, height] = area.get_surface_size();
        const context = area.get_context();
        try {
            if (spec.type === 'visualizer') {
                const frames = this._frames;
                const gap = (spec.bar_gap || 4) * scale;
                const bar = Math.max(1, (width - gap * (frames.length - 1)) / frames.length);
                for (let index = 0; index < frames.length; index++) {
                    const value = Math.max(0, Math.min(1, frames[index] / 1000));
                    const h = Math.max(1, value * height);
                    let fill = this._theme.accent;
                    if (spec.palette?.length) fill = spec.palette[Math.floor(index / frames.length * spec.palette.length) % spec.palette.length];
                    context.setSourceRGBA(...color(fill));
                    context.rectangle(index * (bar + gap), height - h, bar, h); context.fill();
                    if (spec.peaks) {
                        const peak = Math.max(1, Math.min(1, (this._peaks?.[index] || 0) / 1000) * height);
                        context.rectangle(index * (bar + gap), height - peak, bar, Math.max(1, 2 * scale)); context.fill();
                    }
                }
            } else if (spec.type === 'analog') {
                const x = width / 2, y = height / 2, radius = Math.min(width, height) * .46;
                context.setSourceRGBA(...color(this._theme.foreground, .15)); context.arc(x, y, radius, 0, Math.PI * 2); context.fill();
                context.setSourceRGBA(...color(this._theme.foreground, .7)); context.setLineWidth(1.5 * scale); context.arc(x, y, radius, 0, Math.PI * 2); context.stroke();
                for (let index = 0; index < 60; index++) {
                    const angle = index / 60 * Math.PI * 2 - Math.PI / 2;
                    const length = index % 5 === 0 ? 8 : 3;
                    context.moveTo(x + Math.cos(angle) * (radius - length * scale), y + Math.sin(angle) * (radius - length * scale));
                    context.lineTo(x + Math.cos(angle) * (radius - 2 * scale), y + Math.sin(angle) * (radius - 2 * scale)); context.stroke();
                }
                const now = new Date();
                for (const [value, length, thickness, fill] of [
                    [(now.getHours() % 12 + now.getMinutes() / 60) / 12, .53, 4, this._theme.foreground],
                    [(now.getMinutes() + now.getSeconds() / 60) / 60, .80, 3, this._theme.foreground],
                    [now.getSeconds() / 60, .87, 1, this._theme.accent]]) {
                    const angle = value * Math.PI * 2 - Math.PI / 2;
                    context.setSourceRGBA(...color(fill)); context.setLineWidth(thickness * scale);
                    context.moveTo(x, y); context.lineTo(x + Math.cos(angle) * radius * length, y + Math.sin(angle) * radius * length); context.stroke();
                }
            } else if (spec.type === 'worldmap') {
                // Public-domain Natural Earth coastlines. Approximate day/night terminator.
                if (!this._worldMap) this._worldMap = this._read(GLib.build_filenamev([this.path, 'world-map.json']));
                const now = new Date();
                const solarLongitude = 180 - (now.getUTCHours() + now.getUTCMinutes() / 60) * 15;
                for (const ring of this._worldMap) {
                    if (!ring.length) continue;
                    context.moveTo((ring[0][0] + 180) / 360 * width, (90 - ring[0][1]) / 180 * height);
                    for (const [lon, lat] of ring.slice(1)) context.lineTo((lon + 180) / 360 * width, (90 - lat) / 180 * height);
                    context.closePath(); context.setSourceRGBA(...color(this._theme.foreground, .32)); context.fill();
                }
                context.newPath();
                for (const ring of this._worldMap) {
                    if (!ring.length) continue;
                    ring.forEach(([lon, lat], index) => {
                        const x = (lon + 180) / 360 * width, y = (90 - lat) / 180 * height;
                        if (index) context.lineTo(x, y); else context.moveTo(x, y);
                    });
                    context.closePath();
                }
                context.clip();
                for (let lon = -180; lon < 180; lon += 5) {
                    const distance = Math.abs(((lon - solarLongitude + 540) % 360) - 180);
                    if (distance > 90) {
                        context.setSourceRGBA(0, 0, 0, .3); context.rectangle((lon + 180) / 360 * width, 0, width / 72 + 1, height); context.fill();
                    }
                }
            }
        } finally { context.$dispose(); }
    }

    _startAudio() {
        this._audio = Gio.Subprocess.new(['/usr/bin/python3', GLib.build_filenamev([DATA, 'audio.py'])],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
        this._audioInput = new Gio.DataInputStream({base_stream: this._audio.get_stdout_pipe()});
        this._audioCancel = new Gio.Cancellable();
        const input = this._audioInput;
        const cancel = this._audioCancel;
        const generation = this._generation;
        const read = () => {
            if (!this._alive || cancel.is_cancelled() || generation !== this._generation) return;
            input.read_line_async(GLib.PRIORITY_DEFAULT, cancel, (stream, result) => {
                try {
                    const [line] = stream.read_line_finish_utf8(result);
                    if (line === null || !this._alive || generation !== this._generation || cancel.is_cancelled()) return;
                    if (line.startsWith('ERROR:')) { Main.notify('Audio visualizer', line.slice(6)); return; }
                    const values = line.split(';').filter(Boolean).map(Number);
                    if (values.length === 80 && values.every(Number.isFinite)) {
                        this._peaks = values.map((value, index) => Math.max(value, (this._peaks?.[index] || 0) * .94));
                        this._frames = values;
                        for (const drawing of this._audioDrawings) drawing.queue_repaint();
                    }
                    read();
                } catch (error) { if (!cancel.is_cancelled()) console.error(error); }
            });
        };
        read();
    }

    _stopAudio() {
        this._audioCancel?.cancel();
        // SIGTERM lets the Python supervisor terminate its CAVA child cleanly.
        try { this._audio?.send_signal(15); } catch {}
        this._audio = null; this._audioInput = null;
    }

    _visibility() {
        const desktop = !Main.sessionMode.isLocked && !Main.sessionMode.isGreeter && !Main.overview.visible;
        const windows = global.get_window_actors().map(actor => actor.meta_window).filter(window =>
            window && !window.minimized && window.showing_on_its_workspace() && window.get_window_type() !== Meta.WindowType.DESKTOP);
        for (const {actor, spec, interactive} of this._actors) {
            let visible = desktop;
            // Desktop widgets remain behind app windows. The menu bar may stay visible by design.
            if (visible && spec.type !== 'menubar') {
                const x = actor.x, y = actor.y, right = x + actor.width, bottom = y + actor.height;
                visible = !windows.some(window => {
                    const rect = window.get_frame_rect();
                    return rect.x < right && rect.x + rect.width > x && rect.y < bottom && rect.y + rect.height > y;
                });
            }
            actor.visible = visible;
        }
    }

    disable() {
        this._alive = false;
        this._cancellable?.cancel();
        this._watch?.cancel();
        this._watch = null;
        if (this._monitorSignal) Main.layoutManager.disconnect(this._monitorSignal);
        if (this._restackSignal) global.display.disconnect(this._restackSignal);
        if (this._workspaceSignal) global.workspace_manager.disconnect(this._workspaceSignal);
        if (this._overviewSignal) Main.overview.disconnect(this._overviewSignal);
        if (this._overviewHideSignal) Main.overview.disconnect(this._overviewHideSignal);
        if (this._sessionSignal) Main.sessionMode.disconnect(this._sessionSignal);
        for (const id of this._sources || []) GLib.source_remove(id);
        this._sources?.clear();
        for (const process of this._jobs?.values() || []) { try { process.force_exit(); } catch {} }
        this._jobs?.clear();
        this._clear();
        this._config = null; this._theme = null;
    }
}
