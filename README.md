# SimplePlanner
#### Video Demo:  <URL HERE>
#### Description: CS50x final project SimplePlanner, a quick and simple diet and activity tracker
#### The goal in the creation of the system was to:
>*Allow the tracking of calorific intake and expendature without the headache.*

From this idea, the main goals were to:
- Simplify tracking the nutritional value of home cooked meals
- Avoid going into the weeds around the subject
- Remove information not needed for the average user of a diet tracking system
- Give a general awareness of how balanced a user's activity and diet are


### Technology
My CS50x project utilises Python, Flask, SQLITE3 and HTML to create a diet and activity tracker website.


# Python
## Imported Modules

Imported to aid the function of the system

|Module|Useage|Ref|
|:---|:---|:---|
|datetime|Used to manipulate date types|[python.org](https://docs.python.org/3/library/datetime.html)|
|flask|Used to create a flask app|[flask.palletsprojects.com](https://flask.palletsprojects.com/en/2.3.x/api/#flask.Flask)|
|flask_session|Allows the creation of a temporary flask session|[flask-session.readthedocs.io](https://flask-session.readthedocs.io/en/latest/)|
|werkzeug.security|Used the encryption tool to create and login system|[werkzeug.palletsprojects.com](https://werkzeug.palletsprojects.com/en/2.3.x/utils/#module-werkzeug.security)|
|sqlite3|To enable connection and communication to an SQLITE3 database|[sqlite.org](https://www.sqlite.org/index.html)|
|functools|To create a wrapper to secure access to web pages to specific user types|[python.org](https://docs.python.org/3/library/functools.html)|


## helpers.py
Functions created in **helpers.py** to aid the core functionality of the system. The operation of these are detailed below.

### dict_factory()

#### Description
Used to configure the db.cursor() to return sql output as a list of dictionaries (key=column name)

#### Usage
```python
# Connect to database
db = sqlite3.connect("data.db", check_same_thread=False)
db.row_factory = helpers.dict_factory
```

### kcal()

#### Description

Used in Jinja to format values as KCal

#### Useage
```python
# returns '100 KCal'
kcal(100)

# returns '1,100 KCal'
kcal(1100)
```

### gkg()

#### Description

Used in Jinja code to format weights in g and Kg

#### Useage
```python
# returns '100g'
gkg(100)

# returns '1Kg'
gkg(1000)

# returns '2.2Kg'
gkg(2200)

# returns '1,000Kg'
gkg(1000000)
```

### date_format(), date_format_previousday(), date_format_nextday()

#### Description

Used in Jinja code to display formatted dates

#### Useage
```python
# returns 1 January 2023
date_format(2023-1-1) # variable as date type

# returns 31 December 2022
date_format_previousday(2023-1-1) # variable as date type

# returns 2 January 2023
date_format_nextday(2023-1-1) # variable as date type
```

### hrs_mins()

#### Description
Used in Jinja code to convert an integer (time in mins) to a string to help format the data in a user friendly way.

One argument is required - an Integer.

#### Useage
```python
# returns '50 min'
hrs_mins(50)

# returns '1 hr'
hrs_mins(60)

# returns '1 hr 30 min'
hrs_mins(90)
```

### mifflin_st_jeor()

#### Description
Calculates a persons daily energy expenditure using weight (Kg), height (cm), age (years) and sex (m/f).

Reference: [Medscape.com](https://reference.medscape.com/calculator/846/mifflin-st-jeor-equation)

#### Useage
```python
mifflin_st_jeor(weight, height, age, sex)

# returns '1780'
mifflin_st_jeor(80, 180, 30, 'm')

# returns '1614'
mifflin_st_jeor(80, 180, 30, 'f')
```

### calculate_age()

#### Description

Used to calculate a person's age from a given birthdate

#### Useage
```python
# As of November 2023 returns 30
calculate_age(1990-5-20) # variable as date type
```

### create_session()

#### Description
Uses [Flask.Sessions](https://flask.palletsprojects.com/en/2.3.x/api/#sessions) to build a session/dictionary object for the logged in user

#### Useage
```python
# returns session[] object for logged in user
create_session(id, username, height, weight, sex, birthday)
```

### index_toasts()

#### Description
Re-indexes the toast dectionary objects held in session["toasts"]

Adds an incremental value for each session["toasts"]["id"] value

#### Useage
```python
# returns 0
index_toasts()
```

### add_toast()

#### Description
Used to create [toast popups](https://getbootstrap.com/docs/5.0/components/toasts/)

Appends a new dictionary object to session["toast"] containing the data needed to render a toast via Jinja in HTML

The datetime is set using datetime.now() - current date/time is used

Jinja logic is used to create any toast with type=0 as a warning message, any others are standard alerts.

#### Useage
```python
add_toast(message, type=0)

# Assumiung today is the 6th July 2023 at 10:46

# adds {"message": "hi", "type": 0, "date": Thu 6 July 2023 10:46} to session["toast"]
add_toast("hi")

# adds {"message": "hi", "type": 1, "date": Thu 6 July 2023 10:46} to session["toast"]
add_toast("hi", 1)
```

### check_values()

#### Description
Checks values returned from a HTML POST event are valid as required to be processed

Checks performed:
- Are strings present
- Are "zero" values numeric and >= 0
- Are "positive" values > 0

POST values passed as a dictionary -> source:

    request.form.to_dict(flat=True)

All values are checked, if an error is found the 'err' flag is set to 1

Errors create a toast message with appropriate description

If no errors are found err == 0 and all values are returned in a dictionary

#### Useage
```python
check_values(source, **kwargs)

# Checks ["name"] as a string
# Checks ["energy", "protien", "carbohydrate", "fat"] as being 0 or larger
# Checks ["amount"] as being positive

# returns dictionary containing key (**kwargs) values (data from source)
check_values(request.form.to_dict(flat=True), string=["name"], zero=["energy", "protien", "carbohydrate", "fat"], positive=["amount"])
```

# Sqlite3

### data.db

#### Description
A simple database used to store user, catalog and user submitted data.

The python code calls SQL commands to retrieve data from the database, processes the data and serve it to HTML webpages using Jinja. 

Data passed back to Python via POST commands is then processed in Python and the database is updated via SQL.

The layout of the database is described below:

|Table|Use|
|:---|:---|
|users|Store user information|
|weight|Track changes in a user's weight|
|standard_food|Store standard food items avaliable to all users|
|custom_food|Store user created food items|
|food_type|Store a list of types of food|
|consumption|Track food consumption|
|standard_exercises|Store standard exercises and their energy use avaliable to all users|
|activity|Track activity/energy expenditure|


# HTML with Jinja
Making use of the [Jinja Template syntax](https://jinja.palletsprojects.com/en/3.0.x/templates/) to create a standard for all other pages to be called witin. 

The [Bootstrap 5.1](http://getbootstrap.com/docs/5.1/) framework was used to provide navigation, functionality and design.

#### A brief descritpion of the HTML pages created can be found below
|*.html|Use|
|:---|:---|
|layout.html|Template HTML file containing  navigation, notification(Toast) & user information bar|
|index.html|Pre-login page|
|login.html|Basic user login form|
|register.html|Basic user registration form|
|overview.html|A page summarising all the data provided by a user|
|diet_diary.html|A page to input manage food cosumption and the food catalog|
|diet_mealcreation.html|A page to create meals using the food items in the catalog|
|exercise_diary.html|A page to input manage activities and calorific expenditure|
|admin_users.html|An admin page to manage user accounts|
|admin_user_deleted.html|A user deletion confirmation page|
|admin_food.html|An admin page to manage the standard food catalog|
|admin_exercises.html|An admin page to manage the exercise catalog|

## Continued Development
### Further useability improvements
Work on simplifying the interations with the system, making it a "more natural" and "instictive" proces to log both diet and activity

### Further analysis of data
Graphs to show:
- Showing BMI ranges
- Showing calorific defecit and the projected implact on bodymass


