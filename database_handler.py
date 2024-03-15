import MySQLdb
from flask_mysqldb import MySQL
import os

DATABASE = "test_database"
ALL = "*"
SPECIES = "species"
SPECIES_ATTRIBUTES = ["id","species_name","genus_name","common_name"]
ENCOUNTER = "encounter"
ENCOUNTER_ATTRIBUTES = ["id","encounter_name","location","species_id","origin","notes"]


class SQLError(MySQLdb.Error):

    def __init__(self, error: MySQLdb.Error):
        super().__init__()
        self.error = error

    def get_error_description(self):
        if type(self.error) == MySQLdb.IntegrityError:
            error_message = str(self.error)
            if "cannot be null" in error_message:
                column_name = error_message.split("Column '")[1].split("' cannot be null")[0]
                return "Error: {} cannot be null. Please provide a valid value for {}.".format(column_name, column_name)
            elif self.error.args[0] == 1062 and "Duplicate entry" in error_message:
                duplicate_value = error_message.split("Duplicate entry ")[1].split(" for key")[0]
                duplicate_attribute = error_message.split("for key '")[1].split("'")[0]
                return "Duplicate entry: {} for {}.".format(duplicate_value, duplicate_attribute)
            else:
                foreign_key_constraint = self.error.args[1].split('`')[3]
                print(self.error.args[1])
                return "Cannot delete or update a parent row: this data row is relied upon by an entity in '{}'.".format(foreign_key_constraint)
        elif type(self.error) == MySQLdb.OperationalError:
            return "Operational error occurred: {}.".format(self.error.args[1])
        elif type(self.error) == MySQLdb.ProgrammingError:
            return "Programming error occurred: {}.".format(self.error.args[1])
        else:
            return "An error occurred: {}.".format(self.error.args[1])

