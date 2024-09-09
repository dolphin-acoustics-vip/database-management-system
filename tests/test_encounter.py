import pytest
import models
import flask
import sqlalchemy
import exception_handler

blank_error_message = "cannot be blank"
string_error_message = "must be a string"
timezone_bounds_error_message = "timezone must be between"
timezone_datatype_error_message = "timezone must be an integer"
invalid_id_error_message = "invalid id format"
invalid_float_error_message = "invalid float format"
invalid_latitude_error_message = "latitude must be between -90 and 90"
invalid_longitude_error_message = "longitude must be between -180 and 180"

def test_setter_encounter_latitude(db_session, encounter_object: models.Encounter):
    i = -90
    while i < 90:
        encounter_object.set_latitude(str(i))
        db_session.commit()
        assert encounter_object.get_latitude() == i
        encounter_object.set_latitude(i)
        db_session.commit()
        assert encounter_object.get_latitude() == i
        i += 0.25

    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_latitude("2.42sasd")
    assert invalid_float_error_message in str(exc).lower()
    
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_latitude(91)
    assert invalid_latitude_error_message in str(exc).lower()

def test_setter_encounter_longitude(db_session, encounter_object: models.Encounter):
    i = -180
    while i < 180:
        # encounter_object.set_longitude(str(i))
        # db_session.commit()
        # assert encounter_object.get_longitude() == i
        encounter_object.set_longitude(i)
        db_session.commit()
        assert encounter_object.get_longitude() == i
        i += 0.25
    
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_longitude("2.42sasd")
    assert invalid_float_error_message in str(exc).lower()
    
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_longitude(181)
    assert invalid_longitude_error_message in str(exc).lower()

def test_setter_species_id(db_session, species_object1: models.Species, encounter_object: models.Encounter):
    encounter_object.set_species_id(species_object1.id)
    db_session.commit()
    assert encounter_object.get_species() == species_object1

    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_species_id('4k3jt103t-13rvfds-32tsdf') # not a valid UUID
    assert invalid_id_error_message in str(exc).lower()

def test_setter_file_timezone(db_session, encounter_object: models.Encounter):
    timezone = -(12*60)
    while timezone < (14*60):
        # Test setting of int and str
        encounter_object.set_file_timezone(timezone)
        db_session.commit()
        assert encounter_object.get_file_timezone() == timezone
        encounter_object.set_file_timezone(str(timezone))
        db_session.commit()
        assert encounter_object.get_file_timezone() == timezone
        timezone += 15

    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_file_timezone(-(12*60)-1)
    assert timezone_bounds_error_message in str(exc).lower()

    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_file_timezone((14*60)+1)
    assert timezone_bounds_error_message in str(exc).lower()

    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_file_timezone("0sfa")
    assert timezone_datatype_error_message in str(exc).lower()

def test_setter_local_timezone(db_session, encounter_object: models.Encounter):
    timezone = -(12*60)
    while timezone < (14*60):
        # Test setting of int and str
        encounter_object.set_local_timezone(str(timezone))
        db_session.commit()
        assert encounter_object.get_local_timezone() == timezone
        encounter_object.set_local_timezone(timezone)
        db_session.commit()
        assert encounter_object.get_local_timezone() == timezone
        timezone += 15

    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_local_timezone(-(12*60)-1)
    assert timezone_bounds_error_message in str(exc).lower()

    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_local_timezone((14*60)+1)
    assert timezone_bounds_error_message in str(exc).lower()

    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_local_timezone("0sfa")
    assert timezone_datatype_error_message in str(exc).lower()


def test_setter_encounter_name(db_session, encounter_object: models.Encounter):
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_encounter_name("")
    assert blank_error_message in str(exc).lower()
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_encounter_name(["A list is not a string"])
    assert string_error_message in str(exc).lower()
    encounter_object.set_encounter_name("Valid Name")
    db_session.commit()
    assert encounter_object.get_encounter_name() == "Valid Name"
    

def test_setter_location(db_session, encounter_object: models.Encounter):
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_location("")
    assert blank_error_message in str(exc).lower()
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_location(["A list is not a string"])
    assert string_error_message in str(exc).lower()
    encounter_object.set_location("Valid Location")
    db_session.commit()
    assert encounter_object.get_location() == "Valid Location"

def test_setter_project(db_session, encounter_object: models.Encounter):
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_project("")    
    assert blank_error_message in str(exc).lower()
    with pytest.raises(exception_handler.WarningException) as exc:
        encounter_object.set_project(["A list is not a string"])
    assert string_error_message in str(exc).lower()
    encounter_object.set_project("Valid Project")
    db_session.commit()
    assert encounter_object.get_project() == "Valid Project"

def test_duplicate_encounter(app, db_session, species_object: models.Species):
    """
    Test whether Encounter integrity is failed with a unique constraint
    of encounter_name, location, and project.
    """
    with app.app_context():
        species = species_object

        duplicate_encounter_name_obj1 = models.Encounter(
            encounter_name='Test Encounter',
            location='Test Location',
            species_id=species.id,
            project='Test Project',
            file_timezone='0',
            local_timezone='0'
        )
        db_session.add(duplicate_encounter_name_obj1)

        duplicate_encounter_name_obj2 = models.Encounter(
            encounter_name='Test Encounter',
            location='Test Location',
            species_id=species.id,
            project='Test Project',
            file_timezone='0',
            local_timezone='0'
        )
        db_session.add(duplicate_encounter_name_obj2)


        with pytest.raises(sqlalchemy.exc.IntegrityError) as excinfo:
            db_session.commit()

        assert excinfo.value.orig.args[0] == 1062

