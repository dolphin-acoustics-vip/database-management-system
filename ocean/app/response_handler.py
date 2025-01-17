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

from flask import jsonify
from urllib.parse import quote


class JSONResponse:
    """This class acts as a protocol for responses to HTTP requests in OCEAN.
    The class should usually be used for POST and DELETE requests (whereas 
    GET requests are better suited to returning html for example with
    `flask.render_template()`). Standard usage of `JSONResponse` would be to
    create an instance of the class at the start of a flask route handler and
    use `to_json()` when returning the response. WARNING: do not return the object
    itself.

    The protocol involves a JSON object with the following fields:
    `messages`: a list of messages (str) to be displayed to the user (via javascript alert())
    `errors`: a list of errors (str) to be displayed to the user (via javascript alert())
    `redirect`: the url to redirect the user to (afer `messages` and `errors` have been displayed)

    `messages` and `errors` can be added using `add_message()` and `add_error()` respectively.
    A redirect link can be assigned using `set_redirect()`.

    The following are the most likely use cases:
    - a `JSONResponse` with no redirect and messages but with errors implies an error occurred
    - a `JSONResponse` with a redirect and no messages or errors implies a successful operation
    - a `JSONResponse` with a redirect and messages or errors implies a successful operation but with warnings
    """

    def __init__(self, messages: str = None, errors: list = None, redirect: str = None, data: dict = None):
        self.messages = messages or []
        self.errors = errors or []
        self.data = data or {}
        self.redirect = redirect

    def encode_url(self, url):
        return quote(url, safe=':/?=&')

    def custom_encode(self, data):
        if isinstance(data, dict):
            return {key: self.custom_encode(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.custom_encode(item) for item in data]
        elif isinstance(data, str):
            if data.startswith('/'):
                return self.encode_url(data)
            else:
                return data
        elif isinstance(data, bytes):
            return str(data)
        else:
            return data

    def add_error(self, error):
        self.errors.append(error)

    def add_message(self, message):
        self.messages.append(message)
    
    def set_redirect(self, redirect):
        self.redirect = redirect

    def to_json(self):
        self.data = self.custom_encode(self.data)
        print(self.data)
        d = {
            'messages': self.messages,
            'errors': self.errors,
            'redirect': self.redirect,
            'data': self.data
        }
        return jsonify(d)