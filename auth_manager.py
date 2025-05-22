import json
import os
from typing import Dict, List, Optional

class AuthManager:
    def __init__(self, auth_file: str = 'calendar_auth.json'):
        self.auth_file = auth_file
        self.auth_data = self._load_auth_data()

    def _load_auth_data(self) -> Dict:
        if os.path.exists(self.auth_file):
            with open(self.auth_file, 'r') as f:
                return json.load(f)
        return {
            'owners': [],
            'shared_calendars': {},
            'authorized_users': {}
        }

    def _save_auth_data(self):
        with open(self.auth_file, 'w') as f:
            json.dump(self.auth_data, f)

    def add_owner(self, user_id: int, calendar_id: str):
        if user_id not in self.auth_data['owners']:
            self.auth_data['owners'].append(user_id)
            self.auth_data['shared_calendars'][str(user_id)] = {
                'primary': calendar_id,
                'shared_with': []
            }
            self._save_auth_data()

    def share_calendar(self, owner_id: int, user_id: int, access_code: str):
        if str(owner_id) in self.auth_data['shared_calendars']:
            self.auth_data['authorized_users'][str(user_id)] = {
                'owner_id': owner_id,
                'access_code': access_code,
                'verified': False
            }
            self._save_auth_data()

    def verify_access(self, user_id: int, access_code: str) -> bool:
        user_str = str(user_id)
        if user_str in self.auth_data['authorized_users']:
            if self.auth_data['authorized_users'][user_str]['access_code'] == access_code:
                self.auth_data['authorized_users'][user_str]['verified'] = True
                self._save_auth_data()
                return True
        return False

    def is_authorized(self, user_id: int) -> bool:
        return (user_id in self.auth_data['owners'] or 
                (str(user_id) in self.auth_data['authorized_users'] and 
                 self.auth_data['authorized_users'][str(user_id)]['verified']))

    def get_owner_id(self, user_id: int) -> Optional[int]:
        if user_id in self.auth_data['owners']:
            return user_id
        if str(user_id) in self.auth_data['authorized_users']:
            return self.auth_data['authorized_users'][str(user_id)]['owner_id']
        return None