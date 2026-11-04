import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from test_theme_manager import manager, ROOT


class NativeManifestTests(unittest.TestCase):
    def test_all_bundled_assets_match_checksums_and_have_previews(self):
        themes = list((ROOT / 'themes').glob('*/theme.json'))
        self.assertEqual(len(themes), 11)
        layouts = set()
        for path in themes:
            theme = manager.load_theme(path.parent.name)
            image = path.parent / theme['wallpaper']['file']
            self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), theme['wallpaper']['sha256'])
            self.assertTrue((path.parent / 'preview.png').is_file())
            if theme.get('engine') == 'native':
                layouts.add(json.dumps(theme['native'], sort_keys=True))
        self.assertEqual(len(layouts), 10)

    def test_native_manifest_rejects_unsafe_types_and_coordinates(self):
        base = manager.load_theme('monterey')['native']
        for key, value in [('type', 'shell'), ('x', float('nan')), ('y', 2), ('width', -1)]:
            native = copy.deepcopy(base)
            native['widgets'][0][key] = value
            with self.assertRaises(ValueError):
                manager.validate_native(native)

    def test_audio_themes_have_real_spectrum_modules(self):
        for name in ('monstercat', 'fountain-of-colors'):
            widgets = manager.load_theme(name)['native']['widgets']
            self.assertTrue(any(w['type'] == 'visualizer' for w in widgets))

    @unittest.skipUnless(os.environ.get('GSETTINGS_BACKEND') == 'memory', 'Requires in-memory settings')
    def test_native_switch_and_uninstall_keep_original_backup(self):
        from gi.repository import Gio
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data, legacy = root / 'managed', root / 'missing-legacy'
            background = Gio.Settings.new('org.gnome.desktop.background')
            shell = Gio.Settings.new('org.gnome.shell')
            background.set_string('picture-uri', 'file:///original.jpg')
            background.set_string('picture-uri-dark', 'file:///original-dark.jpg')
            shell.set_strv('enabled-extensions', ['other-extension'])
            args = argparse.Namespace(theme='monterey', install_deps=False, dry_run=False,
                auto_location=False, city=None, wallpaper=None, rss_url=None)
            def external(command, **kwargs):
                self.assertIn(command[0], ('gnome-extensions', 'dconf'))
                return subprocess.CompletedProcess(command, 0, '', '')
            with patch.object(manager, 'paths', return_value=(data, legacy)), \
                 patch.object(manager, 'data_home', return_value=root), \
                 patch.object(manager, 'preflight', return_value='50'), \
                 patch.object(manager, 'monitor_count', return_value=3), \
                 patch.object(manager.shutil, 'which', return_value='/usr/bin/fixture'), \
                 patch.object(manager.subprocess, 'check_output', return_value=''), \
                 patch.object(manager.subprocess, 'run', side_effect=external):
                manager.install(args)
                backup = (data / 'backup.json').read_bytes()
                args.theme = 'big-sur'
                manager.install(args)
                self.assertEqual((data / 'backup.json').read_bytes(), backup)
                self.assertEqual(json.loads((data / 'active.json').read_text())['id'], 'big-sur')
                self.assertIn(manager.NATIVE_UUID, shell.get_strv('enabled-extensions'))
                manager.uninstall(args)
            self.assertEqual(background.get_string('picture-uri'), 'file:///original.jpg')
            self.assertEqual(background.get_string('picture-uri-dark'), 'file:///original-dark.jpg')
            self.assertEqual(shell.get_strv('enabled-extensions'), ['other-extension'])
            self.assertFalse((data / 'active.json').exists())
