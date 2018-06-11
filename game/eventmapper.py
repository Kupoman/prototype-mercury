import pprint

from direct.showbase.DirectObject import DirectObject
from direct.directnotify.DirectNotify import DirectNotify
from direct.showbase.MessengerGlobal import messenger
import panda3d.core as p3d


class EventMapper(DirectObject):
    notify = DirectNotify().newCategory("EventMapper")
    event_map_item_prefix = "event-map-item-"

    def __init__(self):
        super().__init__()

        self.gamepad_label_map = {
            'rshoulder': 'RB',
            'rtrigger': 'RT',
            'lshoulder': 'LB',
            'ltrigger': 'LT',
        }
        self.gamepad_label_map_dualshock = {
            'rshoulder': 'R1',
            'rtrigger': 'R2',
            'lshoulder': 'L1',
            'ltrigger': 'L2',
            'x': '□',
            'y': '△',
            'a': '×',
            'b': '○',
        }

        # Setup input map
        self.input_map = {}
        self.reload_config()

    def clear_aliases(self):
        self.input_map = {}
        self.ignoreAll()

    def add_alias(self, input_event, output_event):
        if input_event not in self.input_map:
            self.input_map[input_event] = []

        self.input_map[input_event].append(output_event)

    def reload_config(self):
        cvmgr = p3d.ConfigVariableManager.get_global_ptr()

        # Remove previous mappings
        self.clear_aliases()

        # Build mappings from ConfigVariables
        for cvar in cvmgr.variables:
            if cvar.name.startswith(self.event_map_item_prefix):
                cvar = p3d.ConfigVariableString(cvar.name, '')
                outevent = cvar.name.replace(self.event_map_item_prefix, '')

                for i in range(cvar.get_num_words()):
                    inevent = cvar.get_word(i)

                    if inevent == outevent:
                        # Prevent circular reference
                        self.notify.warning(
                            "skipping circular reference mapping {} to {}".format(
                                inevent, outevent
                            )
                        )
                        continue

                    self.add_alias(inevent, outevent)

        self.notify.info("Loaded Event Map\n{}".format(pprint.pformat(self.input_map)))

        # Listen for events
        for trigger, events in self.input_map.items():
            self.accept(trigger, self.send, [events, ''])
            self.accept(trigger + '-up', self.send, [events, '-up'])
            self.accept(trigger + '-repeat', self.send, [events, '-repeat'])

    def send(self, events, suffix):
        for i in events:
            self.notify.debug("throwing {}".format(i+suffix))
            messenger.send(i + suffix)

    def get_inputs_for_event(self, event):
        return [key for key, value in self.input_map.items() if event in value]

    def _get_mapped_gamepad_label(self, gamepad_device, inp):
        if not inp.startswith('gamepad') or gamepad_device is None:
            return ''

        # remove gamepadN prefix
        label = '-'.join(inp.split('-')[1:])

        prefer_ds_labels = 'playstation' in gamepad_device.name.lower()

        if label.startswith('action'):
            label = label.replace('action_', '')
            if prefer_ds_labels:
                label = self.gamepad_label_map_dualshock.get(label, label.upper())
            else:
                label = self.gamepad_label_map.get(label, label.upper())
            return label

        return ''

    def get_labels_for_event(self, event, default=None):
        inputs = self.get_inputs_for_event(event)
        keymap = base.win.get_keyboard_map() if 'base' in globals() else None

        gamepad_device = None
        if hasattr(p3d, 'InputDeviceManager'):
            devicemgr = p3d.InputDeviceManager.get_global_ptr()
            devices = devicemgr.get_devices(p3d.InputDevice.DC_gamepad)

            gpidx = [
                int(i.split('-')[0].replace('gamepad', ''))
                for i in inputs
                if i.startswith('gamepad')
            ]
            gamepad_device = devices[gpidx[0]] if gpidx and gpidx[0] < len(devices) else None

        if default is not None:
            inputs.append(default)
        inputs = filter(
            lambda x: x.startswith('gamepad') == bool(gamepad_device is not None),
            inputs
        )


        retval = []
        for inp in inputs:
            inp = inp.replace('raw-', '')
            retval.append(next(filter(None, [
                self._get_mapped_gamepad_label(gamepad_device, inp),
                keymap.get_mapped_button_label(inp) if keymap is not None else '',
                inp
            ])))
        return retval


def _test():
    p3d.load_prc_file_data(
        '',
        'notify-level-EventMapper info\n'
        'event-map-item-jump space raw-y\n'
        'event-map-item-p1-move-left j\n'
        'event-map-item-p1-move-right k\n'
        'event-map-item-p1-ability0 a\n'
        'event-map-item-p1-ability2 s\n'
        'event-map-item-p1-ability3 d\n'
        'event-map-item-p1-ability4 f\n'
    )

    emapper = EventMapper()

    print("Inputs for jump", emapper.get_inputs_for_event('jump'))
    print("Labels for jump", emapper.get_labels_for_event('jump'))

if __name__ == '__main__':
    _test()
