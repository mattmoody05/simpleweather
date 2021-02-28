"""IMPORTS"""
# Importing flask modules
from flask import Flask, render_template, redirect, request, url_for, session

# Importing modules for obtaining data from various APIs
from pyowm.owm import OWM # OpenWeatherMap weather information
from geopy.geocoders import Nominatim # Used to get location names from long and lat
import requests # Used to make general API requests

# Importing modules for user authentication
from authlib.integrations.flask_client import OAuth

# Importing misc modules 
from json import load # Module to work with json data
from datetime import datetime # Module for getting date and time data
from functions.PostcodeManagement import get_user_postcodes, add_user_postcode



"""FLASK AND VARIOUS API CONFIG"""
# Pulling the config information from the config.json file
with open("config.json") as f:
    config = load(f)

# Getting a OWM instance using the API key pulled from the config file
owm = OWM(config["OWM-API-KEY"])

# Configuring 404 and 500 error pages
def error_pages(e):
    # Returning an error page with the correct error code passed through
    return render_template("flask-error.html", error=str(e)[:3])

# Configuring the flask instance
app = Flask(__name__)
app.register_error_handler(404, error_pages)
app.register_error_handler(500, error_pages)
app.secret_key = config["APP-SECRET-KEY"]
app.config["SESSION_COOKIE_NAME"] = config["SESSION-COOKIE-NAME"]

# Configuring oauth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=config["GOOGLE-OAUTH2-CLIENT-ID"],
    client_secret=config["GOOGLE-OAUTH2-CLIENT-SECRET"],
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  # This is only needed if using openId to fetch user info
    client_kwargs={'scope': 'openid email profile'},
)



"""FLASK ROUTES & PARTIAL LOGIC FOR NON USER WEATHER"""
# Route for the user to input their postcode
@app.route("/")
def postcode_entry():
    # Returning the postcodeselect.html page without modification
    return render_template("postcodeselect.html")


# Getting the postcode from the form via POST and obtaining the longitude and latitude from it, then redirecting the the weather page
@app.route("/", methods=["POST"])
def postcode_post():
    # Getting the user's postcode from the form 
    user_postcode = request.form["postcode"]

    # Getting data about the postcode from the postcodes.io API
    response = requests.get(f"http://api.postcodes.io/postcodes/{user_postcode}").json()

    # Checking that the API has returned a successful respose
    if response["status"] != 200:
        return render_template("general-error.html", main ="Postcode error!", detail="That postcode doesn't seem to be a valid UK postcode, please try again...")

    else:
        # Getting the user's logitude and latitude from the postcode data
        postcode_response = response['result']
        user_longitude = postcode_response["longitude"]
        user_latitude = postcode_response["latitude"]

        # Redirecting the to weather app, passing through the user's longitude and lattitude 
        return redirect(f"/app/{user_longitude}/{user_latitude}")


# Finding the weather and time data and returning it to the user
@app.route("/app/<long>/<lat>")
def weather_app(long, lat):
    # Getting the weather from OWM using the provided longitude and latitude
    HourlyForecastArray = owm.weather_manager().one_call(lat = float(lat), lon = float(long)).forecast_hourly

    # Getting location data from the longitude and latitude
    geolocator = Nominatim(user_agent="geoapiExercises")
    address = geolocator.reverse(f"{lat},{long}").raw["address"]

    # Creating an array with the correct hours for the weather
    hourarray = [None] * 7
    for i in range(7):
        if datetime.now().hour + i > 23:
            hourarray[i] = f"{str(datetime.now().hour + i - 24)}:00"
        else: 
            hourarray[i] = f"{str(datetime.now().hour + i)}:00"

    # Returning the webpage, populated with the correct weather data
    return render_template("weatherapp.html", weatherdata = HourlyForecastArray, hourdata = hourarray, address=address)



"""FLASK ROUTES AND PARTIAL LOGIC FOR LOGGING IN / LOGGING OUT"""
# Redirecting the user to Google oauth page
@app.route("/login")
def login():
    google = oauth.create_client('google')
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


# Getting the user info from Google and storing it in a session cookie
@app.route('/authorize')
def authorize():
    # Creating the oauth client and getting the access token from Google
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    
    # Getting the user info from Google
    resp = google.get('userinfo')
    user_info = resp.json()
    user = oauth.google.userinfo()

    # Creating the session cookie with the user's info
    session['profile'] = user_info
    session.permanent = True  # make the session permanant so it keeps existing after broweser gets closed
    
    # Redirecting the user to their postcode page
    return redirect(url_for("user"))


# Route for logging the user out, deleting the session data
@app.route("/logout")
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect("/")



"""FLASK ROUTES AND PARTIAL LOGIC FOR THE USER'S SAVED POSTCO"""
# Route for user's page
@app.route("/user")
def user():
    # Check to see if the user has logged in, if not, redirecting them to the user
    if not session:
        return redirect(url_for("login"))
    else:
        # Gets the auth cookie, and returns the correct user profile page
        user_email = dict(session)['profile']['email']
        user_postcodes = get_user_postcodes(user_email)
        
        return render_template("userpage.html", user_postcodes=user_postcodes, email=user_email)


# postcode selected post from /user
@app.route("/user", methods=["POST"])
def user_post():
    # Getting the button press from the form
    button_data = request.form['button']

    # Checking if the button press was to logout
    if button_data == "logout":
        return redirect(url_for("logout"))
    
    # Checking to see if the button press was to add a new postcode
    elif button_data == "addpostcode":
        # Getting the postcode from the webpage and converting it to upper
        postcode = request.form["entered-postcode"]
        postcode = postcode.upper()
        
        # Calling the fucntion to add a new postcode to the database
        postcode_add_stauts = add_user_postcode(dict(session)['profile']['email'], postcode)

        if postcode_add_stauts == None:
            # Re-rendering the page with the new postcode added
            return redirect(url_for("user"))
        else:
            return render_template("general-error.html", main ="Postcode error!", detail="That postcode doesn't seem to be a valid UK postcode, please try again...")

    # This will only happen if a postcode has been clicked
    else:
        # Getting data about the postcode from the postcodes.io API
        postcode_response = requests.get(f"http://api.postcodes.io/postcodes/{button_data}").json()['result']
        
        # Getting the user's logitude and latitude from the postcode data
        user_longitude = postcode_response['longitude']
        user_latitude = postcode_response['latitude']

        # Redirecting the to weather app, passing through the user's longitude and lattitude 
        return redirect(f"/app/{user_longitude}/{user_latitude}")



"""RUNNING THE FLASK APP"""
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0") 