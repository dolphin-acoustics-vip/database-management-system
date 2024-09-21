import pytest
from flask import *

def test_home_route_logged_out(client):
    response = client.get('/home')
    assert response.status_code == 302
