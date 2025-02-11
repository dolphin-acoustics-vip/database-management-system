from flask_restful import Resource
from ... import models

class Selections(Resource):
    def get(self):
        selections = models.Selection.query.all()
        return [selection.to_dict() for selection in selections]