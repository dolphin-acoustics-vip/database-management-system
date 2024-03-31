import re, uuid, zipfile, os
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from db import Session
import db
from models import *

routes_species = Blueprint('species', __name__)


@routes_species.route('/species/dashboard', methods=['GET'])
def species_dashboard():
    with Session() as session:
        try:
            species_data = session.query(Species).all()
            return render_template('species/species.html', species_list=species_data)
        except Exception as e:
            flash(str(e), 'error')


@routes_species.route('/species/<uuid:species_id>/view', methods=['GET'])
def species_view(species_id):
    """
    Edit and update species data based on the provided species ID.

    Parameters:
    - species_id: The UUID of the species to edit.

    Returns:
    - If the request method is POST and the species exists, updates the species data and redirects to '/species'.
    - If the species does not exist, flashes an error message and redirects to '/species'.
    - If the request method is not POST, renders the 'edit_species.html' template for editing.
    - In case of exceptions, rolls back the session, flashes an error message, and redirects to '/species'.
    """
    try:
        session = Session()
        species_data = session.query(Species).filter_by(id=species_id).first()
 
        return render_template('species/species-view.html', species=species_data)
    except Exception as e:
        session.rollback()
        flash(str(e), 'error')
        return redirect(url_for('species.species_dashboard'))
    finally:
        session.close()
    
    
@routes_species.route('/species/<uuid:species_id>/edit', methods=['POST'])
def species_edit(species_id):
    with Session() as session:
        species_data = session.query(Species).filter_by(id=species_id).first()

        if species_data:
            species_name = request.form['species_name']
            genus_name = request.form['genus_name']
            common_name = request.form['common_name']
            species_data.set_species_name(species_name)
            species_data.set_genus_name(genus_name)
            species_data.set_common_name(common_name)
            species_data.update_call(session)
            session.commit()
            #clean_up_root_directory(FILE_SPACE_PATH)
            flash('Species updated: {}'.format(species_name), 'success')
        else:
            flash('Species with ID {} not found'.format(species_id), 'error')
            session.rollback()
        return redirect(url_for('species.species_dashboard'))

# Update the route handler to use SQLAlchemy for deleting a species from the table
@routes_species.route('/species/<uuid:species_id>/delete', methods=['POST'])
def species_delete(species_id):
    try:
        with Session() as session:
            species = session.query(Species).filter_by(id=species_id).first()
            species_name = species.get_species_name()
            session.delete(species)
            session.commit()
            flash('Species deleted: {}'.format(species_name), 'success')
    except SQLAlchemyError as e:
        flash(str(e), 'error')
        session.rollback()
    return redirect(url_for('species.species_dashboard'))

    
@routes_species.route('/species/new', methods=['GET'])
def species_new():
    return render_template('species/species-new.html')

@routes_species.route('/species/insert', methods=['POST'])
def species_insert():
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
            flash(db.parse_alchemy_error(e), 'error')
            session.rollback()
    return redirect(url_for('species.species_dashboard'))