class DatabaseHandler:


    def __init__(self, mysql):
        self.mysql = mysql


    def selection_query(self, table, attributes, selection: list, filter: dict):
        """
        A method to execute a selection query on a specified table with given attributes, selection criteria, and filters.

        Parameters:
            - table (str): The name of the table to query.
            - attributes (list): List of attributes to select from the table.
            - selection (list): List of attributes to include in the selection.
            - filter (dict): Dictionary of filters to apply to the query.

        Returns:
            - result (list of tuples): The result set of the query.
        """

        values=[]

        if selection==ALL:
            selection=[ALL]
        elif len(selection)==0:
            selection=[ALL]
        elif not all(key in attributes for key in selection):
            raise ValueError("Invalid selection parameters for query")
        
        
        query = "SELECT {} FROM {}".format(", ".join(selection), table)

        if len(filter)>0:
            if all(key in list(attributes + [ALL]) for key in filter.keys()):
                query += " WHERE " + " AND ".join(["{} = %s".format(key) for key in filter.keys()])
                values.extend([value for value in filter.values()])
        query = query + ";"
        print(query,values)
        return query,values

    def update_query(self, table, update_values: dict, filter: dict):
        """
        A method to generate an update query for a specified table with given update values and filters.

        Parameters:
            - table (str): The name of the table to update.
            - update_values (dict): Dictionary of column-value pairs to update.
            - filter (dict): Dictionary of filters to apply to the update query.

        Returns:
            - query (str): The generated update query.
            - values (list): The values to be updated in the query.
        """
        values=[]
        query = "UPDATE {} SET {}".format(table, ", ".join(["{} = %s".format(key) for key in update_values.keys()]))
        # Replace empty/whitespace strings with None
        for value in list(update_values.values()):
            if value.strip() == '':
                values.append(None)
            else:
                values.append(value)
        print(filter)
        if len(filter) > 0:
            query += " WHERE " + " AND ".join(["{} = %s".format(key) for key in filter.keys()])
            values.extend([value for value in filter.values()])

        query += ";"
        print(query,values)
        return query, values
    
    def insert_query(self, table, insert_values: dict):
        columns = ", ".join(insert_values.keys())
        placeholders = ", ".join(["%s"] * len(insert_values))
        query = "INSERT INTO {} ({}) VALUES ({})".format(table, columns, placeholders)
        values = []

        # Replace empty/whitespace strings with None
        for value in insert_values.values():
            if value.strip() == '':
                values.append(None)
            else:
                values.append(value)

        # Fetching all column names from the database
        cursor = self.mysql.connection.cursor()
        cursor.execute("SHOW COLUMNS FROM {}".format(table))
        print(cursor.fetchall())
        columns_from_db = [column[0] for column in cursor.fetchall()]
        cursor.close()

        # Check for missing columns and add None for those columns
        for column in columns_from_db:
            if column not in insert_values:
                query = query.replace("({})".format(placeholders), "({}, {})".format(placeholders, "%s"))
                values.append(None)

        query += ";"
        return query, values
    
    def query_species_table_manual(self,query, values):
        try:
            cursor = self.mysql.connection.cursor()
            cursor.execute(query,values)
            result = cursor.fetchall()
            cursor.close()
        except MySQLdb.Error as e:
            raise SQLError(e)
        return result

    def query_species_table(self, selection=[], filter={},one_record=False):
        try:
            cursor = self.mysql.connection.cursor()
            if selection==ALL: selection=[]
            query,values=self.selection_query("test_database.species", SPECIES_ATTRIBUTES, selection, filter)
            if len(values)>0:
                cursor.execute(query,values)
            else:
                cursor.execute(query)

            result = cursor.fetchall()
            
            cursor.close()
            if one_record and len(result)>0:
                result = result[0]
        except MySQLdb.Error as e:
            raise SQLError(e)
        return result 
    
    def delete_query(self, table, filter: dict):
        """
        A method to generate a delete query for a specified table with given filters.

        Parameters:
            - table (str): The name of the table to delete from.
            - filter (dict): Dictionary of filters to apply to the delete query.

        Returns:
            - query (str): The generated delete query.
            - values (list): The values to be used in the query.
        """

        query = "DELETE FROM {}".format(table)
        values = []

        if len(filter) > 0:
            query += " WHERE " + " AND ".join(["{} = %s".format(key) for key in filter.keys()])
            values.extend([value for value in filter.values()])

        query += ";"
        return query, values
    
    def update_species_table(self, update_values, id):
        try:
            query, values = self.update_query("test_database.species", update_values, {"id":id})
            cursor = self.mysql.connection.cursor()
            cursor.execute(query, values)
            self.mysql.connection.commit()
        except MySQLdb.Error as e:
            cursor.close()
            raise SQLError(e)
        
        cursor.close()

    def insert_species_table(self, insert_values):
        try:
            query, values = self.insert_query("test_database.species", insert_values)
            cursor = self.mysql.connection.cursor()
            cursor.execute(query, values)
            self.mysql.connection.commit()
        except MySQLdb.Error as e:
            cursor.close()
            raise SQLError(e)
        cursor.close()

    def delete_species_table(self, id):
        try:
            query, values = self.delete_query("test_database.species", {"id":id})
            cursor = self.mysql.connection.cursor()
            cursor.execute(query, values)
            self.mysql.connection.commit()
        except MySQLdb.Error as e:
            cursor.close()
            raise SQLError(e)
        cursor.close()


    def insert_encounter_table(self, insert_values):
        try:
            query, values = self.insert_query("test_database.encounter", insert_values)
            cursor = self.mysql.connection.cursor()
            cursor.execute(query, values)
            self.mysql.connection.commit()
        except MySQLdb.Error as e:
            cursor.close()
            raise SQLError(e)
        cursor.close()
    
    def delete_encounter_table(self, id):
        try:
            query, values = self.delete_query("test_database.encounter", {"id":id})
            cursor = self.mysql.connection.cursor()
            cursor.execute(query, values)
            self.mysql.connection.commit()
        except MySQLdb.Error as e:
            cursor.close()
            raise SQLError(e)
        cursor.close()
    
    def update_encounter_table(self, update_values, id):
        try:
            query, values = self.update_query("test_database.encounter", update_values, {"id":id})
            cursor = self.mysql.connection.cursor()
            cursor.execute(query, values)
            self.mysql.connection.commit()
        except MySQLdb.Error as e:
            cursor.close()
            raise SQLError(e)
        cursor.close()
    
    def query_encounter_table(self, selection=[], filter={},one_record=False):
        try:
            cursor = self.mysql.connection.cursor()
            query,values=self.selection_query("test_database.encounter", ENCOUNTER_ATTRIBUTES, selection, filter)
            if selection==ALL: selection=[]

            if len(values)>0:
                cursor.execute(query,values)
            else:
                cursor.execute(query)

            result = cursor.fetchall()
            cursor.close()
            if one_record and len(result)>0:
                result = result[0]
        except MySQLdb.Error as e:
            raise SQLError(e)
        return result

    def query_encounter_table_manual(self,query, values):
        try:
            cursor = self.mysql.connection.cursor()
            cursor.execute(query,values)
            result = cursor.fetchall()
            cursor.close()
        except MySQLdb.Error as e:
            raise SQLError(e)
        return result

