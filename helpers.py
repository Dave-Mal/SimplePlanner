from functools import wraps
from flask import redirect, session
from datetime import date, timedelta, datetime


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/2.3.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") != 1:
            return redirect("/logout")
        return f(*args, **kwargs)
    return decorated_function


def kcal(value):
    """Format value as KCal."""
    return f"{value:,} KCal"


def gkg(value):
    if value < 1000:
        return f"{value:}g"
    else:
        return f"{float(value/1000):,.1f}Kg"


def date_format(value):
    months = ("January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December")
    month = months[value.month-1]
    return "{} {} {}".format(value.day, month, value.year)


def date_format_previousday(value):
    value = value - timedelta(days=1)
    months = ("January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December")
    month = months[value.month-1]
    return "{} {} {}".format(value.day, month, value.year)


def date_format_nextday(value):
    value = value + timedelta(days=1)
    months = ("January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December")
    month = months[value.month-1]
    return "{} {} {}".format(value.day, month, value.year)


def hrs_mins(value):
    if value < 60:
        return (f"{value} min")
    elif value % 60 == 0:
        return (f"{int(value / 60)} hr")
    else:
        return (f"{int(value / 60)} hr {value % 60} min")


def mifflin_st_jeor(weight, height, age, sex):
    if sex == 'm':
        # Mifflin-St Jeor to calculate RMR(Male)
        rmr = int((10 * weight) + (6.25 * height) - (5 * age) + 5)
        return rmr
    elif sex == 'f':
        # Mifflin-St Jeor to calculate RMR(Female)
        rmr = int((10 * weight) + (6.25 * height) - (5 * age) - 161)
        return rmr
    else:
        print("error in mifflin_st_jeor")
        return 1


def calculate_age(birthdate):
    days_in_year = 365.2425
    age = int((date.today() - datetime.strptime(birthdate,
              '%Y-%m-%d').date()).days / days_in_year)
    return age


def create_session(id, username, height, weight, sex, birthday):
    session["user_id"] = id
    session["username"] = username
    session["height"] = float(height)
    session["weight"] = int(weight)
    session["sex"] = sex
    session["birthday"] = birthday
    session["rmr"] = mifflin_st_jeor(session["weight"], session["height"], calculate_age(
        session["birthday"]), session["sex"])
    session["date"] = date.today()
    session["today"] = date.today()
    session["food_type"] = "%"
    session["meal_creation"] = []
    session["toasts"] = []



def index_toasts():
    x = 0
    for i in session["toasts"]:
        i["id"] = x
        x = x + 1
    return 0


def add_toast(message, type=0):
    # Add message to a dictionary
    this_toast = {
        "message": message,
        "type": type,           # 0 is a (red alert)
        "date": datetime.now().strftime("%a %d %b %Y %H:%M")
    }
    # Add dictionary to list in session
    session["toasts"].append(this_toast)

    index_toasts()
    return 0


def check_values(source, **kwargs):
    # kwargs dict
    # "string" - string values to check present
    # "zero" - numeric values to check are >= 0
    # "positive" - numeric valyes to check > 0
    result = {}
    errors = []
    err = 0
    if "string" in kwargs:
        for arg in kwargs["string"]:
            if not source[arg]:
                add_toast(f"{arg.title()} is required")
                err = 1
                errors.append(arg)
                continue
            else:
                result[arg] = source[arg].title()
                continue
    if "zero" in kwargs:
        for arg in kwargs["zero"]:
            if not source[arg]:
                add_toast(f"{arg.title()} can not be blank")
                err = 1
                errors.append(arg)
                continue
            try:
                result[arg] = float(source[arg])
            except:
                add_toast(
                    f"{source[arg]} is not a valid value for {arg.title()}")
                err = 1
                errors.append(arg)
                continue
            if result[arg] < 0:
                add_toast(
                    f"Please enter a value for {arg.title()} larger than 0")
                err = 1
                errors.append(arg)
    if "positive" in kwargs:
        for arg in kwargs["positive"]:
            if not source[arg]:
                add_toast(f"{arg.title()} can not be blank")
                err = 1
                errors.append(arg)
                continue
            try:
                result[arg] = float(source[arg])
            except:
                add_toast(
                    f"{source[arg]} is not a valid value for {arg.title()}")
                err = 1
                errors.append(arg)
                continue
            if result[arg] <= 0:
                add_toast(f"Please enter a positive value for {arg.title()}")
                err = 1
                errors.append(arg)
    if err == 0:
        return result
    else:
        raise ValueError(f"Errors found in the following values {errors}")


