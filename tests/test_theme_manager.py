import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

manager = module('manager', ROOT / 'scripts/theme_manager.py')
metrics = module('metrics', ROOT / 'runtime/metrics.py')


class ManagerTests(unittest.TestCase):
    def test_theme_name_cannot_escape_theme_directory(self):
        for name in ('../private', '/tmp', 'solo-leveling/../../x', 'bad name'):
            with self.assertRaises(ValueError):
                manager.load_theme(name)

    def test_layout_is_unique_on_three_monitors_and_can_disable_weather(self):
        theme = manager.load_theme('solo-leveling')
        plan = manager.layout(theme, 3, '/home/a user/metrics.py', 'off')
        self.assertEqual(len({w['id'] for w in plan}), 6)
        self.assertEqual({w['monitor'] for w in plan}, {0, 1, 2})
        self.assertTrue(all(e[0] != 'weather' for w in plan for e in w['elements']))
        enabled = manager.layout(theme, 3, '/home/a user/metrics.py', 'auto')
        self.assertEqual(sum(e[0] == 'weather' for w in enabled for e in w['elements']), 3)

    def test_bad_download_never_replaces_existing_file(self):
        class Response(io.BytesIO):
            def geturl(self):
                return 'https://example.com/art.jpg'
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'art.jpg'
            target.write_bytes(b'original')
            with patch.object(manager.urllib.request, 'urlopen', return_value=Response(b'bad')):
                with self.assertRaises(ValueError):
                    manager.checked_download('https://example.com/art.jpg', target, hashlib.sha256(b'good').hexdigest())
            self.assertEqual(target.read_bytes(), b'original')
            self.assertEqual([p.name for p in Path(folder).iterdir()], ['art.jpg'])

    def test_zip_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as zipped:
                zipped.writestr('../escape', 'bad')
            with self.assertRaises(ValueError):
                manager.extract_extension(archive, Path(folder) / 'extension')
            self.assertFalse((Path(folder) / 'escape').exists())

    def test_weather_snow_showers_are_not_thunderstorms(self):
        self.assertEqual(metrics.conditions(85), ('❄', 'Snow'))
        self.assertEqual(metrics.conditions(95), ('ϟ', 'Thunderstorms'))

    def test_failed_fetch_is_cached_and_marked_stale(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(metrics, 'CACHE', Path(folder)):
            with patch.object(metrics.time, 'time', return_value=100):
                self.assertEqual(metrics.cached('weather', 10, lambda: {'temp': 20}), ({'temp': 20}, False))
            def fail():
                raise OSError('offline')
            with patch.object(metrics.time, 'time', return_value=120):
                self.assertEqual(metrics.cached('weather', 10, fail), ({'temp': 20}, True))
            with patch.object(metrics.time, 'time', return_value=125):
                self.assertEqual(metrics.cached('weather', 10, lambda: self.fail('Must back off')), ({'temp': 20}, True))

    def test_missing_gpu_does_not_fake_zero_usage(self):
        result = metrics.render_stats({'cpu': 10, 'ramgb': 3.2, 'gpu': {}}, {'accent': '#dd554d', 'muted': '#acb8c5'})
        self.assertIn('GPU usage unavailable', result)
        self.assertNotIn('GPU TEMP', result)


@unittest.skipUnless(os.environ.get('URT_TEST_EXTENSION'), 'set URT_TEST_EXTENSION for isolated schema integration test')
class SchemaIntegrationTests(unittest.TestCase):
    def test_reapply_preserves_existing_widgets_without_duplicates(self):
        self.assertEqual(os.environ.get('GSETTINGS_BACKEND'), 'memory', 'Never test against real desktop settings')
        from gi.repository import GLib
        settings = manager.get_settings(Path(os.environ['URT_TEST_EXTENSION']))
        original = {'user-widget': GLib.Variant('a{sv}', {'enabled': GLib.Variant('b', True)})}
        settings().set_value('widgets', GLib.Variant('aa{sv}', [original]))
        theme = manager.load_theme('solo-leveling')
        for count in (3, 3, 1):
            manager.apply_layout(settings, theme, manager.layout(theme, count, Path('/home/a user/metrics.py'), 'auto'))
            widgets = settings().get_value('widgets').unpack()
            ids = [key for item in widgets for key in item]
            self.assertIn('user-widget', ids)
            self.assertEqual(len(ids), 1 + 2 * count)
            self.assertEqual(len(ids), len(set(ids)))
        # Emulate uninstall's list removal, preserving the original untouched entry.
        self.assertEqual(manager.non_theme_entries(settings().get_value('widgets')), [original])
        import gi
        gi.require_version('Pango', '1.0')
        from gi.repository import Pango
        for spec in manager.layout(theme, 1, Path('/home/a user/metrics.py'), 'auto'):
            for _, kind, fmt, _ in spec['elements']:
                if kind == 0:
                    Pango.parse_markup(GLib.DateTime.new_now_local().format(fmt), -1, '\0')
        command = settings(manager.SCHEMA + '.element-data', manager.SETTINGS_PATH + 'widget-data/urt-solo-leveling-clock-0/element-data/weather/').get_string('command')
        self.assertIn("'/home/a user/metrics.py'", command)


    def test_install_and_uninstall_restore_wallpaper_and_keep_user_widgets(self):
        self.assertEqual(os.environ.get('GSETTINGS_BACKEND'), 'memory')
        import argparse
        import shutil
        import subprocess
        from gi.repository import Gio, GLib
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'managed'
            extension = Path(folder) / 'extension'
            shutil.copytree(Path(os.environ['URT_TEST_EXTENSION']) / 'schemas', extension / 'schemas')
            (extension / 'metadata.json').write_text(json.dumps({'shell-version': ['50']}))
            settings = manager.get_settings(extension)
            settings().set_value('widgets', GLib.Variant('aa{sv}', [manager.enabled_entry('user-existing')]))
            background = Gio.Settings.new('org.gnome.desktop.background')
            background.set_string('picture-uri', 'file:///previous-light.jpg')
            background.set_string('picture-uri-dark', 'file:///previous-dark.jpg')
            shell = Gio.Settings.new('org.gnome.shell')
            shell.set_strv('enabled-extensions', ['other-extension'])
            args = argparse.Namespace(theme='solo-leveling', install_deps=False, dry_run=False, auto_location=True, city=None)
            def download(url, destination, checksum):
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b'fixture wallpaper')
            def no_external_mutations(command, **kwargs):
                self.assertIn(command[0], ('gnome-extensions', 'dconf'))
                return subprocess.CompletedProcess(command, 1 if command[0] == 'gnome-extensions' else 0, '', '')
            with patch.object(manager, 'paths', return_value=(data, extension)), \
                 patch.object(manager, 'preflight', return_value='50'), \
                 patch.object(manager, 'monitor_count', return_value=3), \
                 patch.object(manager, 'checked_download', side_effect=download), \
                 patch.object(manager.subprocess, 'check_output', return_value=''), \
                 patch.object(manager.subprocess, 'run', side_effect=no_external_mutations):
                manager.install(args)
                manager.install(args)
                self.assertEqual(len(settings().get_value('widgets').unpack()), 7)
                manager.uninstall(args)
            self.assertEqual(background.get_string('picture-uri'), 'file:///previous-light.jpg')
            self.assertEqual(background.get_string('picture-uri-dark'), 'file:///previous-dark.jpg')
            self.assertEqual(list(settings().get_value('widgets').unpack()[0]), ['user-existing'])
            self.assertIn('other-extension', shell.get_strv('enabled-extensions'))
            self.assertFalse((data / 'active.json').exists())


if __name__ == '__main__':
    unittest.main()
