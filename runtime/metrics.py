#!/usr/bin/python3
"""Small cached collectors for the Desktop Widgets command-label element."""
import fcntl
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

DATA = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'ubuntu-rainmeter-themes'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'ubuntu-rainmeter-themes'


def get_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'UbuntuRainmeterThemes/1.0'})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read(2_000_000))


def cached(name, age, build, stale_limit=86400):
    """Share readings across monitors; back off after offline/API failures."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (name + '.json')
    with (CACHE / (name + '.lock')).open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            old = json.loads(path.read_text())
        except (OSError, ValueError):
            old = {}
        now = time.time()
        if now - old.get('checked', 0) < age:
            if 'data' in old and now - old.get('success', 0) < stale_limit:
                return old['data'], old.get('stale', False)
            raise RuntimeError('Temporarily unavailable')
        try:
            data = build()
            path.write_text(json.dumps({'checked': now, 'success': now, 'data': data}))
            return data, False
        except Exception:
            old.update(checked=now, stale=True)
            path.write_text(json.dumps(old))
            if 'data' in old and now - old.get('success', 0) < stale_limit:
                return old['data'], True
            raise


def cpu_sample():
    values = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    return sum(values), values[3] + values[4]


def read_gpu():
    if shutil.which('nvidia-smi'):
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total',
                '--format=csv,noheader,nounits',
            ], capture_output=True, text=True, timeout=3, check=True)
            values = []
            for part in result.stdout.splitlines()[0].split(','):
                try:
                    value = float(part.strip())
                    values.append(value if math.isfinite(value) else None)
                except ValueError:
                    values.append(None)
            return dict(zip(('use', 'temp', 'used', 'total'), values))
        except (OSError, subprocess.SubprocessError, IndexError):
            pass
    # AMD exposes utilization and VRAM through sysfs. Never require root.
    for device in sorted(Path('/sys/class/drm').glob('card[0-9]*/device')):
        busy = device / 'gpu_busy_percent'
        if busy.exists():
            try:
                result = {'use': float(busy.read_text()), 'temp': None, 'used': None, 'total': None}
                for key, filename in [('used', 'mem_info_vram_used'), ('total', 'mem_info_vram_total')]:
                    path = device / filename
                    if path.exists():
                        result[key] = int(path.read_text()) / 1048576
                temps = sorted(device.glob('hwmon/hwmon*/temp1_input'))
                if temps:
                    result['temp'] = int(temps[0].read_text()) / 1000
                return result
            except (OSError, ValueError):
                pass
    return {}  # Intel/unsupported GPUs: explicitly show unavailable, never invent values.


def stats():
    total, idle = cpu_sample()
    path = CACHE / 'cpu-sample.json'
    try:
        previous = json.loads(path.read_text())
    except (OSError, ValueError):
        previous = None
    if not previous or total <= previous[0] or idle < previous[1]:
        previous = [total, idle]
        time.sleep(0.15)
        total, idle = cpu_sample()
    delta = total - previous[0]
    cpu = 100 * (1 - (idle - previous[1]) / delta) if delta else 0
    path.write_text(json.dumps([total, idle]))
    memory = {line.split(':')[0]: int(line.split()[1])
              for line in Path('/proc/meminfo').read_text().splitlines() if len(line.split()) > 1}
    used = memory['MemTotal'] - memory['MemAvailable']
    return {'cpu': max(0, min(100, cpu)), 'ramgb': used / 1048576,
            'ram': 100 * used / memory['MemTotal'], 'gpu': read_gpu()}


def weather(config):
    mode = config.get('weather', 'off')
    if mode == 'auto':
        def locate():
            data = get_json('https://ipwho.is/')
            if not data.get('success') or 'latitude' not in data:
                raise RuntimeError('Location lookup failed')
            # Persist only approximate city/coordinates, not the IP response.
            return {key: data[key] for key in ('city', 'latitude', 'longitude')}
        location, _ = cached('location', 3600, locate, stale_limit=86400)
    elif mode == 'city':
        def locate_city():
            query = urllib.parse.urlencode({'name': config['city'], 'count': 1, 'language': 'en'})
            matches = get_json('https://geocoding-api.open-meteo.com/v1/search?' + query).get('results', [])
            if not matches:
                raise RuntimeError('City not found')
            item = matches[0]
            return {'city': item['name'], 'latitude': item['latitude'], 'longitude': item['longitude']}
        import hashlib
        city_key = hashlib.sha256(config['city'].encode()).hexdigest()[:12]
        location, _ = cached('city-location-' + city_key, 86400, locate_city)
    else:
        raise RuntimeError('Weather is disabled')
    query = urllib.parse.urlencode({
        'latitude': location['latitude'], 'longitude': location['longitude'],
        'current': 'temperature_2m,weather_code,relative_humidity_2m', 'timezone': 'auto',
    })
    data = get_json('https://api.open-meteo.com/v1/forecast?' + query)['current']
    data['city'] = location['city']
    return data


def conditions(code):
    if code == 0:
        return '☀', 'Clear'
    if code <= 3:
        return '☁', 'Cloudy'
    if code in (45, 48):
        return '≋', 'Fog'
    if code in (71, 73, 75, 77, 85, 86):
        return '❄', 'Snow'
    if code >= 95:
        return 'ϟ', 'Thunderstorms'
    if code in (80, 81, 82):
        return '☂', 'Showers'
    return '☂', 'Rain'


def row(label, value, suffix, color):
    return (f'<span foreground="{color}" size="24000">◉</span>  '
            f'<span size="12000">{label}</span>  <span size="16000">{value}{suffix}</span>')


def render_stats(data, config):
    color, muted = config['accent'], config['muted']
    lines = [row('CPU', round(data['cpu']), '%', color), row('RAM', f'{data["ramgb"]:.1f}', ' GB', color)]
    gpu = data['gpu']
    if gpu.get('use') is not None:
        lines.append(row('GPU', round(gpu['use']), '%', color))
    else:
        lines.append(f'<span foreground="{muted}" size="11000">GPU usage unavailable</span>')
    if gpu.get('temp') is not None:
        lines.append(row('GPU TEMP', round(gpu['temp']), '°C', color))
    if gpu.get('used') is not None and gpu.get('total') is not None:
        lines.append(f'<span foreground="{muted}" size="10000">VRAM  {gpu["used"]/1024:.1f} / {gpu["total"]/1024:.1f} GB</span>')
    return '\n'.join(lines)


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else 'stats'
    try:
        config = json.loads((DATA / 'active.json').read_text())
        if kind == 'weather':
            # Weather mode/city is part of the cache key, so switching city cannot show the old city.
            import hashlib
            token = hashlib.sha256(json.dumps([config.get('weather'), config.get('city')]).encode()).hexdigest()[:12]
            data, stale = cached('weather-' + token, 900, lambda: weather(config), stale_limit=21600)
            icon, description = conditions(data['weather_code'])
            stale_text = ' · cached' if stale else ''
            print(f'<span size="30000">{icon}  {round(data["temperature_2m"])}°C</span>\n'
                  f'<span size="12000">{description} · {html.escape(data["city"])}</span>\n'
                  f'<span foreground="{config["muted"]}" size="9000">Humidity {data["relative_humidity_2m"]}% · Open-Meteo{stale_text}</span>')
        else:
            data, _ = cached('stats', 2, stats, stale_limit=15)
            print(render_stats(data, config))
    except Exception:
        print('Weather temporarily unavailable' if kind == 'weather' else 'Statistics temporarily unavailable')


if __name__ == '__main__':
    main()
