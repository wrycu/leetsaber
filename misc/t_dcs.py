from bs4 import BeautifulSoup as bs
from flask import render_template
from PIL import Image, ImageDraw, ImageFont
import os
import io
import base64
import dcs as pydcs
from pathlib import Path
import glob


class ControlMapper:
    def __init__(self):
        self.controllers = {
            'X52': X52(),
        }

    @staticmethod
    def draw_text(the_draw, x, y, size, message):
        font = ImageFont.truetype(
            os.path.join(os.getcwd(), 'app', 'flask_app', 'static', 'font', 'lucon.ttf'),
            size=12,
        )
        color = 'rgb(0, 0, 0)'  # black color
        while len(message) > size:
            position = message[0:size].rfind(' ')
            the_draw.text((x, y), message[0:position], fill=color, font=font)
            message = message[position + 1:]
            # next line should be 15 pixels down
            y += 15
        # draw the message on the image
        the_draw.text((x, y), message, fill=color, font=font)
        return the_draw

    def render_controls(self, controls):
        soup = bs(controls, 'html.parser')

        try:
            title = soup.find('title').next
        except Exception:
            raise Exception("Invalid/malformed file format")
        # detect controller and validate we support it
        controller = None
        for a_controller in self.controllers.keys():
            if a_controller in title:
                controller = self.controllers[a_controller]
        if not controller:
            raise Exception(
                "Unknown controller: {}. Supported controllers: {}".format(title, ','.join(self.controllers.keys()))
            )

        file_path = os.path.join(os.getcwd(), 'app', 'flask_app', 'static', 'img')
        stick_image = Image.open(os.path.join(file_path, 'x52_stick.png'))
        throttle_image = Image.open(os.path.join(file_path, 'x52_throttle.png'))
        # initialise the drawing context with
        # the image object as background
        draw = {
            'stick': ImageDraw.Draw(stick_image),
            'throttle': ImageDraw.Draw(throttle_image),
        }

        table = bs.find(soup, 'table')
        switches = []
        # iterate over possible controls
        for row in table.find_all('tr'):
            columns = row.find_all('td')
            control_a = columns[0].text.replace('"', '').strip()
            # iterate over each bind for the control
            for control in control_a.split('; '):
                # look for a switch
                if not control or control in controller.ignore_mapping:
                    continue
                switched = False
                if control.find(' - ') > 0:
                    switch = control.split(' - ')[0]
                    (x, y, size, hotas) = controller.lookup_position(switch, False)
                    self.draw_text(draw[hotas], x, y, size, '(SWITCH)')
                    control = control.split(' - ')[1]
                    switches.append(switch)
                    switched = True
                try:
                    (x, y, size, hotas) = controller.lookup_position(control, switched)
                except Exception as e:
                    print("unknown control - {} - {}".format(control, e))
                    continue
                try:
                    the_draw = draw[hotas]
                except KeyError:
                    print("unknown stick type")
                    continue
                message = columns[1].text.replace('"', '').strip()
                self.draw_text(the_draw, x, y, size, message)

        # return the edited images (these are never written to disk)
        stick_output = io.BytesIO()
        throttle_output = io.BytesIO()
        io.BytesIO(stick_image.save(stick_output, format='png', compress_level=9))
        io.BytesIO(throttle_image.save(throttle_output, format='png', compress_level=9))

        stick_output.seek(0)
        return render_template(
            'dcs/{}.html'.format(controller.name),
            joystick=base64.b64encode(stick_output.getvalue()).decode('utf-8'),
            throttle=base64.b64encode(throttle_output.getvalue()).decode('utf-8'),
        )


