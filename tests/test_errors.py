import pytest

def test_403_error_page(logged_in_general_client):
    # Simulate a 403 error
    response = logged_in_general_client.get('/admin')

    # Check that the response status code is 403
    assert response.status_code == 403
