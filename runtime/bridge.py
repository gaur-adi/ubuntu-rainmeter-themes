#!/usr/bin/python3
"""Local JSON bridge. Never runs shell strings or uploads hardware/media data."""
import calendar
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import metrics


def hardware():
    data, stale = metrics.cached('stats', 2, metrics.stats, stale_limit=15)
    data = dict(data)
    disk = shutil.disk_usage(Path.home())
    data['disk'] = {'used': disk.used / 1073741824, 'total': disk.total / 1073741824,
                    'percent': 100 * disk.used / disk.total}
    data['uptime'] = float(Path('/proc/uptime').read_text().split()[0])
    batteries = list(Path('/sys/class/power_supply').glob('BAT*/capacity'))
    data['battery'] = int(batteries[0].read_text()) if batteries else None
    network = [line.split(':', 1) for line in Path('/proc/net/dev').read_text().splitlines()[2:] if ':' in line]
    rx = sum(int(values.split()[0]) for name, values in network if name.strip() != 'lo')
    tx = sum(int(values.split()[8]) for name, values in network if name.strip() != 'lo')
    now = time.monotonic()
    def rates():
        path = metrics.CACHE / 'network-sample.json'
        try:
            before = json.loads(path.read_text())
        except (OSError, ValueError):
            before = [now, rx, tx]
        path.write_text(json.dumps([now, rx, tx]))
        dt = max(0.1, now - before[0])
        return {'down': max(0, rx - before[1]) / dt, 'up': max(0, tx - before[2]) / dt}
    data['network'], _ = metrics.cached('network', 2, rates, stale_limit=15)
    # Current hottest readable CPU/package sensor. Missing sensors remain null.
    temperatures = []
    for hwmon in Path('/sys/class/hwmon').glob('hwmon*'):
        try:
            if hwmon.joinpath('name').read_text().strip() in ('coretemp', 'k10temp', 'zenpower', 'acpitz'):
                temperatures.extend(float(path.read_text()) / 1000 for path in hwmon.glob('temp*_input'))
        except (OSError, ValueError):
            pass
    data['cpu_temperature'] = max(temperatures) if temperatures else None
    try:
        output = subprocess.check_output(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'], text=True, timeout=2)
        data['volume'] = float(output.split()[1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        data['volume'] = None
    data['stale'] = stale
    return data


def media():
    from gi.repository import Gio, GLib
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    names = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
        'ListNames', None, GLib.VariantType.new('(as)'), 0, 1000, None).unpack()[0]
    players = []
    for name in names:
        if not name.startswith('org.mpris.MediaPlayer2.'):
            continue
        try:
            values = bus.call_sync(name, '/org/mpris/MediaPlayer2', 'org.freedesktop.DBus.Properties',
                'GetAll', GLib.Variant('(s)', ('org.mpris.MediaPlayer2.Player',)), None, 0, 1000, None).unpack()[0]
            meta = values.get('Metadata', {})
            if isinstance(meta, GLib.Variant):
                meta = meta.unpack()
            players.append({'bus': name, 'title': str(meta.get('xesam:title', 'Unknown track')),
                'artist': ', '.join(meta.get('xesam:artist', [])), 'album': str(meta.get('xesam:album', '')),
                'art': str(meta.get('mpris:artUrl', '')), 'status': values.get('PlaybackStatus', 'Stopped'),
                'position': values.get('Position', 0), 'duration': meta.get('mpris:length', 0),
                'can_control': bool(values.get('CanControl', False))})
        except Exception:
            continue
    players.sort(key=lambda p: p['status'] != 'Playing')
    return players[0] if players else {'status': 'Stopped', 'title': 'No player is active', 'artist': '', 'bus': None}


def weather(config):
    if config.get('weather') == 'off':
        return {'available': False, 'reason': 'Weather is disabled'}
    import hashlib
    key = hashlib.sha256(json.dumps([config.get('weather'), config.get('city')]).encode()).hexdigest()[:12]
    def fetch():
        basic = metrics.weather(config)
        # Reuse the approximate location, or configured geocoding cache, for daily forecasts.
        if config['weather'] == 'auto':
            location = json.loads((metrics.CACHE / 'location.json').read_text())['data']
        else:
            city_key = hashlib.sha256(config['city'].encode()).hexdigest()[:12]
            location = json.loads((metrics.CACHE / ('city-location-' + city_key + '.json')).read_text())['data']
        query = metrics.urllib.parse.urlencode({'latitude': location['latitude'], 'longitude': location['longitude'],
            'daily': 'weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset',
            'forecast_days': 5, 'timezone': 'auto'})
        try:
            basic['daily'] = metrics.get_json('https://api.open-meteo.com/v1/forecast?' + query)['daily']
        except Exception:
            basic['daily'] = {}
        return basic
    data, stale = metrics.cached('forecast-' + key, 900, fetch, stale_limit=21600)
    data = dict(data, available=True, stale=stale)
    data['icon'], data['condition'] = metrics.conditions(data['weather_code'])
    return data


def trash():
    from gi.repository import Gio
    root = Gio.File.new_for_uri('trash:///')
    enum = root.enumerate_children('standard::name,standard::size', Gio.FileQueryInfoFlags.NONE, None)
    count, size = 0, 0
    try:
        while item := enum.next_file(None):
            count += 1
            size += item.get_size()
    finally:
        enum.close(None)
    return {'count': count, 'megabytes': size / 1048576}


def headlines(config):
    url = config.get('rss_url')
    if not url:
        return {'items': [], 'message': 'Add --rss-url to display headlines'}
    if not url.startswith('https://'):
        raise ValueError('RSS feeds must use HTTPS')
    def fetch():
        request = urllib.request.Request(url, headers={'User-Agent': 'UbuntuRainmeterThemes/1.0'})
        with urllib.request.urlopen(request, timeout=8) as response:
            if not response.geturl().startswith('https://'):
                raise ValueError('Insecure feed redirect')
            document = ET.fromstring(response.read(1_000_000))
        items = []
        for node in list(document.findall('.//item')) + list(document.findall('{http://www.w3.org/2005/Atom}entry')):
            title = node.findtext('title') or node.findtext('{http://www.w3.org/2005/Atom}title') or ''
            if title:
                items.append(title[:150])
        return {'items': items[:5]}
    import hashlib
    return metrics.cached('rss-' + hashlib.sha256(url.encode()).hexdigest()[:12], 1800, fetch, stale_limit=86400)[0]


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else 'hardware'
    config = json.loads((metrics.DATA / 'active.json').read_text())
    try:
        value = {'hardware': hardware, 'media': media, 'weather': lambda: weather(config),
                 'trash': trash, 'headlines': lambda: headlines(config)}[kind]()
        print(json.dumps(value, allow_nan=False))
    except Exception as error:
        print(json.dumps({'available': False, 'error': type(error).__name__}))


if __name__ == '__main__':
    main()
