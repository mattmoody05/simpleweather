"""Various imports"""
import sqlite3 # Module for using an SQLite database
import json # Module for working with json data
import requests # Module for making API requests



"""Function for getting all of the user's postcodes stored in the database"""
def get_user_postcodes(email):
    # Connecting to the database
    conn = sqlite3.connect("./databases/userdata.db")
    cursor = conn.cursor()

    # Fetching the user data for the specified email in the database, and creating the userdata table if there is not one already
    cursor.execute("CREATE TABLE IF NOT EXISTS userdata (email TEXT, postcodes TEXT)")
    cursor.execute('SELECT * FROM userdata WHERE email=?', [email])
    userdata = cursor.fetchall()
    
    # Checking that a matching email has been found in the database
    if not userdata:

        # Inserting the template data into the database, including the user's email
        cursor.execute("INSERT INTO userdata VALUES (?, ?)", [email, '{ "postcodes" : [] }'])
        cursor.execute("COMMIT")

        # Fetching the user data for the specified email in the database
        cursor.execute('SELECT * FROM userdata WHERE email=?', [email])
        userdata = cursor.fetchall()

        # Returning a list of the user's postcodes from the database    
        user_postcodes = json.loads(userdata[0][1])
        user_postcodes = user_postcodes['postcodes']
        return user_postcodes

    else:

        # Returning a list of the user's postcodes from the database    
        user_postcodes = json.loads(userdata[0][1])
        user_postcodes = user_postcodes['postcodes']
        return user_postcodes



"""Function for updating the postcodes that are stored in the database"""
def add_user_postcode(email, postcode):
    # Checking if the postcode is valid
    if verify_postcode(postcode):
        # Connecting to the database
        conn = sqlite3.connect("./databases/userdata.db")
        cursor = conn.cursor()

        # Getting the current postcodes from the database
        cursor.execute("SELECT * FROM userdata WHERE email=?", [email])
        userdata = cursor.fetchall()

        # Updating the json data storing the postcodes
        user_postcodes = json.loads(userdata[0][1])
        user_postcodes['postcodes'].append(postcode)
        new_json = json.dumps(user_postcodes)

        # Writing the new json data to the database
        cursor.execute("UPDATE userdata SET postcodes=? WHERE email=?", [new_json, email])
        cursor.execute("COMMIT")
    
    else:
        return "postcode_not_valid_fail"




"FUNCTION TO CHECK IF THE POSTCODE IS VALID"
def verify_postcode(postcode):
    response = requests.get(f"http://api.postcodes.io/postcodes/{postcode}").json()
    print(response)
    if response['status'] != 200:
        return False
    else:
        return True