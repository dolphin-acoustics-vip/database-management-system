from datetime import datetime, timedelta
from flask_restx import Resource, reqparse, marshal_with, fields, Namespace, inputs
from flask import Response, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from ... import models, exception_handler

api = Namespace('auth', 'All endpoints that are used for authentication.' )


login_resource_parser = reqparse.RequestParser()
login_resource_parser.add_argument('username', type=str, required=True, location='args')
login_resource_parser.add_argument('password', type=str, required=True, location='args')

@api.route('/login/')
class LoginResource(Resource):
    @api.expect(login_resource_parser)
    def post(self):
        username = login_resource_parser.parse_args().get('username')
        password = login_resource_parser.parse_args().get('password')
        user = models.User.query.filter_by(login_id=username).first()
        if not user:
            raise exception_handler.DoesNotExistError("User")
        elif not user.api_password_hash:
            raise exception_handler.WarningException("User does not have API privileges")
        elif not password:
            raise exception_handler.WarningException("Password is required")
        elif not check_password_hash(user.api_password_hash, password):
            raise exception_handler.WarningException("Incorrect password")
        elif not user.is_active:
            raise exception_handler.WarningException("User is inactive")
        days_until_expiry = (user.expiry - datetime.now().date()).days
        if user.expiry < datetime.now().date():
            raise exception_handler.WarningException("User has expired")
        expires_delta = timedelta(minutes=15)
        return {"access_token": create_access_token(user, expires_delta=expires_delta)}, 200