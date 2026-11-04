#!/usr/bin/python3
"""Stream CAVA spectrum frames from system playback. Audio is never recorded."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile


def main():
    if not shutil.which('cava'):
        print('ERROR: Install cava for live audio visualizers', flush=True)
        return 1
    with tempfile.TemporaryDirectory(prefix='urt-cava-') as folder:
        config = Path(folder) / 'config'
        config.write_text('''[general]
framerate = 30
bars = 80
autosens = 1
[input]
method = pulse
source = auto
[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 1000
bar_delimiter = 59
frame_delimiter = 10
[smoothing]
noise_reduction = 75
''')
        # cava opens the default Pulse/PipeWire output monitor, not a microphone.
        child = subprocess.Popen(['cava', '-p', str(config)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 text=True, start_new_session=True)
        def stop(*_):
            if child.poll() is None:
                child.terminate()
            raise SystemExit(0)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        try:
            for line in child.stdout:
                print(line.strip(), flush=True)
        except BrokenPipeError:
            pass
        finally:
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        return child.returncode or 0


if __name__ == '__main__':
    sys.exit(main())
