import requests
import json
import configparser
import csv


class GDrive:
    def __init__(self, client_id, client_secret, refresh_token, access_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = access_token
        # v3 appears to not have the functionality we want. classic, I know
        self.base_url = 'https://www.googleapis.com/drive/v2'
        # 'ShackTac DCS/Missions' folder
        self.base_folder_id = '1gstx6nmHFxXS10QWqEhyhnA84J72ay_I'
        # Module ownership file
        self.st_module_id = '1KMzOyT4HdDm5u42O1pDuBdLMxBaGQMt-z_pEl1tGEG8'
        self.leetsaber_module_id = '1Pl0rFF3s1vzfxAg0r0gFZ7Rl8mKCrdFiKM2c8vl9lQE'

    def _make_request_(self, method, endpoint, data=None, query_params=None):
        headers = {
            ''
        }
        url = '{}/{}?access_token={}'.format(self.base_url, endpoint, self.access_token)
        if query_params:
            url += '&' + query_params
        if method == 'GET':
            reply = requests.get(
                url
            )
            try:
                reply.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if reply.status_code == 401:
                    print("Caught 401 - refreshing access token")
                    data = {
                        'refresh_token': self.refresh_token,
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'grant_type': 'refresh_token',
                    }

                    reply = requests.post('https://www.googleapis.com/oauth2/v3/token', data=data)
                    print(reply.json())
                    self.access_token = reply.json()['access_token']
                    print(self.access_token)
                    reply = self._make_request_(method, endpoint, data, query_params)
                else:
                    print(reply.text, reply.status_code)
                    raise e
        elif method == 'POST':
            reply = None
        else:
            raise Exception("GDRIVE: Unknown method {}".format(method))
        return reply

    def download_zip(self, file_id):
        return self._make_request_(
            'GET',
            'files/{}?alt=zip'.format(file_id),
        ).content.decode('utf-8')

    def get_file_details(self, file_id):
        return requests.get(
            self._make_request_(
                'GET',
                'files/{}'.format(file_id),
            ).json()['exportLinks']['text/csv'],
            stream=True,
        ).content.decode('utf-8')

    def parse_pilots(self, pilot_data):
        pilot_data = csv.reader(pilot_data.splitlines(), delimiter=',')
        pilot_modules = []
        pilots = {}
        is_pilot = False
        for row in pilot_data:
            if 'Last Updated' in row and not is_pilot:
                is_pilot = True
                for entry in row[3:]:
                    pilot_modules.append(entry)
            elif 'Last Updated' in row and is_pilot:
                is_pilot = False
            elif is_pilot:
                pilots[row[1]] = {}
                for x, entry in enumerate(row[3:]):
                    pilots[row[1]][pilot_modules[x]] = entry
        return pilots, pilot_modules

    def get_pilots(self):
        pilots = {}
        modules = {}

        pilots['st'], modules['st'] = self.parse_pilots(
            self.get_file_details(
                self.st_module_id
            )
        )
        pilots['leetsaber'], modules['leetsaber'] = self.parse_pilots(
            self.get_file_details(
                self.leetsaber_module_id
            )
        )
        return pilots, modules

    def get_folders(self, folder_id):
        all_items = []
        folders = self._make_request_(
            'GET',
            'files/{}/children'.format(folder_id),
            query_params='q=mimeType+=+\'application/vnd.google-apps.folder\'',
        ).json()['items']

        for folder in folders:
            all_items.append(folder['id'])
            all_items += self.get_folders(folder['id'])
        return all_items

    def list_files(self):
        folders = list(set(self.get_folders(self.base_folder_id)))
        print(len(folders))
        exit(0)
        for folder in folders:
            files = self._make_request_(
                'GET',
                'files/{}}',
            )
            print(len(files.json()['items']))
            try:
                print(json.dumps(
                    files.json(),
                    sort_keys=True,
                    indent=4,
                ))
            except Exception:
                pass
