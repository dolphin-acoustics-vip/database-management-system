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