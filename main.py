import os
import sys

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d
import cefpanda
import pman.shim
import eventmapper
import simplepbr

from game import gamedb
from game import gamestates
from game import pathutils
from game.playerdata import PlayerData
from game.monster import Monster


# Load config files before ShowBase is initialized
p3d.load_prc_file(p3d.Filename(pathutils.CONFIG_DIR, 'game.prc'))
p3d.load_prc_file(p3d.Filename(pathutils.CONFIG_DIR, 'inputs.prc'))
p3d.load_prc_file(p3d.Filename(pathutils.USER_CONFIG_DIR, 'user.prc'))
p3d.load_prc_file(p3d.Filename(pathutils.CONFIG_DIR, 'user.prc'))


class GameApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        pman.shim.init(self)
        gamedb.get_instance()

        # Render pipeline
        self.render.set_antialias(p3d.AntialiasAttrib.MAuto)
        simplepbr.init(
            msaa_samples=p3d.ConfigVariableInt('msaa-samples', 4).get_value(),
            enable_shadows=p3d.ConfigVariableBool('enable-shadows', True).get_value(),
            exposure=6,
        )

        # Controls
        self.event_mapper = eventmapper.EventMapper()
        self.disable_mouse()
        self.accept('quit', sys.exit)
        self.accept('toggle-buffer-viewer', self.bufferViewer.toggleEnable)
        self.accept('toggle-oobe', self.oobe)
        self.accept('save-screenshot', self.screenshot)

        # Global storage
        self.blackboard = {
            'player': PlayerData(),
        }
        default_monster = Monster.make_new('player_monster', 'Default', 'bobcatshark')
        self.blackboard['player'].monsters = [default_monster]

        # UI
        self.ui = cefpanda.CEFPanda()
        self.ui.use_mouse = False

        # Game states
        initial_state = p3d.ConfigVariableString('mercury-initial-state', 'Title').get_value()
        self.gman = gamestates.StateManager(initial_state)
        def update_state(task):
            self.gman.update()
            return task.cont
        self.taskMgr.add(update_state, 'GameState Update')

    def change_state(self, next_state):
        self.gman.change(next_state)

    def change_to_previous_state(self):
        self.gman.change_to_previous()

    def load_ui(self, uiname):
        self.ui.load_file(os.path.join(pathutils.APP_ROOT_DIR, 'ui', '{}.html'.format(uiname)))


def main():
    app = GameApp()
    app.run()

if __name__ == '__main__':
    if '--dumpdb' in sys.argv:
        print(gamedb.get_instance().to_json())
    else:
        main()
