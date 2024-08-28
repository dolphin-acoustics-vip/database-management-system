# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

# Local application imports
from database_handler import Session, require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
from exception_handler import *

routes_admin = Blueprint('admin', __name__)

@routes_admin.route('/admin', methods=['GET'])
@exclude_role_4
@exclude_role_3
def admin():
    """
    Route to redirect root to the admin_dashboard() page.
    PERMISSIONS: Role 1, Role 2.
    """
    return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/dashboard', methods=['GET'])
@exclude_role_4
@exclude_role_3
def admin_dashboard():
    """
    Route for the admin dashboard page.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET
    """
    # TODO: split the data source, recording platform, and species editing, into different subpages
    with Session() as session:
        data_source_list = session.query(DataSource).all()
        recording_platform_list = session.query(RecordingPlatform).all()
        species_list = session.query(Species).all()
        return render_template('admin/admin-dashboard.html', data_source_list=data_source_list, recording_platform_list=recording_platform_list, species_list=species_list)

@routes_admin.route('/admin/data-source/<data_source_id>/view', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_data_source_view(data_source_id):
    """
    Route for viewing a specific data source in the admin panel.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET
    """
    with Session() as session:
        try:
            data_source = session.query(DataSource).filter_by(id=data_source_id).first()  
            return render_template('admin/admin-data-source-view.html', data_source=data_source, data_source_type_values  = DataSource.type.type.enums)
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
            return redirect(url_for('admin.admin_dashboard'))
        
@routes_admin.route('/admin/data-source/<data_source_id>/edit', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_data_source_edit(data_source_id):
    """
    Update the data for a data source in the admin panel.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with Session() as session:
        try:
            # Update a DataSource object with form data
            data_source = session.query(DataSource).filter_by(id=data_source_id).first()  
            data_source.name = request.form['name']
            data_source.phone_number1 = request.form['phone_number1']
            data_source.phone_number2 = request.form['phone_number2']
            data_source.email1 = request.form['email1']
            data_source.email2 = request.form['email2']
            data_source.address = request.form['address']
            data_source.notes = request.form['notes']
            data_source.type = request.form['source-type']
            session.commit()
            flash('Data source updated: {}'.format(data_source.name), 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
    return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/data-source/new', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_data_source_new():
    """
    Route for the new data source page.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    return render_template('admin/admin-data-source-new.html', data_source_type_values = DataSource.type.type.enums)

@routes_admin.route('/admin/data-source/insert', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_data_source_insert():
    """
    Route to insert a new data source into the database. 
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    
    Requires a form with the following input fields (text input unless otherwise stated):
    - name
    - phone_number1
    - phone_number2
    - email1
    - email2
    - address
    - notes
    - source-type (dropdown of enum('person','organisation')); NOT NULL
    """
    with Session() as session:
        try:
            # Create a new data source with form data
            new_data_source = DataSource(
                name=request.form['name'],
                phone_number1=request.form['phone_number1'],
                phone_number2=request.form['phone_number2'],
                email1=request.form['email1'],
                email2=request.form['email2'],
                address=request.form['address'],
                notes=request.form['notes'],
                type=request.form['source-type']
            )
            session.add(new_data_source)
            session.commit()
            flash('Data source created: {}'.format(new_data_source.name), 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/data-source/<data_source_id>/delete', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_data_source_delete(data_source_id):
    """
    Route to delete a DataSource object given its ID. 
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    with Session() as session:
        try:
            data_source = session.query(DataSource).filter_by(id=data_source_id).first()
            session.delete(data_source)
            session.commit()
            flash('Data source deleted: {}'.format(data_source.name), 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
            
    return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/<recording_platform_id>/view', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_recording_platform_view(recording_platform_id):
    """
    Route to view a RecordingPlatform object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with Session() as session:
        try:
            recording_platform = session.query(RecordingPlatform).filter_by(id=recording_platform_id).first()  
            return render_template('admin/admin-recording-platform-view.html', recording_platform=recording_platform)
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
            return redirect(url_for('admin.admin_dashboard'))
        
@routes_admin.route('/admin/recording-platform/<recording_platform_id>/edit', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_recording_platform_edit(recording_platform_id):
    """
    Route to update a RecordingPlatform object, given its ID and an HTTP form request with the following fields:
    - name (text) NOT NULL
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST
    """
    with Session() as session:
        try:
            recording_platform = session.query(RecordingPlatform).filter_by(id=recording_platform_id).first()
            recording_platform.name = request.form['name']
            session.commit()
            flash('Recording platform updated: {}'.format(recording_platform.name), 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/new', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_recording_platform_new():
    """
    Route for viewing the page to create a new RecordingPlatform object.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET
    """
    return render_template('admin/admin-recording-platform-new.html')

@routes_admin.route('/admin/recording-platform/insert', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_recording_platform_insert():
    """
    Route to create a new RecordingPlatform object, given an HTTP form request with the following fields:
    - name (text) NOT NULL
    PERMISSIONS: Role 1, Role 2.
    METHODS: POST.
    """
    with Session() as session:
        try:
            new_recording_platform = RecordingPlatform(
                name=request.form['name']
            )
            session.add(new_recording_platform)
            session.commit()
            flash('Recording platform created: {}'.format(new_recording_platform.name), 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/<recording_platform_id>/delete', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_recording_platform_delete(recording_platform_id):
    """
    Route to delete a RecordingPlatform object from the database, given its ID.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with Session() as session:
        try:
            recording_platform = session.query(RecordingPlatform).filter_by(id=recording_platform_id).first()
            session.delete(recording_platform)
            session.commit()
            flash('Recording platform deleted: {}'.format(recording_platform.name), 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/species/<species_id>/view', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_species_view(species_id):
    """
    Route to open the edit page for a Species object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    with Session() as session:
        try:
            session = Session()
            species_data = session.query(Species).filter_by(id=species_id).first()
            return render_template('admin/admin-species-view.html', species=species_data)
        except Exception as e:
            handle_sqlalchemy_exception(session, e)
            return redirect(url_for('admin.admin_dashboard'))
    
@routes_admin.route('/admin/species/<species_id>/edit', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_species_edit(species_id):
    """
    Route to update a Species object with new values, given a form with the following fields:
    - species_name (text) NOT NULL
    - genus_name (text)
    - common_name (text)
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with Session() as session:
        species_data = session.query(Species).filter_by(id=species_id).first()
        if species_data:
            try:
                species_name = request.form['species_name']
                genus_name = request.form['genus_name']
                common_name = request.form['common_name']
                species_data.set_species_name(species_name)
                species_data.set_genus_name(genus_name)
                species_data.set_common_name(common_name)
                species_data.update_call(session)
                session.commit()
                flash('Species updated: {}'.format(species_name), 'success')
            except Exception as e:
                handle_sqlalchemy_exception(session, e)
        else:
            flash('Species with ID {} not found'.format(species_id), 'error')
            session.rollback()
        return redirect(url_for('admin.admin_dashboard'))


@routes_admin.route('/admin/species/<species_id>/delete', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_species_delete(species_id):
    """
    Route to delete a Species object, give its ID.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with Session() as session:
        try:
            species = session.query(Species).filter_by(id=species_id).first()
            species_name = species.get_species_name()
            session.delete(species)
            session.commit()
            flash('Species deleted: {}'.format(species_name), 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

    
@routes_admin.route('/admin/species/new', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_species_new():
    """
    Route to render the new Species template.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    return render_template('admin/admin-species-new.html')

@routes_admin.route('/admin/species/insert', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_species_insert():
    """
    Route to create a new Species object, given an HTTP form request with:
    - species_name (text) NOT NULL
    - genus_name (text)
    - common_name (text)
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST
    """
    with Session() as session:
        species_name = request.form['species_name']
        genus_name = request.form['genus_name']
        common_name = request.form['common_name']
        try:
            new_species = Species(species_name=species_name, genus_name=genus_name, common_name=common_name)
            session.add(new_species)
            session.commit()
            flash('Species added: {}.'.format(species_name), 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session,e)
    return redirect(url_for('admin.admin_dashboard'))



@routes_admin.route('/admin/user', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_user():
    """
    Route to render the template to view all users.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with Session() as session:
        users = session.query(User).filter_by(is_temporary=0).order_by(User.is_active.desc()).all()
        temporary_users = session.query(User).filter_by(is_temporary=1).order_by(User.is_active.desc()).all()
        return render_template('admin/admin-user.html', users=users, temporary_users=temporary_users)
    
    
@routes_admin.route('/admin/user/<user_id>/view', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_user_view(user_id):
    """
    Route to view info on a particular User object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with Session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        roles = session.query(Role).all()
        return render_template('admin/admin-user-view.html', user=user, roles=roles,datetime=datetime)
    
@require_live_session
def update_or_insert_user(session, user, request, login_id=None, is_temporary=False, role_id=None):
    """
    Method to edit (UPDATE) or create (INSERT) a user into the User ORM class. 
    PARAMETERS:
    - session: the current session object.
    - user: the user object (if INSERT the user object must already be made, but can be empty)
    - request: the HTTP request with form data for the user, containing name, password, role, expiry, login_id, is_active
    (see method for more details)
    - login_id (default None): override the login_id of the INSERT or UPDATE operation.
    - is_temporary (default False): to be set to True if it is a temporary user.
    - role_id (default None): override the role_id of the INSERT or UPDATE operation.
    RETURNS:
    Redirect page
    """
    if user:
        # Insert new data
        user.set_name(request.form['name'])
        user.set_password(request.form['password'])
        # Override the User object's role if passed as a parameter
        if role_id:
            user.set_role_id(role_id)
        else:
            user.set_role_id(request.form['role'])
        user.set_expiry(request.form['expiry'])
        user.is_temporary = is_temporary
        if login_id is not None:
            user.set_login_id(login_id)
        else:
            user.set_login_id(request.form['login_id'])
        is_active = False
        # This logic is required because is_active is a checkbox
        # so if it is not checked it will not appear in the HTTP request.
        if 'is_active' in request.form:
            is_active = True
        user.activate() if is_active else user.deactivate()
        session.commit()
        flash('User updated: {}'.format(user.get_login_id()), 'success')
    else:
        flash('User with ID {} not found'.format(user.id), 'error')
        session.rollback()
    return redirect(url_for('admin.admin_user'))
    
@routes_admin.route('/admin/user/<user_id>/update', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_user_update(user_id):
    """
    Route to complete an UPDATE operation on a User object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with Session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        return update_or_insert_user(session, user, request)
    
@routes_admin.route('/admin/user/new', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_user_new():
    """
    Route to show the page where the admin can add a new user.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    roles=database_handler.session.query(Role).all()
    default_date = datetime.now() + timedelta(days=365)

    return render_template('admin/admin-user-new.html',roles=roles,default_date=default_date)    

@routes_admin.route('/admin/user/insert', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_user_insert():
    """
    Route to insert a new user into the database through the User class.
    The data for the user should be given in a request. See update_or_insert_user()
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with Session() as session:
        user = User()
        session.add(user)
        return update_or_insert_user(session, user, request)
    
@routes_admin.route('/admin/user/temporary/new', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_temporary_user_new():
    """
    Route to show the page where the admin can add a new temporary user.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    default_date = datetime.now() + timedelta(days=30)
    return render_template('admin/admin-temporary-user-new.html',default_date=default_date)

@routes_admin.route('/admin/user/temporary/insert', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_temporary_user_insert():
    """
    Route to insert a new user into the database through the User class.
    The data for the user should be given in a request. See update_or_insert_user()
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with Session() as session:
        user = User()
        session.add(user)
        return update_or_insert_user(session, user, request, login_id=uuid.uuid4(), is_temporary=True, role_id=4)

@routes_admin.route('/admin/temporary-user/<user_id>/view', methods=['GET'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_temporary_user_view(user_id):
    """
    Route to view info on a particular User object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with Session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        roles = session.query(Role).all()
        return render_template('admin/admin-temporary-user-view.html', user=user, roles=roles,datetime=datetime)

@routes_admin.route('/admin/temporary-user/<user_id>/update', methods=['POST'])
@exclude_role_4
@exclude_role_3
@require_live_session
def admin_temporary_user_update(user_id):
    """
    Route to update an existing temporary user. Require a form with fields - see update_or_insert_user()
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with Session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        return update_or_insert_user(session, user, request, login_id=user.login_id, is_temporary=True, role_id=4)