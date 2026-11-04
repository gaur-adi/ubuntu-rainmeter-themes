#!/usr/bin/python3
"""Install data-driven themes into GNOME Desktop Widgets, with reversible settings."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UUID = 'azclock@azclock.gitlab.com'
NATIVE_UUID = 'ubuntu-rainmeter-themes@gaur-adi'
SCHEMA = 'org.gnome.shell.extensions.azclock'
SETTINGS_PATH = '/org/gnome/shell/extensions/azclock/'
PREFIX = 'urt-'
EXTENSION_URL = 'https://extensions.gnome.org/download-extension/azclock%40azclock.gitlab.com.shell-extension.zip?version_tag=75151'
EXTENSION_SHA = '79b0e9fcd4d11fb86985dd64eef4d4f6310698a6c37646507812bc3e2eb5b603'
PACKAGES = ['python3-gi', 'dconf-cli', 'gnome-shell-extension-prefs', 'fonts-lato',
            'gir1.2-gweather-4.0', 'gir1.2-nm-1.0', 'gir1.2-soup-3.0', 'gir1.2-rsvg-2.0',
            'gir1.2-adw-1', 'gir1.2-gtk-4.0']


def data_home():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))


def paths():
    data = data_home() / 'ubuntu-rainmeter-themes'
    return data, data_home() / 'gnome-shell/extensions' / UUID


def validate_theme(theme):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', theme['id']):
        raise ValueError('Invalid theme id')
    for key in ('accent', 'muted', 'foreground'):
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', theme[key]):
            raise ValueError('Theme colors must be six-digit hex values')
    for key in ('clock_position', 'stats_position'):
        position = theme[key]
        if len(position) != 2 or any(not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in position):
            raise ValueError('Positions must be two normalized coordinates')
    image = theme['wallpaper']
    if image.get('mode') != 'preserve' and (not re.fullmatch('[0-9a-f]{64}', image['sha256']) or
            (image.get('mode') != 'bundled' and not image['url'].startswith('https://'))):
        raise ValueError('Wallpaper requires an HTTPS URL and SHA-256 checksum')
    if not isinstance(theme['font'], str) or not theme['font'].strip():
        raise ValueError('Theme must specify a font')
    if theme.get('engine') == 'native':
        validate_native(theme['native'])
    return theme


ALLOWED_WIDGETS = {'panel', 'clock', 'analog', 'worldmap', 'calendar', 'weather', 'stats', 'media', 'apps',
                   'menubar', 'notes', 'timer', 'volume', 'trash', 'headlines', 'search', 'visualizer'}


def validate_native(native):
    widgets = native.get('widgets')
    if not isinstance(widgets, list) or not 1 <= len(widgets) <= 40:
        raise ValueError('Native themes need between 1 and 40 widgets')
    for widget in widgets:
        if widget.get('type') not in ALLOWED_WIDGETS:
            raise ValueError('Unknown native widget type')
        for name in ('x', 'y'):
            value = widget.get(name)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('Native positions must be normalized coordinates')
        for name in ('width', 'height'):
            value = widget.get(name)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not 1 <= value <= 4000:
                raise ValueError('Invalid native widget dimensions')
        if widget.get('type') == 'stats' and any(row not in {'cpu', 'ram', 'gpu', 'temperature', 'disk', 'network', 'battery', 'uptime'} for row in widget.get('rows', [])):
            raise ValueError('Unknown hardware statistic')
    return native


def load_theme(name):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
        raise ValueError('Use a theme folder name such as solo-leveling')
    path = ROOT / 'themes' / name / 'theme.json'
    if not path.is_file():
        raise ValueError(f'Unknown theme: {name}. Run ./install.sh --list')
    theme = validate_theme(json.loads(path.read_text()))
    if theme['id'] != name:
        raise ValueError('Theme id must match its folder name')
    return theme


def checked_download(url, destination, expected, max_bytes=40_000_000):
    destination = Path(destination)
    if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() == expected:
        return
    request = urllib.request.Request(url, headers={'User-Agent': 'UbuntuRainmeterThemes/1.0'})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp:
        pending = Path(temp.name)
        try:
            digest, size = hashlib.sha256(), 0
            with urllib.request.urlopen(request, timeout=30) as response:
                if not response.geturl().startswith('https://'):
                    raise ValueError('Refusing an insecure redirect')
                while chunk := response.read(65536):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError('Download exceeds size limit')
                    digest.update(chunk)
                    temp.write(chunk)
            temp.close()
            if digest.hexdigest() != expected:
                raise ValueError('Download checksum changed. No desktop settings were modified.')
            pending.replace(destination)
        finally:
            pending.unlink(missing_ok=True)


def extract_extension(archive, target):
    with zipfile.ZipFile(archive) as zipped:
        if sum(info.file_size for info in zipped.infolist()) > 50_000_000:
            raise ValueError('Extension archive is too large')
        for info in zipped.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename:
                raise ValueError('Unsafe extension archive path')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Extension archive contains a symbolic link')
        zipped.extractall(target)


def dependencies(install=False):
    missing = any(not shutil.which(cmd) for cmd in ('gnome-shell', 'gnome-extensions', 'dconf'))
    try:
        import gi
        for namespace, version in [('GWeather', '4.0'), ('NM', '1.0'), ('Soup', '3.0'), ('Rsvg', '2.0'), ('Adw', '1'), ('Gtk', '4.0')]:
            gi.require_version(namespace, version)
        from gi.repository import Gio, GLib  # noqa: F401
    except (ImportError, ValueError):
        missing = True
    if missing:
        if os.environ.get('URT_DEPS_REEXEC') == '1':
            raise RuntimeError('Required desktop dependencies remain unavailable after package installation. Check your Ubuntu/GNOME installation.')
        command = ['sudo', 'apt-get', 'install', '-y', *PACKAGES]
        if not install:
            raise RuntimeError('Missing Ubuntu dependencies. Run with --install-deps, or:\n' + shlex.join(command))
        subprocess.run(['sudo', 'apt-get', 'update'], check=True)
        subprocess.run(command, check=True)
        # The parent Python may have cached missing typelib lookups. Re-exec cleanly.
        os.execve('/usr/bin/python3', ['/usr/bin/python3', __file__, *sys.argv[1:]], {**os.environ, 'URT_DEPS_REEXEC': '1'})


def preflight(install_deps=False):
    if os.geteuid() == 0:
        raise RuntimeError('Run as your normal desktop user, not with sudo.')
    if not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        raise RuntimeError('Run in a Terminal inside your Ubuntu GNOME desktop session.')
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    if 'gnome' not in desktop:
        raise RuntimeError('This installer supports GNOME (Ubuntu desktop), not KDE/XFCE.')
    dependencies(install_deps)
    output = subprocess.check_output(['gnome-shell', '--version'], text=True)
    match = re.search(r'(\d+)\.', output)
    if not match:
        raise RuntimeError('Could not determine GNOME Shell version')
    version = match.group(1)
    if version not in {'45', '46', '47', '48', '49', '50', '51'}:
        raise RuntimeError(f'GNOME {version} is not supported by the pinned extension release.')
    return version


def get_settings(extension):
    from gi.repository import Gio
    source = Gio.SettingsSchemaSource.new_from_directory(str(extension / 'schemas'), Gio.SettingsSchemaSource.get_default(), False)
    def settings(schema=SCHEMA, path=SETTINGS_PATH):
        definition = source.lookup(schema, False)
        if definition is None:
            raise RuntimeError('Installed Desktop Widgets extension has an incompatible schema')
        return Gio.Settings.new_full(definition, None, path)
    return settings


def monitor_count():
    from gi.repository import Gio
    proxy = Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SESSION, 0, None, 'org.gnome.Mutter.DisplayConfig',
        '/org/gnome/Mutter/DisplayConfig', 'org.gnome.Mutter.DisplayConfig', None)
    return max(1, len(proxy.call_sync('GetCurrentState', None, 0, 10000, None).unpack()[2]))


def layout(theme, count, runtime, weather_mode):
    """Return a declarative layout. Pure Python, no settings mutation."""
    widgets = []
    for monitor in range(count):
        for kind in ('clock', 'stats'):
            wid = f'{PREFIX}{theme["id"]}-{kind}-{monitor}'
            if kind == 'clock':
                accent = theme['accent']
                elements = [
                    ('day', 0, '<span letter_spacing="6000">%^A</span>', 36),
                    ('date', 0, '<span letter_spacing="1000">%d %^B, %Y</span>', 13),
                    ('time', 0, f'%I<span foreground="{accent}">│</span>%M<span foreground="{accent}">│</span><span size="28000">%S</span><span size="12000"> %p</span>', 58),
                ]
                if weather_mode != 'off':
                    elements.append(('weather', 3, '', 18))
            else:
                elements = [('stats', 3, '', 18)]
            widgets.append({'id': wid, 'monitor': monitor, 'kind': kind,
                'position': theme[kind + '_position'], 'elements': elements,
                'runtime': str(runtime)})
    return widgets


def is_theme_widget(name):
    """Include IDs reserved by the original pre-repository Solo setup."""
    return name.startswith(PREFIX) or re.fullmatch(r'solo-(?:clock|stats)-[0-9]+', name) is not None


def non_theme_entries(raw):
    """Keep original GVariant values intact rather than unpacking/repacking variants."""
    entries = []
    for index in range(raw.n_children()):
        child = raw.get_child_value(index)
        entry = {}
        for item in range(child.n_children()):
            pair = child.get_child_value(item)
            name = pair.get_child_value(0).get_string()
            if not is_theme_widget(name):
                entry[name] = pair.get_child_value(1).get_variant()
        if entry:
            entries.append(entry)
    return entries


def enabled_entry(name):
    from gi.repository import GLib
    return {name: GLib.Variant('a{sv}', {'enabled': GLib.Variant('b', True)})}


def apply_layout(settings, theme, widgets):
    from gi.repository import GLib
    main = settings()
    entries = non_theme_entries(main.get_value('widgets'))
    for spec in widgets:
        path = SETTINGS_PATH + 'widget-data/' + spec['id'] + '/'
        widget = settings(SCHEMA + '.widget-data', path)
        widget.set_string('name', f'{theme["name"]} {spec["kind"]} — Display {spec["monitor"] + 1}')
        widget.set_enum('anchor-point', 5 if spec['kind'] == 'clock' else 0)
        widget.set_boolean('convert-old-location-done', True)
        widget.set_string('location-data', json.dumps({'monitorIndex': spec['monitor'],
            'relativeX': spec['position'][0], 'relativeY': spec['position'][1]}))
        widget.set_value('padding', GLib.Variant('(iiii)', (0, 0, 0, 0)))
        widget.set_int('spacing', 8)
        widget.set_boolean('lock-widget', True)
        widget.set_boolean('show-background', False)
        elements = []
        for name, kind, fmt, size in spec['elements']:
            element = settings(SCHEMA + '.element-data', path + 'element-data/' + name + '/')
            element.set_string('name', name.title())
            element.set_enum('element-type', kind)
            element.set_value('font-family-override', GLib.Variant('(bs)', (True, theme['font'])))
            element.set_int('font-size', size)
            element.set_int('font-weight', 400)
            element.set_string('foreground-color', theme['foreground'])
            element.set_value('shadow', GLib.Variant('(bsiiii)', (True, 'rgba(0,0,0,0.7)', 0, 1, 0, 3)))
            if kind == 0:
                element.set_string('date-format', fmt)
            else:
                element.set_string('command', shlex.join(['/usr/bin/python3', spec['runtime'], name]))
                element.set_int('polling-interval', 60000 if name == 'weather' else 3000)
            elements.append(enabled_entry(name))
        widget.set_value('elements', GLib.Variant('aa{sv}', elements))
        entries.append(enabled_entry(spec['id']))
    main.set_boolean('create-initial-widget', False)
    main.set_value('widgets', GLib.Variant('aa{sv}', entries))


def write_json(path, data):
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(data, indent=2) + '\n')
    pending.replace(path)


def install(args):
    theme = load_theme(args.theme)
    if theme.get('engine') == 'native':
        return install_native(args, theme)
    version = preflight(args.install_deps and not args.dry_run)
    data, extension = paths()
    count = monitor_count()
    weather_mode = 'auto' if args.auto_location else 'city' if args.city else 'off'
    if args.dry_run:
        print(json.dumps({'theme': theme['id'], 'gnome': version, 'displays': count,
            'weather': weather_mode, 'wallpaper': theme['wallpaper'].get('url', theme['wallpaper'].get('mode')),
            'widgets': layout(theme, count, data / 'metrics.py', weather_mode)}, indent=2))
        return
    data.mkdir(parents=True, exist_ok=True)
    image = choose_wallpaper(theme, data, getattr(args, 'wallpaper', None))
    if image is None:
        raise ValueError('Desktop Widgets themes require a wallpaper')
    if not extension.exists():
        archive = data / 'desktop-widgets-v21.zip'
        checked_download(EXTENSION_URL, archive, EXTENSION_SHA, max_bytes=8_000_000)
        extension.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=extension.parent) as temp:
            staged = Path(temp) / UUID
            staged.mkdir()
            extract_extension(archive, staged)
            metadata = json.loads((staged / 'metadata.json').read_text())
            if metadata['uuid'] != UUID or version not in metadata['shell-version']:
                raise RuntimeError('Downloaded extension does not support this GNOME version')
            subprocess.run(['glib-compile-schemas', '--strict', str(staged / 'schemas')], check=True)
            staged.rename(extension)
    metadata = json.loads((extension / 'metadata.json').read_text())
    if version not in metadata.get('shell-version', []):
        raise RuntimeError('Your existing Desktop Widgets version does not support this GNOME version. Update it first.')
    settings = get_settings(extension)
    from gi.repository import Gio
    background = Gio.Settings.new('org.gnome.desktop.background')
    shell = Gio.Settings.new('org.gnome.shell')
    backup = data / 'backup.json'
    old_wallpaper = {key: background.get_string(key) for key in ('picture-uri', 'picture-uri-dark', 'picture-options')}
    old_tree = subprocess.check_output(['dconf', 'dump', SETTINGS_PATH], text=True)
    old_enabled = shell.get_strv('enabled-extensions')
    previous_active = (data / 'active.json').read_bytes() if (data / 'active.json').exists() else None
    if not backup.exists():
        write_json(backup, {'wallpaper': old_wallpaper, 'extension_enabled': UUID in shell.get_strv('enabled-extensions'),
            'initial_widget': settings().get_boolean('create-initial-widget')})
        (data / 'before-install.dconf').write_text(old_tree)
    try:
        shutil.copy2(ROOT / 'runtime/metrics.py', data / 'metrics.py')
        config = {key: theme[key] for key in ('id', 'accent', 'muted', 'foreground')}
        config.update(weather=weather_mode, city=args.city, wallpaper_uri=image.as_uri(), engine='desktop-widgets')
        write_json(data / 'active.json', config)
        apply_layout(settings, theme, layout(theme, count, data / 'metrics.py', weather_mode))
        for key in ('picture-uri', 'picture-uri-dark'):
            background.set_string(key, image.as_uri())
        background.set_string('picture-options', 'zoom')
        enabled = [value for value in shell.get_strv('enabled-extensions') if value != NATIVE_UUID]
        if UUID not in enabled:
            shell.set_strv('enabled-extensions', [*enabled, UUID])
        else:
            shell.set_strv('enabled-extensions', enabled)
        Gio.Settings.sync()
    except Exception:
        subprocess.run(['dconf', 'reset', '-f', SETTINGS_PATH], check=True)
        subprocess.run(['dconf', 'load', SETTINGS_PATH], input=old_tree, text=True, check=True)
        for key, value in old_wallpaper.items():
            background.set_string(key, value)
        shell.set_strv('enabled-extensions', old_enabled)
        if previous_active is None:
            (data / 'active.json').unlink(missing_ok=True)
        else:
            (data / 'active.json').write_bytes(previous_active)
        Gio.Settings.sync()
        raise
    subprocess.run(['gnome-extensions', 'enable', UUID], capture_output=True, text=True)
    info = subprocess.run(['gnome-extensions', 'info', UUID], capture_output=True, text=True, env={**os.environ, 'LC_ALL': 'C'})
    print(f'Applied {theme["name"]} for {count} display(s).')
    if shell.get_boolean('disable-user-extensions'):
        print('User extensions are globally disabled. Enable them in the Extensions app to show the widgets.')
    elif info.returncode != 0 or 'ACTIVE' not in info.stdout:
        print('Log out and sign in again once to load the new extension. Do not restart GNOME Shell on Wayland.')
    else:
        print('Desktop Widgets is active. The layout should update immediately.')
    if weather_mode == 'off':
        print('Weather is off. Add --auto-location or --city "City name" to enable it.')
    print('Undo with: ./uninstall.sh')


def choose_wallpaper(theme, data, override=None):
    if override:
        source = Path(override).expanduser().resolve()
        if not source.is_file() or source.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.svg'}:
            raise ValueError('--wallpaper must point to a local supported image')
        target = data / 'wallpapers' / (theme['id'] + '-custom' + source.suffix.lower())
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target
    image = theme['wallpaper']
    if image.get('mode') == 'preserve':
        return None
    if image.get('mode') == 'bundled':
        source = (ROOT / 'themes' / theme['id'] / image['file']).resolve()
        source.relative_to((ROOT / 'themes' / theme['id']).resolve())
        if hashlib.sha256(source.read_bytes()).hexdigest() != image['sha256']:
            raise ValueError('Bundled wallpaper checksum mismatch')
        target = data / 'wallpapers' / (theme['id'] + source.suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target
    target = data / 'wallpapers' / (theme['id'] + '.jpg')
    checked_download(image['url'], target, image['sha256'])
    return target


def install_native(args, theme):
    version = preflight(args.install_deps and not args.dry_run)
    metadata = json.loads((ROOT / 'native' / NATIVE_UUID / 'metadata.json').read_text())
    if version not in metadata['shell-version']:
        raise RuntimeError(f'The native launcher/audio engine currently targets GNOME {metadata["shell-version"]}. Your version is {version}. Solo Leveling still uses Desktop Widgets.')
    count = monitor_count()
    if args.dry_run:
        print(json.dumps({'theme': theme['id'], 'engine': 'native', 'gnome': version, 'displays': count,
            'wallpaper': theme['wallpaper'], 'widgets': theme['native']['widgets']}, indent=2))
        return
    audio = any(widget['type'] == 'visualizer' for widget in theme['native']['widgets'])
    missing = [name for name in (['cava', 'pactl'] if audio else []) if not shutil.which(name)]
    if any(widget['type'] == 'volume' for widget in theme['native']['widgets']) and not shutil.which('wpctl'):
        missing.append('wpctl')
    if missing:
        packages = (['cava', 'pulseaudio-utils'] if audio else []) + (['wireplumber'] if 'wpctl' in missing else [])
        command = ['sudo', 'apt-get', 'install', '-y', *packages]
        if not args.install_deps:
            raise RuntimeError('Missing native widget tools: ' + ', '.join(missing) + '. Run with --install-deps, or:\n' + shlex.join(command))
        subprocess.run(command, check=True)
    from gi.repository import Gio, GLib
    data, legacy = paths()
    data.mkdir(parents=True, exist_ok=True)
    image = choose_wallpaper(theme, data, getattr(args, 'wallpaper', None))
    background = Gio.Settings.new('org.gnome.desktop.background')
    shell = Gio.Settings.new('org.gnome.shell')
    original_enabled = shell.get_strv('enabled-extensions')
    native_path = data_home() / 'gnome-shell/extensions' / NATIVE_UUID
    native_path.parent.mkdir(parents=True, exist_ok=True)
    backup = data / 'backup.json'
    old_wallpaper = {key: background.get_string(key) for key in ('picture-uri', 'picture-uri-dark', 'picture-options')}
    old_tree = subprocess.check_output(['dconf', 'dump', SETTINGS_PATH], text=True)
    old_active = (data / 'active.json').read_bytes() if (data / 'active.json').exists() else None
    if not backup.exists():
        initial = get_settings(legacy)().get_boolean('create-initial-widget') if legacy.exists() else True
        write_json(backup, {'wallpaper': old_wallpaper, 'extension_enabled': UUID in original_enabled,
            'native_enabled': NATIVE_UUID in original_enabled, 'initial_widget': initial})
        (data / 'before-install.dconf').write_text(old_tree)
    try:
        shutil.copytree(ROOT / 'native' / NATIVE_UUID, native_path, dirs_exist_ok=True)
        for script in ('metrics.py', 'bridge.py', 'audio.py'):
            shutil.copy2(ROOT / 'runtime' / script, data / script)
        config = {key: theme[key] for key in ('id', 'accent', 'muted', 'foreground')}
        config.update(engine='native', native=theme['native'],
            weather='auto' if args.auto_location else 'city' if args.city else 'off', city=args.city,
            wallpaper_uri=image.as_uri() if image else None,
            rss_url=getattr(args, 'rss_url', None) or theme.get('rss_url'))
        if legacy.exists():
            main = get_settings(legacy)()
            main.set_value('widgets', GLib.Variant('aa{sv}', non_theme_entries(main.get_value('widgets'))))
        # Load fonts only from theme-declared, checksum-pinned HTTPS sources.
        font_dir = data_home() / 'fonts/ubuntu-rainmeter-themes'
        for font in theme.get('fonts', []):
            if not re.fullmatch(r'[A-Za-z0-9_.-]+\.(?:otf|ttf)', font['file']):
                raise ValueError('Invalid font filename')
            checked_download(font['url'], font_dir / font['file'], font['sha256'], max_bytes=8_000_000)
        if theme.get('fonts') and shutil.which('fc-cache'):
            subprocess.run(['fc-cache', '-f', str(font_dir)], check=True)
        write_json(data / 'active.json', config)
        if image:
            for key in ('picture-uri', 'picture-uri-dark'):
                background.set_string(key, image.as_uri())
            background.set_string('picture-options', 'zoom')
        if NATIVE_UUID not in original_enabled:
            shell.set_strv('enabled-extensions', [*original_enabled, NATIVE_UUID])
        Gio.Settings.sync()
    except Exception:
        subprocess.run(['dconf', 'reset', '-f', SETTINGS_PATH], check=True)
        subprocess.run(['dconf', 'load', SETTINGS_PATH], input=old_tree, text=True, check=True)
        for key, value in old_wallpaper.items():
            background.set_string(key, value)
        shell.set_strv('enabled-extensions', original_enabled)
        if old_active is None:
            (data / 'active.json').unlink(missing_ok=True)
        else:
            (data / 'active.json').write_bytes(old_active)
        Gio.Settings.sync()
        raise
    subprocess.run(['gnome-extensions', 'enable', NATIVE_UUID], capture_output=True, text=True)
    print(f'Applied {theme["name"]} using native GNOME widgets on {count} display(s).')
    print('First native-engine installation or code update: log out and sign in again. Later theme switches reload live.')
    if image is None:
        print('This component keeps your wallpaper. Use --wallpaper /path/to/image.jpg to select a background.')
    print('Undo with: ./uninstall.sh')


def uninstall(args):
    preflight(False)
    data, extension = paths()
    backup = data / 'backup.json'
    if not backup.exists():
        print('No managed installation found. Nothing changed.')
        return
    if args.dry_run:
        print('Would remove managed widgets and restore the previous wallpaper if still selected.')
        return
    from gi.repository import Gio, GLib
    saved = json.loads(backup.read_text())
    owned, entries = [], []
    if extension.exists():
        settings = get_settings(extension)
        main = settings()
        raw = main.get_value('widgets')
        owned = [key for entry in raw.unpack() for key in entry if is_theme_widget(key)]
        entries = non_theme_entries(raw)
        main.set_value('widgets', GLib.Variant('aa{sv}', entries))
        main.set_boolean('create-initial-widget', saved['initial_widget'])
    active = json.loads((data / 'active.json').read_text()) if (data / 'active.json').exists() else {}
    background = Gio.Settings.new('org.gnome.desktop.background')
    restored = False
    for key in ('picture-uri', 'picture-uri-dark'):
        if background.get_string(key) == active.get('wallpaper_uri'):
            background.set_string(key, saved['wallpaper'][key])
            restored = True
    if restored and background.get_string('picture-options') == 'zoom':
        background.set_string('picture-options', saved['wallpaper']['picture-options'])
    # Leave the shared extension enabled if the user now has other widgets.
    if not saved['extension_enabled'] and not entries:
        shell = Gio.Settings.new('org.gnome.shell')
        shell.set_strv('enabled-extensions', [x for x in shell.get_strv('enabled-extensions') if x != UUID])
    if not saved.get('native_enabled', False):
        shell = Gio.Settings.new('org.gnome.shell')
        shell.set_strv('enabled-extensions', [x for x in shell.get_strv('enabled-extensions') if x != NATIVE_UUID])
    Gio.Settings.sync()
    for wid in owned:
        subprocess.run(['dconf', 'reset', '-f', SETTINGS_PATH + 'widget-data/' + wid + '/'], check=True)
    # Keep the last backup for manual recovery. Only remove managed runtime after detaching widgets.
    shutil.copy2(backup, data / 'last-uninstall-backup.json')
    backup.unlink()
    (data / 'active.json').unlink(missing_ok=True)
    for script in ('metrics.py', 'bridge.py', 'audio.py'):
        (data / script).unlink(missing_ok=True)
    print('Theme removed. Other widgets and extensions were preserved. Shared extension and downloaded artwork remain installed.')


def main():
    parser = argparse.ArgumentParser(description='Rainmeter-style themes for Ubuntu GNOME')
    parser.add_argument('theme', nargs='?', help='theme folder name, e.g. solo-leveling')
    parser.add_argument('--list', action='store_true', help='list available themes')
    parser.add_argument('--dry-run', action='store_true', help='inspect plan without downloads or desktop changes')
    parser.add_argument('--install-deps', action='store_true', help='install missing Ubuntu packages using sudo apt')
    parser.add_argument('--wallpaper', help='use your own local wallpaper image')
    parser.add_argument('--rss-url', help='HTTPS RSS/Atom feed for news widgets')
    parser.add_argument('--uninstall', action='store_true', help='remove managed widgets and restore wallpaper')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--auto-location', action='store_true', help='use IP-based approximate city for weather')
    group.add_argument('--city', help='weather city, e.g. "Agra"')
    args = parser.parse_args()
    try:
        if args.list:
            for file in sorted((ROOT / 'themes').glob('*/theme.json')):
                theme = validate_theme(json.loads(file.read_text()))
                print(f'{theme["id"]:24} {theme["name"]}')
        elif args.uninstall:
            uninstall(args)
        elif not args.theme:
            parser.print_help()
        else:
            install(args)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
