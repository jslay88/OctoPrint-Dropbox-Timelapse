import os
import shutil

import yaml
from octoprint.settings import _default_basedir, _APPNAME


base_dir = _default_basedir(_APPNAME)
config_path = os.path.join(base_dir, 'config.yaml')
if not os.path.isfile(os.path.join(base_dir, 'config.yaml')):
    os.makedirs(base_dir)
    shutil.copyfile('/octoprint_dropbox_timelapse/octoprint-config.yaml',
                    os.path.join(base_dir, 'config.yaml'))

settings = yaml.load(open(os.path.join(base_dir, 'config.yaml')), Loader=yaml.FullLoader)

# Dont override 'devel' if it already exists
if 'devel' not in settings:
    settings['devel'] = {
        'virtualPrinter': {
            'enabled': True
        }
    }
# Dont override 'virtualPrinter' if it already exists
elif 'virtualPrinter' not in settings['devel']:
    settings['devel']['virtualPrinter'] = {
        'enabled': True
    }
# Set enabled to True if it isn't set or set to False
elif 'enabled' not in settings['devel']['virtualPrinter'] or \
        not settings['devel']['virtualPrinter']['enabled']:
    settings['virtualPrinter']['enabled'] = True

# Set autoconnect to VIRTUAL
settings['serial'] = {
        'autoconnect': True,
        'baudrate': 0,
        'port': 'VIRTUAL'
}

# Write the file out
with open(os.path.join(base_dir, 'config.yaml'), 'w') as f:
    f.write(yaml.dump(settings))

# Copy test GCode, fake timelapse plugin, and test movie
if not os.path.isdir(os.path.join(base_dir, 'uploads')):
    os.makedirs(os.path.join(base_dir, 'uploads'))
if not os.path.isdir(os.path.join(base_dir, 'plugins')):
    os.makedirs(os.path.join(base_dir, 'plugins'))
shutil.copyfile('/octoprint_dropbox_timelapse/tests/cube.gcode',
                os.path.join(base_dir, 'uploads', 'cube.gcode'))
shutil.copyfile('/octoprint_dropbox_timelapse/tests/fake_timelapse_plugin.py',
                os.path.join(base_dir, 'plugins', 'fake_timelapse_plugin.py'))
shutil.copyfile('/octoprint_dropbox_timelapse/tests/test.mp4',
                os.path.join(base_dir, 'plugins', 'test.mp4'))