class X52:
    def __init__(self, switch_key=None):
        """
        Mapping of buttons to actual buttons

        Stick
            Fire                JOY_BTN2        530, 135        530, 205
            Fire A              JOY_BTN3        1350, 114       1350, 183
            Fire B              JOY_BTN4        1350, 295       1350, 364
            Fire C              JOY_BTN5        530, 363        530, 433
            POV Hat 1           --------
                Up              JOY_BTN_POV1_U  75, 355         333, 355
                Down            JOY_BTN_POV1_D  75, 495         333, 495
                Left            JOY_BTN_POV1_L  5, 423          263, 423
                Right           JOY_BTN_POV1_R  140, 423        396, 423
            POV Hat 2           ---------
                Up              JOY_BTN16       75, 122         333, 122
                Down            JOY_BTN18       75, 262         333, 262
                Left            JOY_BTN19       5, 190          263, 190
                Right           JOY_BTN17       140, 190        396, 190
            Trigger             JOY_BTN1        1350, 474       1350, 542
            Second Trigger      JOY_BTN15       1620, 474       1620, 542
            Toggle 1            JOY_BTN9        103, 622        103, 774
            Toggle 2            JOY_BTN10       103, 692        103, 844
            Toggle 3            JOY_BTN11       230, 622        230, 774
            Toggle 4            JOY_BTN12       230, 692        230, 844
            Toggle 5            JOY_BTN13       358, 622        358, 774
            Toggle 6            JOY_BTN14       358, 692        358, 844
            Pinkie Switch       JOY_BTN6
            Mode 1              JOY_BTN24       1620, 107
            Mode 2              JOY_BTN25       1620. 174
            Mode 3              JOY_BTN26       1620, 244
        Throttle
            Fire D              JOY_BTN7        1365, 1180      1597, 1180
            Fire E              JOY_BTN8        1365, 968       1597, 968
            Rotary 1
                Clockwise
                C-Clockwise
            Rotary 2
                Clockwise
                C-Clockwise
            POV Hat 3
                Up              JOY_BTN20       78, 940         332, 940
                Down            JOY_BTN22       78, 1081        332, 1081
                Left            JOY_BTN23       7, 1011         267, 1011
                Right           JOY_BTN21       142, 1013       400, 1013
            Ministick
            Throttle Base 1     JOY_BTN27       5, 1500         5, 1582
            Throttle Base 2     JOY_BTN28       130, 1500       130, 1582
            Throttle Base 3     JOY_BTN29       258, 1500       2556, 1582
            Precision Slider
            Clutch Fixed
        """
        self.name = 'x52'
        self.controller_type = 'hotas'
        self.ignore_mapping = {
            'JOY_Z',
            'JOY_Y',
            'JOY_X',
            'JOY_RZ',
            'JOY_RY',
            'JOY_RX',
        }
        self.switches = []

        self.switch_key = ''  # 'JOY_BTN6 - '

        self.control_mapping = {
            # Joystick
            'JOY_BTN2': 'fire',
            self.switch_key + 'JOY_BTN2': 'fire_s',
            'JOY_BTN3': 'fire_a',
            self.switch_key + 'JOY_BTN3': 'fire_a_s',
            'JOY_BTN4': 'fire_b',
            self.switch_key + 'JOY_BTN4': 'fire_b_s',
            'JOY_BTN5': 'fire_c',
            self.switch_key + 'JOY_BTN5': 'fire_c_s',
            'JOY_BTN_POV1_U': 'pov_1_up',
            'JOY_BTN_POV1_D': 'pov_1_down',
            'JOY_BTN_POV1_L': 'pov_1_left',
            'JOY_BTN_POV1_R': 'pov_1_right',
            self.switch_key + 'JOY_BTN_POV1_U': 'pov_1_s_up',
            self.switch_key + 'JOY_BTN_POV1_D': 'pov_1_s_down',
            self.switch_key + 'JOY_BTN_POV1_L': 'pov_1_s_left',
            self.switch_key + 'JOY_BTN_POV1_R': 'pov_1_s_right',
            'JOY_BTN16': 'pov_2_up',
            'JOY_BTN18': 'pov_2_down',
            'JOY_BTN19': 'pov_2_left',
            'JOY_BTN17': 'pov_2_right',
            self.switch_key + 'JOY_BTN16': 'pov_2_s_up',
            self.switch_key + 'JOY_BTN18': 'pov_2_s_down',
            self.switch_key + 'JOY_BTN19': 'pov_2_s_left',
            self.switch_key + 'JOY_BTN17': 'pov_2_s_right',
            'JOY_BTN1': 'trigger',
            self.switch_key + 'JOY_BTN1': 'trigger_s',
            'JOY_BTN15': 'trigger_2',
            self.switch_key + 'JOY_BTN15': 'trigger_2_s',
            'JOY_BTN9': 't_1',
            'JOY_BTN10': 't_2',
            'JOY_BTN11': 't_3',
            'JOY_BTN12': 't_4',
            'JOY_BTN13': 't_5',
            'JOY_BTN14': 't_6',
            self.switch_key + 'JOY_BTN9': 't_1_s',
            self.switch_key + 'JOY_BTN10': 't_2_s',
            self.switch_key + 'JOY_BTN11': 't_3_s',
            self.switch_key + 'JOY_BTN12': 't_4_s',
            self.switch_key + 'JOY_BTN13': 't_5_s',
            self.switch_key + 'JOY_BTN14': 't_6_s',
            'JOY_BTN6': 'Pinkie Switch',
            # Throttle
            'JOY_BTN7': 'fire_d',
            self.switch_key + 'JOY_BTN7': 'fire_d_s',
            'JOY_BTN8': 'fire_e',
            self.switch_key + 'JOY_BTN8': 'fire_e_s',
            'JOY_BTN20': 'pov_3_up',
            'JOY_BTN22': 'pov_3_down',
            'JOY_BTN23': 'pov_3_left',
            'JOY_BTN21': 'pov_3_right',
            self.switch_key + 'JOY_BTN20': 'pov_3_s_up',
            self.switch_key + 'JOY_BTN22': 'pov_3_s_down',
            self.switch_key + 'JOY_BTN23': 'pov_3_s_left',
            self.switch_key + 'JOY_BTN21': 'pov_3_s_right',
            'JOY_BTN27': 'throttle_1',
            'JOY_BTN28': 'throttle_2',
            'JOY_BTN29': 'throttle_3',
            self.switch_key + 'JOY_BTN27': 'throttle_1_s',
            self.switch_key + 'JOY_BTN28': 'throttle_2_s',
            self.switch_key + 'JOY_BTN29': 'throttle_3_s',
            'JOY_BTN24': 'm_1',
            'JOY_BTN25': 'm_2',
            'JOY_BTN26': 'm_3',
            'JOY_BTN31': 'm_b_1',
            self.switch_key + 'JOY_BTN31': 'm_b_s_1',
            'JOY_BTN33': 'm_w_2_d',
            'JOY_BTN34': 'm_w_2_u',
        }

        self.position_mapping = {
            # Joystick
            'JOY_BTN2': (530, 123, 30, 'stick'),                              # fire
            'JOY_BTN3': (1350, 101, 30, 'stick'),                             # fire A
            'JOY_BTN4': (1350, 282, 30, 'stick'),                             # fire B
            'JOY_BTN5': (530, 350, 30, 'stick'),                              # fire C
            'JOY_BTN_POV1_U': (75, 342, 16, 'stick'),                         # pov hat 1 up
            'JOY_BTN_POV1_D': (75, 482, 16, 'stick'),
            'JOY_BTN_POV1_L': (5, 410, 16, 'stick'),
            'JOY_BTN_POV1_R': (140, 410, 16, 'stick'),
            'JOY_BTN16': (75, 109, 16, 'stick'),                              # pov hat 2 up
            'JOY_BTN18': (75, 249, 16, 'stick'),                              # down
            'JOY_BTN19': (5, 177, 16, 'stick'),                               # left -13
            'JOY_BTN17': (140, 177, 16, 'stick'),                             # right
            'JOY_BTN1': (1350, 461, 30, 'stick'),                             # trigger
            'JOY_BTN15': (1620, 461, 30, 'stick'),                            # stage 2 trigger
            'JOY_BTN9': (103, 609, 16, 'stick'),                              # t1
            'JOY_BTN10': (103, 679, 16, 'stick'),
            'JOY_BTN11': (230, 609, 16, 'stick'),
            'JOY_BTN12': (230, 679, 16, 'stick'),
            'JOY_BTN13': (358, 609, 16, 'stick'),
            'JOY_BTN14': (358, 679, 16, 'stick'),
            'JOY_BTN6': (1350, 644, 30, 'stick'),                                   # pinkie switch
            'JOY_BTN24': (1620, 96, 30, 'stick'),                             # mode 1
            'JOY_BTN25': (1620, 163, 30, 'stick'),
            'JOY_BTN26': (1620, 233, 30, 'stick'),
            # Throttle
            'JOY_BTN7': (1365, 266, 30, 'throttle'),                            # fire D
            'JOY_BTN8': (1368, 54, 30, 'throttle'),                             # fire E
            'JOY_BTN20': (78, 26, 16, 'throttle'),                              # pov 3 up
            'JOY_BTN22': (78, 167, 16, 'throttle'),
            'JOY_BTN23': (7, 97, 16, 'throttle'),
            'JOY_BTN21': (142, 99, 16, 'throttle'),
            'JOY_BTN27': (5, 586, 16, 'throttle'),                              # throttle 1
            'JOY_BTN28': (130, 586, 16, 'throttle'),
            'JOY_BTN29': (258, 586, 16, 'throttle'),
            'JOY_BTN31': (1367, 483, 30, 'throttle'),                            # mouse button 1
            'JOY_BTN33': (61, 302, 16, 'throttle'),                              # mouse wheel down
            'JOY_BTN34': (198, 302, 16, 'throttle'),                             # mouse wheel up
        }

        self.switched_mapping = {
            # Joystick
            'JOY_BTN2': (530, 192, 30, 'stick'),  # fire switched
            'JOY_BTN3': (1350, 170, 30, 'stick'),  # fire A switched
            'JOY_BTN4': (1350, 351, 30, 'stick'),  # fire B switched
            'JOY_BTN5': (530, 420, 30, 'stick'),  # fire C switched
            'JOY_BTN_POV1_U': (333, 342, 16, 'stick'),    # fire pov hat 1
            'JOY_BTN_POV1_D': (333, 482, 16, 'stick'),
            'JOY_BTN_POV1_L': (263, 410, 16, 'stick'),
            'JOY_BTN_POV1_R': (396, 410, 16, 'stick'),
            'JOY_BTN16': (333, 109, 16, 'stick'),  # pov hat 2 up switched
            'JOY_BTN18': (333, 249, 16, 'stick'),
            'JOY_BTN19': (263, 177, 16, 'stick'),
            'JOY_BTN17': (396, 177, 16, 'stick'),
            'JOY_BTN1': (1350, 529, 30, 'stick'),  # trigger switched
            'JOY_BTN15': (1620, 529, 30, 'stick'),  # stage 2 trigger switched
            'JOY_BTN9': (103, 761, 16, 'stick'),  # t1 switched
            'JOY_BTN10': (103, 831, 16, 'stick'),
            'JOY_BTN11': (230, 761, 16, 'stick'),
            'JOY_BTN12': (230, 831, 16, 'stick'),
            'JOY_BTN13': (358, 761, 16, 'stick'),
            'JOY_BTN14': (358, 831, 16, 'stick'),
            # Throttle
            'JOY_BTN7': (1597, 266, 30, 'throttle'),  # fire D switched
            'JOY_BTN8': (1597, 54, 30, 'throttle'),   # fire E switched
            'JOY_BTN20': (332, 26, 16, 'throttle'),  # pov 3 up switched
            'JOY_BTN22': (332, 167, 16, 'throttle'),
            'JOY_BTN23': (267, 97, 16, 'throttle'),
            'JOY_BTN21': (400, 99, 16, 'throttle'),
            'JOY_BTN27': (5, 668, 16, 'throttle'),    # throttle 1
            'JOY_BTN28': (130, 668, 16, 'throttle'),
            'JOY_BTN29': (258, 668, 16, 'throttle'),
            'JOY_BTN31': (1600, 483, 30, 'throttle'),  # mb 1 switched
        }

    def add_switch(self, control):
        if control not in self.control_mapping:
            raise Exception("Unknown switch detected - {}".format(control))
        self.switches.append(control)

    def lookup_control(self, control):
        if not control:
            return None, None
        try:
            return self.control_mapping[control], False
        except KeyError:
            try:
                return self.control_mapping[control], True
            except KeyError:
                return None, None

    def lookup_position(self, control, switched):
        if switched:
            return self.switched_mapping[control]
        else:
            return self.position_mapping[control]


