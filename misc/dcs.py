from bs4 import BeautifulSoup as bs
from jinja2 import Environment, FileSystemLoader
from flask import render_template


class ControlMapper:
    def __init__(self):
        self.controllers = {
            'X52': X52(),
        }

    def render_controls(self, controls):
        output = {}
        soup = bs(controls, 'html.parser')

        try:
            title = soup.find('title').next
        except Exception:
            raise Exception("Invalid/malformed file format")
        controller = None
        for a_controller in self.controllers.keys():
            if a_controller in title:
                controller = self.controllers[a_controller]
        if not controller:
            raise Exception("Unknown controller: {}".format(title))

        table = bs.find(soup, 'table')
        for row in table.find_all('tr'):
            columns = row.find_all('td')
            control = columns[0].text.replace('"', '').strip()
            if control in controller.control_mapping:
                output[controller.control_mapping[control]] = columns[1].text.replace('"', '').strip()
            elif control and control not in controller.ignore_mapping:
                print("Found control not mapped to", controller.name, control)
        return render_template('dcs/{}.html'.format(controller.name), **output)


class X52:
    def __init__(self):
        """
        Mapping of buttons to actual buttons

        Stick
            Fire                JOY_BTN2        592,148         687,148
            Fire A              JOY_BTN3        1381,486        1473,486
            Fire B              JOY_BTN4        1379,636        1475,636
            Fire C              JOY_BTN5        592,329         689,329
            POV Hat 1           --------
                Up              JOY_BTN_POV1_U  139,618         351,618
                Down            JOY_BTN_POV1_D  139,687
                Left            JOY_BTN_POV1_L  90,652
                Right           JOY_BTN_POV1_R  190,652
            POV Hat 2           ---------
                Up              JOY_BTN16       139,344         348,344
                Down            JOY_BTN18       139,413
                Left            JOY_BTN19       91,380
                Right           JOY_BTN17       191,378
            Trigger             JOY_BTN1        596,467
            Second Trigger      JOY_BTN15       597,599
            Toggle 1            JOY_BTN9        107,909
            Toggle 2            JOY_BTN10       107,944
            Toggle 3            JOY_BTN11       224,909
            Toggle 4            JOY_BTN12
            Toggle 5            JOY_BTN13
            Toggle 6            JOY_BTN14
            Pinkie Switch       JOY_BTN6        1452,803
        Throttle
            Fire D              JOY_BTN7
            Fire E              JOY_BTN8
            Rotary 1
                Clockwise
                C-Clockwise
            Rotary 2
                Clockwise
                C-Clockwise
            POV Hat 3
                Up              JOY_BTN20
                Down            JOY_BTN22
                Left            JOY_BTN23
                Right           JOY_BTN21
            Ministick
            Throttle Base 1     JOY_BTN27
            Throttle Base 2     JOY_BTN28
            Throttle Base 3     JOY_BTN29
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
        }

        self.switch_key = 'JOY_BTN6 - '

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
