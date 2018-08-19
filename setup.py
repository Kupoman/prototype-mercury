import os
import sys
import subprocess
from setuptools import setup


SETUP_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(SETUP_DIR, 'game', 'blenderpanda'))
#pylint:disable=wrong-import-position
import pman


try:
    from direct.showutil.dist import build_apps
    class CustomBuildApps(build_apps):
        def finalize_options(self):
            # Create requirements.txt file from Pipfile
            reqs = subprocess.check_output(['pipenv', 'lock', '--requirements']).decode('utf8')

            # Swap input-overhaul wheel for deploy-ng
            reqs = list(filter(lambda x: 'panda3d' not in x, reqs.split('\n')))
            reqs += [
                '--extra-index-url https://archive.panda3d.org/branches/deploy-ng',
                'panda3d',
            ]

            reqspath = os.path.join(self.build_base, 'requirements.txt')
            with open(reqspath, 'w')  as rfile:
                rfile.write('\n'.join(reqs))
            #pylint:disable=attribute-defined-outside-init
            self.requirements_path = reqspath

            super().finalize_options()

        def run(self):
            # Run pman build
            pman.build()

            # Run regular build_apps
            super().run()

            # Do any post-build fixing/cleanup
            for platform in self.platforms:
                build_dir = os.path.join(self.build_base, platform)

                # Remove some CEF files
                locales_dir = os.path.join(build_dir, 'locales')
                for i in os.listdir(locales_dir):
                    if i != 'en-US.pak':
                        os.remove(os.path.join(locales_dir, i))
                os.remove(os.path.join(build_dir, 'devtools_resources.pak'))
                os.remove(os.path.join(build_dir, 'cef_extensions.pak'))
                os.remove(os.path.join(build_dir, 'snapshot_blob.bin'))
except ImportError:
    class CustomBuildApps():
        pass


setup(
    name='mercury',
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
    cmdclass={
        'build_apps': CustomBuildApps,
    },
    options={
        'build_apps': {
            'include_patterns': [
                'game/**',
                '.pman',
            ],
            'rename_paths': {
                'game/': './',
            },
            'exclude_patterns': [
                '*.py',
                'game/config/user.prc',
                'game/saves/**',
            ],
            'gui_apps': {
                'mercury': 'game/main.py',
            },
            'log_filename': '$USER_APPDATA/mercury/mercury.log',
            'plugins': [
                'pandagl',
                'p3openal_audio',
            ],
            'include_modules': {
                '*': [
                    'configparser',
                    'gamestates.*.*',
                    'blenderpanda.*.*',
                ],
            },
            'exclude_modules': {
                '*': [
                    'cefpython3.cefpython_py27',
                    'cefpython3.cefpython_py34',
                    'cefpython3.cefpython_py35',
                ],
            },
            'platforms': [
                'manylinux1_x86_64',
                'win_amd64',
            ],
        }
    },
)