class MissionParser:
    def __init__(self):
        self.msn = pydcs.Mission()

    @staticmethod
    def list_missions(path=None):
        return Path(path).glob('**/*.miz')

    def populate_modules(self):
        pass

    def parse_mission(self, mission_name):
        data = {
            'factions': {
                'blue': {
                    'slot_count': 0,
                    'aircraft': {},
                },
                'red': {
                    'slot_count': 0,
                    'aircraft': {},
                },
            },
            'map': 'unknown',
            'time': 'unknown',
            'meets_filter': False,
            'format': 'unknown',
        }
        skip = []
        if str(mission_name) in skip:
            return data
        self.msn.load_file(str(mission_name))
        data['map'] = self.msn.terrain.name
        data['format'] = self.msn.version
        data['time'] = self.msn.start_time.strftime('%H:%M')
        for country in self.msn.coalition['blue'].countries:
            for plane_group in self.msn.coalition['blue'].country(country).plane_group:
                for plane in plane_group.units:
                    if not plane.is_human():
                        continue
                    if plane.type not in data['factions']['blue']['aircraft']:
                        data['factions']['blue']['aircraft'][plane.type] = {
                            'start_type': 'unknown',
                            'count': 0,
                        }
                    data['factions']['blue']['aircraft'][plane.type]['count'] += 1
                    data['factions']['blue']['slot_count'] += 1
        for country in self.msn.coalition['red'].countries:
            for plane_group in self.msn.coalition['red'].country(country).plane_group:
                for plane in plane_group.units:
                    if not plane.is_human():
                        continue
                    if plane.type not in data['factions']['red']['aircraft']:
                        data['factions']['red']['aircraft'][plane.type] = {
                            'start_type': 'unknown',
                            'count': 0,
                        }
                    data['factions']['red']['aircraft'][plane.type]['count'] += 1
                    data['factions']['red']['slot_count'] += 1
        return data


