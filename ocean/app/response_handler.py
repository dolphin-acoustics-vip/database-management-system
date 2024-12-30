# Copyright (c) 2024
#
# This file is part of OCEAN.
#
# OCEAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OCEAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

import json
from flask import jsonify

class JSONResponse:
    def __init__(self, messages: str = None, errors: list = None, redirect: str = None):
        self.messages = messages or []
        self.errors = errors or []
        self.redirect = redirect

    def add_error(self, error):
        self.errors.append(error)

    def add_message(self, message):
        self.messages.append(message)
    
    def set_redirect(self, redirect):
        self.redirect = redirect

    def to_json(self):
        data = {
            'messages': self.messages,
            'errors': self.errors,
            'redirect': self.redirect,
        }
        return jsonify(data)