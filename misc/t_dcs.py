from bs4 import BeautifulSoup as bs
from flask import render_template
from PIL import Image, ImageDraw, ImageFont
import os
import io
import base64
import dcs as pydcs
from pathlib import Path
import glob
SIZE_LARGE = 45
SIZE_NORMAL = 30
SIZE_MEDIUM = 20
SIZE_SMALL = 16


class Renderer:
    def __init__(self, controller_type, controller_image):
        self.controller_type = controller_type
        self.controller_image = controller_image

    def render(self, controls, parent):
        soup = bs(controls, 'html.parser')
        file_path = os.path.join(os.getcwd(), 'app', 'flask_app', 'static', 'img')
        # initialise the drawing context with
        # the image object as background
        image = Image.open(os.path.join(file_path, self.controller_image))
        draw = ImageDraw.Draw(image)
        table = bs.find(soup, 'table')
        switches = []
        # iterate over possible controls
        for row in table.find_all('tr'):
            columns = row.find_all('td')
            control_a = columns[0].text.replace('"', '').strip()
            # iterate over each bind for the control
            for control in control_a.split('; '):
                # look for a switch
                if not control or control in parent.ignore_mapping:
                    continue
                switched = False
                if control.find(' - ') > 0:
                    switch = control.split(' - ')[0]
                    (x, y, size, hotas) = parent.lookup_position(switch, False)
                    if hotas != self.controller_type:
                        # We've pulled a control for an object other than the type we're currently parsing; ignore it
                        continue
                    self.draw_text(draw, x, y, size, '(SWITCH)')
                    control = control.split(' - ')[1]
                    switches.append(switch)
                    switched = True
                try:
                    (x, y, size, hotas) = parent.lookup_position(control, switched)
                    if hotas != self.controller_type:
                        # We've pulled a control for an object other than the type we're currently parsing; ignore it
                        continue
                except Exception as e:
                    print("unknown control - {} - {}".format(control, e))
                    continue
                try:
                    the_draw = draw
                except KeyError:
                    print("unknown stick type")
                    continue
                message = columns[1].text.replace('"', '').strip()
                print(the_draw, x, y, size, message)
                self.draw_text(the_draw, x, y, size, message)

        # return the edited images (these are never written to disk)
        output = io.BytesIO()
        io.BytesIO(image.save(output, format='png', compress_level=9))

        output.seek(0)
        return base64.b64encode(output.getvalue()).decode('utf-8')

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