class MissionSearcher:
    def __init__(self, pilot_mapping, slots):
        """
        pilot_mapping
        {
            "pokej6": [
                "A-10C",
                ...
            ],
            ...
        }
        slots
        {
            "A-10C": 1,
            ...
        }
        """
        self.slots = slots
        self.state = {x: None for x in pilot_mapping.keys()}
        self.pilot_mapping = pilot_mapping

    def solve(self, pilots):
        """
        pilots
        {
            "pokej6": "A-10C",
            "wrycu": None,
            ...
        }
        """
        try:
            pilot = self.find_empty(pilots)
        except IndexError:
            return True
        for module in self.pilot_mapping[pilot]:
            if self.valid(pilots, module):
                pilots[pilot] = module
                # we've made an assignment; see if we've solved everything
                if self.solve(pilots):
                    return True
                # did not work - back out the change
                pilots[pilot] = None
        return False

    def find_empty(self, pilots):
        """
        Find a pilot associated with None
        Raises an exception if all pilots are assigned
        """
        return [x for x in pilots.keys() if not pilots[x]][0]

    def valid(self, pilots, module):
        """
        Given an existing mapping of pilots to modules, determine if a new nominated mapping results in an invalid state
        """
        assigned_count = 0
        for slot in pilots.values():
            if slot == module:
                assigned_count += 1
        if module not in self.slots or assigned_count + 1 > self.slots[module]:
            return False
        else:
            return True