class ControlMapper:
    def __init__(self):
        pass

    def render_controls(self, controls):
        soup = bs(controls, 'html.parser')

        try:
            title = soup.find('title').next
        except Exception:
            raise Exception("Invalid/malformed file format")
        # detect controller and validate we support it
        if 'X52' in title:
            controller = X52()
        elif 'Warthog' in title:
            if 'Joystick' in title:
                controller = WarthogStick()
            elif 'Throttle' in title:
                controller = WarthogThrottle()
        else:
            raise Exception(
                "Unknown controller: {}. Supported controllers: {}".format(title, ','.join(self.controllers.keys()))
            )

        if controller.render_stick:
            stick_image = Renderer('stick', controller.stick_file).render(controls, controller)
        else:
            stick_image = None
        if controller.render_throttle:
            throttle_image = Renderer('throttle', controller.throttle_file).render(controls, controller)
        else:
            throttle_image = None

        return render_template(
            'dcs/hotas.html',
            joystick=stick_image,
            throttle=throttle_image,
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
        self.stick_file = 'x52_stick.png'
        self.throttle_file = 'x52_throttle.png'
        self.render_stick = True
        self.render_throttle = True

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
            'JOY_BTN2': (530, 123, SIZE_NORMAL, 'stick'),                              # fire
            'JOY_BTN3': (1350, 101, SIZE_NORMAL, 'stick'),                             # fire A
            'JOY_BTN4': (1350, 282, SIZE_NORMAL, 'stick'),                             # fire B
            'JOY_BTN5': (530, 350, SIZE_NORMAL, 'stick'),                              # fire C
            'JOY_BTN_POV1_U': (75, 342, SIZE_SMALL, 'stick'),                         # pov hat 1 up
            'JOY_BTN_POV1_D': (75, 482, SIZE_SMALL, 'stick'),
            'JOY_BTN_POV1_L': (5, 410, SIZE_SMALL, 'stick'),
            'JOY_BTN_POV1_R': (140, 410, SIZE_SMALL, 'stick'),
            'JOY_BTN16': (75, 109, SIZE_SMALL, 'stick'),                              # pov hat 2 up
            'JOY_BTN18': (75, 249, SIZE_SMALL, 'stick'),                              # down
            'JOY_BTN19': (5, 177, SIZE_SMALL, 'stick'),                               # left -13
            'JOY_BTN17': (140, 177, SIZE_SMALL, 'stick'),                             # right
            'JOY_BTN1': (1350, 461, SIZE_NORMAL, 'stick'),                             # trigger
            'JOY_BTN15': (1620, 461, SIZE_NORMAL, 'stick'),                            # stage 2 trigger
            'JOY_BTN9': (103, 609, SIZE_SMALL, 'stick'),                              # t1
            'JOY_BTN10': (103, 679, SIZE_SMALL, 'stick'),
            'JOY_BTN11': (230, 609, SIZE_SMALL, 'stick'),
            'JOY_BTN12': (230, 679, SIZE_SMALL, 'stick'),
            'JOY_BTN13': (358, 609, SIZE_SMALL, 'stick'),
            'JOY_BTN14': (358, 679, SIZE_SMALL, 'stick'),
            'JOY_BTN6': (1350, 644, SIZE_NORMAL, 'stick'),                                   # pinkie switch
            'JOY_BTN24': (1620, 96, SIZE_NORMAL, 'stick'),                             # mode 1
            'JOY_BTN25': (1620, 163, SIZE_NORMAL, 'stick'),
            'JOY_BTN26': (1620, 233, SIZE_NORMAL, 'stick'),
            # Throttle
            'JOY_BTN7': (1365, 266, SIZE_NORMAL, 'throttle'),                            # fire D
            'JOY_BTN8': (1368, 54, SIZE_NORMAL, 'throttle'),                             # fire E
            'JOY_BTN20': (78, 26, SIZE_SMALL, 'throttle'),                              # pov 3 up
            'JOY_BTN22': (78, 167, SIZE_SMALL, 'throttle'),
            'JOY_BTN23': (7, 97, SIZE_SMALL, 'throttle'),
            'JOY_BTN21': (142, 99, SIZE_SMALL, 'throttle'),
            'JOY_BTN27': (5, 586, SIZE_SMALL, 'throttle'),                              # throttle 1
            'JOY_BTN28': (130, 586, SIZE_SMALL, 'throttle'),
            'JOY_BTN29': (258, 586, SIZE_SMALL, 'throttle'),
            'JOY_BTN31': (1367, 483, SIZE_NORMAL, 'throttle'),                            # mouse button 1
            'JOY_BTN33': (61, 302, SIZE_SMALL, 'throttle'),                              # mouse wheel down
            'JOY_BTN34': (198, 302, SIZE_SMALL, 'throttle'),                             # mouse wheel up
        }

        self.switched_mapping = {
            # Joystick
            'JOY_BTN2': (530, 192, SIZE_NORMAL, 'stick'),  # fire switched
            'JOY_BTN3': (1350, 170, SIZE_NORMAL, 'stick'),  # fire A switched
            'JOY_BTN4': (1350, 351, SIZE_NORMAL, 'stick'),  # fire B switched
            'JOY_BTN5': (530, 420, SIZE_NORMAL, 'stick'),  # fire C switched
            'JOY_BTN_POV1_U': (333, 342, SIZE_SMALL, 'stick'),    # fire pov hat 1
            'JOY_BTN_POV1_D': (333, 482, SIZE_SMALL, 'stick'),
            'JOY_BTN_POV1_L': (263, 410, SIZE_SMALL, 'stick'),
            'JOY_BTN_POV1_R': (396, 410, SIZE_SMALL, 'stick'),
            'JOY_BTN16': (333, 109, SIZE_SMALL, 'stick'),  # pov hat 2 up switched
            'JOY_BTN18': (333, 249, SIZE_SMALL, 'stick'),
            'JOY_BTN19': (263, 177, SIZE_SMALL, 'stick'),
            'JOY_BTN17': (396, 177, SIZE_SMALL, 'stick'),
            'JOY_BTN1': (1350, 529, SIZE_NORMAL, 'stick'),  # trigger switched
            'JOY_BTN15': (1620, 529, SIZE_NORMAL, 'stick'),  # stage 2 trigger switched
            'JOY_BTN9': (103, 761, SIZE_SMALL, 'stick'),  # t1 switched
            'JOY_BTN10': (103, 831, SIZE_SMALL, 'stick'),
            'JOY_BTN11': (230, 761, SIZE_SMALL, 'stick'),
            'JOY_BTN12': (230, 831, SIZE_SMALL, 'stick'),
            'JOY_BTN13': (358, 761, SIZE_SMALL, 'stick'),
            'JOY_BTN14': (358, 831, SIZE_SMALL, 'stick'),
            # Throttle
            'JOY_BTN7': (1597, 266, SIZE_NORMAL, 'throttle'),  # fire D switched
            'JOY_BTN8': (1597, 54, SIZE_NORMAL, 'throttle'),   # fire E switched
            'JOY_BTN20': (332, 26, SIZE_SMALL, 'throttle'),  # pov 3 up switched
            'JOY_BTN22': (332, 167, SIZE_SMALL, 'throttle'),
            'JOY_BTN23': (267, 97, SIZE_SMALL, 'throttle'),
            'JOY_BTN21': (400, 99, SIZE_SMALL, 'throttle'),
            'JOY_BTN27': (5, 668, SIZE_SMALL, 'throttle'),    # throttle 1
            'JOY_BTN28': (130, 668, SIZE_SMALL, 'throttle'),
            'JOY_BTN29': (258, 668, SIZE_SMALL, 'throttle'),
            'JOY_BTN31': (1600, 483, SIZE_NORMAL, 'throttle'),  # mb 1 switched
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


class WarthogStick:
    def __init__(self):
        """
                Mapping of buttons to actual buttons

                Stick
                    Fire                JOY_BTN2        530, 135        530, 205
                    TMS FWD             JOY_BTN7
                    TMS AFT             JOY_BTN9
                    TMS LEFT            JOY_BTN10
                    TMS RIGHT           JOY_BTN8
                    DMS FWD             JOY_BTN11
                    DMS AFT             JOY_BTN13
                    DMS LEFT            JOY_BTN14
                    DMS RIGHT           JOY_BTN12
                    TRIM DOWN           JOY_BTN_POV1_D
                    TRIM UP             JOY_BTN_POV1_U
                    TRIM LEFT           JOY_BTN_POV1_L
                    TRIM RIGHT          JOY_BTN_POV1_R
                    CMS FWD             JOY_BTN15
                    CMS AFT             JOY_BTN17
                    CMS LEFT            JOY_BTN18
                    CMS RIGHT           JOY_BTN16
                    CMS DOWN
                    MASTER MODE         JOY_BTN5
                    WEAPON RELEASE      JOY_BTN2
                    TRIGGER
                    TRIGGER 2           JOY_BTN1
                    NSB                 JOY_BTN3
                    PINKIE
        """
        self.name = 'warthog_stick'
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
        self.stick_file = 'warthog_stick.png'
        self.render_stick = True
        self.render_throttle = False

        self.switch_key = 'JOY_BTN3'  # 'JOY_BTN6 - '

        self.control_mapping = {
            # Joystick
            'JOY_BTN7': 'tms_fwd',
            self.switch_key + 'JOY_BTN7': 'tms_fwd_s',
            'JOY_BTN9': 'tms_aft',
            self.switch_key + 'JOY_BTN9': 'tms_aft_s',
            'JOY_BTN10': 'tms_left',
            self.switch_key + 'JOY_BTN10': 'tms_left_s',
            'JOY_BTN8': 'tms_right',
            self.switch_key + 'JOY_BTN8': 'tms_right_s',
            'JOY_BTN11': 'dms_fwd',
            self.switch_key + 'JOY_BTN11': 'dms_fwd_s',
            'JOY_BTN13': 'dms_aft',
            self.switch_key + 'JOY_BTN13': 'dms_aft_s',
            'JOY_BTN14': 'dms_left',
            self.switch_key + 'JOY_BTN14': 'dms_left_s',
            'JOY_BTN12': 'dms_right',
            self.switch_key + 'JOY_BTN12': 'dms_right_s',
            'JOY_BTN_POV1_D': 'trim_down',
            self.switch_key + 'JOY_BTN_POV1_D': 'trim_down_s',
            'JOY_BTN_POV1_U': 'trim_up',
            self.switch_key + 'JOY_BTN_POV1_U': 'trim_up_s',
            'JOY_BTN_POV1_L': 'trim_left',
            self.switch_key + 'JOY_BTN_POV1_L': 'trim_left_s',
            'JOY_BTN_POV1_R': 'trim_right',
            self.switch_key + 'JOY_BTN_POV1_R': 'trim_right_s',
            'JOY_BTN15': 'cms_fwd',
            self.switch_key + 'JOY_BTN15': 'cms_fwd_s',
            'JOY_BTN17': 'cms_aft',
            self.switch_key + 'JOY_BTN17': 'cms_aft_s',
            'JOY_BTN18': 'cms_left',
            self.switch_key + 'JOY_BTN18': 'cms_left_s',
            'JOY_BTN16': 'cms_right',
            self.switch_key + 'JOY_BTN16': 'cms_right_s',
            '': 'cms_down',
            self.switch_key + '': 'cms_down_s',
            'JOY_BTN5': 'master_mode',
            self.switch_key + 'JOY_BTN5': 'master_mode_s',
            'JOY_BTN2': 'weapon_release',
            self.switch_key + 'JOY_BTN2': 'weapon_release_s',
            'JOY_BTN1': 'weapon_fire',
            self.switch_key + 'JOY_BTN1': 'weapon_fire_s',
            'JOY_BTN3': 'nose_wheel_steering',
            self.switch_key + 'JOY_BTN3': 'nose_wheel_steering_s',
            '': 'r_pinkie_switch',
            self.switch_key + '': 'r_pinkie_switch_s',
        }

        self.position_mapping = {
            # Joystick
            'JOY_BTN7': (622, 542, SIZE_MEDIUM, 'stick'),  # TMS FWD
            'JOY_BTN9': (622, 642, SIZE_MEDIUM, 'stick'),  # TMS AFT
            'JOY_BTN10': (526, 593, SIZE_MEDIUM, 'stick'),  # TMS LEFT
            'JOY_BTN8': (713, 593, SIZE_MEDIUM, 'stick'),  # TMS RIGHT
            'JOY_BTN11': (1449, 885, SIZE_MEDIUM, 'stick'),  # DMS FWD
            'JOY_BTN13': (1449, 986, SIZE_MEDIUM, 'stick'),  # DMS AFT
            'JOY_BTN14': (1350, 937, SIZE_MEDIUM, 'stick'),  # DMS LEFT
            'JOY_BTN12': (1538, 937, SIZE_MEDIUM, 'stick'),  # DMS RIGHT
            'JOY_BTN_POV1_D': (1388, 237, SIZE_MEDIUM, 'stick'),  # TRIM DOWN
            'JOY_BTN_POV1_U': (1391, 342, SIZE_MEDIUM, 'stick'),  # TRIM UP
            'JOY_BTN_POV1_L': (1290, 287, SIZE_MEDIUM, 'stick'),  # TRIM LEFT
            'JOY_BTN_POV1_R': (1478, 287, SIZE_MEDIUM, 'stick'),  # TRIM RIGHT
            'JOY_BTN15': (627, 905, SIZE_MEDIUM, 'stick'),  # CMS FWD
            'JOY_BTN17': (627, 1007, SIZE_MEDIUM, 'stick'),  # CMS AFT
            'JOY_BTN18': (531, 957, SIZE_MEDIUM, 'stick'),  # CMS LEFT
            'JOY_BTN16': (718, 957, SIZE_MEDIUM, 'stick'),  # CMS RIGHT
            '': (0, 0, SIZE_MEDIUM, 'stick'),  # CMS DOWN
            'JOY_BTN5': (1524, 439, SIZE_MEDIUM, 'stick'),  # MASTER MODE
            'JOY_BTN2': (975, 208, SIZE_MEDIUM, 'stick'),  # WEAPON RELEASE
            'JOY_BTN1': (0, 0, SIZE_MEDIUM, 'stick'),  # WEAPON FIRE
            'JOY_BTN3': (510, 1225, SIZE_MEDIUM, 'stick'),  # NOSE WHEEL STEERING
            '': (510, 1158, SIZE_MEDIUM, 'stick'),  # PINKIE SWITCH
        }

        self.switched_mapping = {
            # Joystick
            'JOY_BTN7': (0, 0, SIZE_LARGE, 'stick'),  # TMS FWD
            'JOY_BTN9': (0, 0, SIZE_LARGE, 'stick'),  # TMS AFT
            'JOY_BTN10': (0, 0, SIZE_LARGE, 'stick'),  # TMS LEFT
            'JOY_BTN8': (0, 0, SIZE_LARGE, 'stick'),  # TMS RIGHT
            'JOY_BTN11': (0, 0, SIZE_LARGE, 'stick'),  # DMS FWD
            'JOY_BTN13': (0, 0, SIZE_LARGE, 'stick'),  # DMS AFT
            'JOY_BTN14': (0, 0, SIZE_LARGE, 'stick'),  # DMS LEFT
            'JOY_BTN12': (0, 0, SIZE_LARGE, 'stick'),  # DMS RIGHT
            'JOY_BTN_POV1_D': (0, 0, SIZE_LARGE, 'stick'),  # TRIM DOWN
            'JOY_BTN_POV1_U': (0, 0, SIZE_LARGE, 'stick'),  # TRIM UP
            'JOY_BTN_POV1_L': (0, 0, SIZE_LARGE, 'stick'),  # TRIM LEFT
            'JOY_BTN_POV1_R': (0, 0, SIZE_LARGE, 'stick'),  # TRIM RIGHT
            'JOY_BTN15': (0, 0, SIZE_LARGE, 'stick'),  # CMS FWD
            'JOY_BTN17': (0, 0, SIZE_LARGE, 'stick'),  # CMS AFT
            'JOY_BTN18': (0, 0, SIZE_LARGE, 'stick'),  # CMS LEFT
            'JOY_BTN16': (0, 0, SIZE_LARGE, 'stick'),  # CMS RIGHT
            '': (0, 0, SIZE_LARGE, 'stick'),  # CMS DOWN
            'JOY_BTN5': (0, 0, SIZE_LARGE, 'stick'),  # MASTER MODE
            'JOY_BTN2': (0, 0, SIZE_LARGE, 'stick'),  # WEAPON RELEASE
            'JOY_BTN1': (0, 0, SIZE_LARGE, 'stick'),  # WEAPON FIRE
            'JOY_BTN3': (0, 0, SIZE_LARGE, 'stick'),  # NOSE WHEEL STEERING
            '': (0, 0, SIZE_LARGE, 'stick'),  # PINKIE SWITCH
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


class WarthogThrottle:
    def __init__(self):
        """
                Mapping of buttons to actual buttons
                Throttle
                    Coolie Switch Up    JOY_BTN_POV1_U
                    Coolie Switch Down  JOY_BTN_POV1_D
                    Coolie Switch Left  JOY_BTN_POV1_L
                    Coolie Switch Right JOY_BTN_POV1_R
                    Mic Switch FWD
                    Mic Switch AFT
                    Mic Switch LEFT
                    Mic Switch RIGHT
                    SPEEDBRAKE OUT
                    SPEEDBRAKE IN
                    Boat switch FWD
                    Boat Switch AFT
                    China Hat FWD       JOY_BTN11
                    China Hat AFT
                    Throttle Button     JOY_BTN15
                    Pinkie Switch
                    FLAPS UP            JOY_BTN22
                    FLAPS DWN           JOY_BTN23
        """
        self.name = 'warthog_throttle'
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
        self.throttle_file = 'warthog_throttle.png'
        self.render_stick = False
        self.render_throttle = True

        self.switch_key = 'JOY_BTN3'  # 'JOY_BTN6 - '

        self.control_mapping = {
            # Throttle
            'JOY_BTN_POV1_U': 'coolie_switch_up',
            self.switch_key + '': 'coolie_switch_up_s',
            'JOY_BTN_POV1_D': 'coolie_switch_down',
            self.switch_key + '': 'coolie_switch_down_s',
            'JOY_BTN_POV1_L': 'coolie_switch_left',
            self.switch_key + '': 'coolie_switch_left_s',
            'JOY_BTN_POV1_R': 'coolie_switch_right',
            self.switch_key + '': 'coolie_switch_right_s',
            '': 'mic_switch_fwd',
            self.switch_key + '': 'mic_switch_fwd_s',
            '': 'mic_switch_aft',
            self.switch_key + '': 'mic_switch_aft_s',
            '': 'mic_switch_left',
            self.switch_key + '': 'mic_switch_left_s',
            '': 'mic_switch_right',
            self.switch_key + '': 'mic_switch_right_s',
            '': 'speedbrake_out',
            self.switch_key + '': 'speedbrake_out_s',
            '': 'speedbrake_in',
            self.switch_key + '': 'speedbrake_in_s',
            '': 'boat_switch_fwd',
            self.switch_key + '': 'boat_switch_fwd_s',
            '': 'boat_switch_aft',
            self.switch_key + '': 'boat_switch_aft_s',
            'JOY_BTN11': 'china_hat_fwd',
            self.switch_key + 'JOY_BTN11': 'china_hat_fwd_s',
            '': 'china_hat_aft',
            self.switch_key + '': 'china_hat_aft_s',
            'JOY_BTN15': 'throttle_button',
            self.switch_key + 'JOY_BTN15': 'throttle_button_s',
            '': 'l_pinkie_switch',
            self.switch_key + 'l_pinkie_switch': 'l_pinkie_switch_s',
            'JOY_BTN22': 'flaps_up',
            self.switch_key + 'JOY_BTN22': 'flaps_up_s',
            'JOY_BTN23': 'flaps_down',
            self.switch_key + 'JOY_BTN23': 'flaps_down_s',
        }

        self.position_mapping = {
            # Throttle
            'JOY_BTN_POV1_U': (893, 220, SIZE_NORMAL, 'throttle'),  # Coolie Switch Up
            'JOY_BTN_POV1_D': (893, 321, SIZE_NORMAL, 'throttle'),  # Coolie Switch Down
            'JOY_BTN_POV1_L': (798, 272, SIZE_NORMAL, 'throttle'),  # Coolie Switch Left
            'JOY_BTN_POV1_R': (983, 272, SIZE_NORMAL, 'throttle'),  # Coolie Switch Right
            '': (648, 589, SIZE_NORMAL, 'throttle'),  # Mic Switch FWD
            '': (648, 687, SIZE_NORMAL, 'throttle'),  # Mic Switch AFT
            '': (549, 641, SIZE_NORMAL, 'throttle'),  # Mic Switch LEFT
            '': (737, 641, SIZE_NORMAL, 'throttle'),  # Mic Switch RIGHT
            '': (0, 0, SIZE_NORMAL, 'throttle'),  # Speed brake out
            '': (0, 0, SIZE_NORMAL, 'throttle'),  # Speed brake in
            '': (17, 947, SIZE_NORMAL, 'throttle'),  # Boat Switch FWD
            '': (376, 947, SIZE_NORMAL, 'throttle'),  # Boat Switch AFT
            'JOY_BTN11': (15, 1075, SIZE_NORMAL, 'throttle'),  # China Hat FWD
            '': (378, 1075, SIZE_NORMAL, 'throttle'),  # China Hat AFT
            'JOY_BTN15': (54, 695, SIZE_NORMAL, 'throttle'),  # Throttle Button
            '': (0, 0, SIZE_NORMAL, 'throttle'),  # Pinkie Switch
            'JOY_BTN22': (0, 0, SIZE_NORMAL, 'throttle'),  # Flaps Up
            'JOY_BTN23': (0, 0, SIZE_NORMAL, 'throttle'),  # Flaps Down
        }

        self.switched_mapping = {
            # Throttle
            'JOY_BTN_POV1_U': (0, 0, SIZE_LARGE, 'throttle'),  # Coolie Switch Up
            'JOY_BTN_POV1_D': (0, 0, SIZE_LARGE, 'throttle'),  # Coolie Switch Down
            'JOY_BTN_POV1_L': (0, 0, SIZE_LARGE, 'throttle'),  # Coolie Switch Left
            'JOY_BTN_POV1_R': (0, 0, SIZE_LARGE, 'throttle'),  # Coolie Switch Right
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Mic Switch FWD
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Mic Switch AFT
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Mic Switch LEFT
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Mic Switch RIGHT
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Speed brake out
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Speed brake in
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Boat Switch FWD
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Boat Switch AFT
            'JOY_BTN11': (0, 0, SIZE_LARGE, 'throttle'),  # China Hat FWD
            '': (0, 0, SIZE_LARGE, 'throttle'),  # China Hat AFT
            'JOY_BTN15': (0, 0, SIZE_LARGE, 'throttle'),  # Throttle Button
            '': (0, 0, SIZE_LARGE, 'throttle'),  # Pinkie Switch
            'JOY_BTN22': (0, 0, SIZE_LARGE, 'throttle'),  # Flaps Up
            'JOY_BTN23': (0, 0, SIZE_LARGE, 'throttle'),  # Flaps Down
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
