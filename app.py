from datetime import date, timedelta, datetime
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import helpers

# Configure application
app = Flask(__name__)
app.config["SESSION_TYPE"] = 'filesystem'
app.config["SESSION_PERMANENT"] = False
Session(app)

# Custom filters
app.jinja_env.filters["kcal"] = helpers.kcal
app.jinja_env.filters["gkg"] = helpers.gkg
app.jinja_env.filters["date_format"] = helpers.date_format
app.jinja_env.filters["date_format_previousday"] = helpers.date_format_previousday
app.jinja_env.filters["date_format_nextday"] = helpers.date_format_nextday
app.jinja_env.filters["hrs_mins"] = helpers.hrs_mins

# Connect to database
db = sqlite3.connect("data.db", check_same_thread=False)
db.row_factory = helpers.dict_factory

# Homepage to show users not logged in
@app.route("/")
def index():
    if session:
        return redirect("/overview")
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", failure="Unable to log in, a username must be provided")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", failure="Unable to log in, a password must be provided")

        # Query database for username
        cur = db.cursor()
        user = cur.execute("SELECT * FROM users WHERE username = ?",
                           (request.form.get("username"), )).fetchone()

        # Ensure username exists and password is correct
        if not user or not check_password_hash(user["hash"], request.form.get("password")):
            return render_template("login.html", failure="Unable to log in, invalid username and/or password")

        # Remember which user has logged in
        helpers.create_session(user["id"], user["username"], user["height"],
                               user["weight"], user["sex"], user["birthday"])

        # Sucessful login - Redirect user to overview page
        return redirect("/overview")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    username_length = 5
    if request.method == "POST":
        # Check Username meets basic requirements
        if not (request.form.get("username")):
            return render_template("register.html", failure="Please enter a username")

        if len(request.form.get("username")) < username_length:
            return render_template("register.html", failure=f"A username must be at least {username_length} characters")

        if " " in request.form.get("username"):
            return render_template("register.html", failure="A username must be a single word")

        # Check height & weight given are valid
        try:
            height = float(request.form.get("height"))
        except:
            return render_template("register.html", failure="Height must be a number")

        if height <= 0:
            return render_template("register.html", failure="Height must be a positive number")

        try:
            weight = float(request.form.get("weight"))
        except:
            return render_template("register.html", failure="Weight must be a number")

        if weight <= 0:
            return render_template("register.html", failure="Height must be a positive number")

        # Check password and confirmation pressent & match
        if not (
            (request.form.get("password"))
            and (request.form.get("confirmation"))
            and ((request.form.get("password")) == (request.form.get("confirmation")))
        ):
            return render_template("register.html", failure="Passwords do not match")

        # Check Username not already in users table
        cur = db.cursor()
        rows = cur.execute("SELECT * FROM users WHERE username = ?",
                           (request.form.get("username"), )).fetchall()
        if len(rows) > 0:
            return render_template("register.html", failure="Username already registered")

        # Insert username and password hash into users table
        cur = db.cursor()
        cur.execute("""INSERT INTO users (username, hash, weight, height, sex, birthday) 
                        VALUES (?, ?, ?, ?, ?, ?)""", (request.form.get("username"), generate_password_hash(request.form.get("password")), weight, height, request.form.get("sex"), request.form.get("birthday")))
        db.commit()
        user = cur.execute("SELECT * FROM users WHERE id = ?",
                           (cur.lastrowid, )).fetchone()
        helpers.create_session(user["id"], user["username"], user["height"],
                               user["weight"], user["sex"], user["birthday"])
        cur.close()

        # Insert weight into weight table
        cur = db.cursor()
        cur.execute("INSERT INTO weight (user_id, date, weight) VALUES (?, ?, ?)", ((
            session["user_id"]), date.today(), session["weight"]))
        db.commit()
        cur.close()

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/account")
@helpers.login_required
def account():
    return render_template("account.html")

# Overview page for users
@app.route("/overview")
@helpers.login_required
def overview():
    # Retrieve data from the database for diet, weight and activity to combine and display as anoverview
    cur = db.cursor()
    daily_diet = cur.execute("""SELECT date, sum(amount) AS amount, sum(energy) AS energy, sum(protein) AS protein, sum(carbohydrate) AS carbohydrate, sum(fat) AS fat
                            FROM consumption 
                            WHERE user_id = ?
                            GROUP BY date
                            ORDER BY date DESC
                            LIMIT 7""", (session["user_id"], )).fetchall()
    monthly_diet = cur.execute("""SELECT STRFTIME("%Y-%m", date) AS month, avg(amount) AS amount, avg(energy) AS energy, avg(protein) AS protein, avg(carbohydrate) AS carbohydrate, avg(fat) AS fat
                            FROM (SELECT date, sum(amount) AS amount, sum(energy) AS energy, sum(protein) AS protein, sum(carbohydrate) AS carbohydrate, sum(fat) AS fat
                            FROM consumption 
                            WHERE user_id = ?
                            GROUP BY date)
                            GROUP BY month
                            ORDER BY month DESC""", (session["user_id"], )).fetchall()
    daily_weight = cur.execute(
        "SELECT * FROM weight where user_id = ?", (session["user_id"], )).fetchall()
    monthly_weight = cur.execute(
        "SELECT STRFTIME('%Y-%m', date) AS month, AVG(weight) AS weight FROM weight WHERE user_id = ?  GROUP BY month", (session["user_id"], )).fetchall()
    daily_activity = cur.execute(
        "SELECT date, sum(energy) AS energy FROM activity WHERE user_id = ? GROUP BY date ORDER BY date DESC LIMIT 7", (session["user_id"], )).fetchall()
    monthly_activity = cur.execute(
        "SELECT STRFTIME('%Y-%m', date) AS month, AVG(energy) AS energy FROM activity WHERE user_id = ?  GROUP BY month", (session["user_id"], )).fetchall()
    cur.close()

    # If activity or diet information is not in the database, return without the data
    if not daily_activity or not daily_diet:
        return render_template("overview.html")

    # Combine diet, weight and activity data together
    for day in daily_diet:
        for x in daily_weight:
            if day["date"] >= x["date"]:
                day["weight"] = x["weight"]
            elif 'weight' not in day:
                day["weight"] = x["weight"]
        day["rmr"] = helpers.mifflin_st_jeor(day["weight"], session["height"], helpers.calculate_age(
            session["birthday"]), session["sex"])
        day["basic_maint"] = day["rmr"] * 1.2
        for y in daily_activity:
            if not any(day["date"] == y["date"] for day in daily_diet):
                daily_diet.append({"date": y["date"], "amount": 0, "energy": 0,
                                   "protein": 0, "carbohydrate": 0, "fat": 0})
            if day["date"] == y["date"]:
                day["energy_out"] = y["energy"]
            elif "energy_out" not in day:
                day["energy_out"] = 0

    daily_diet = sorted(daily_diet, key=lambda d: d["date"], reverse=True)

    for day in daily_diet:
        day["date"] = datetime.strptime(
            day["date"], '%Y-%m-%d').strftime("%a %d %b %Y")

    for month in monthly_diet:
        for x in monthly_weight:
            if month["month"] >= x["month"]:
                month["weight"] = x["weight"]
            elif 'weight' not in month:
                month["weight"] = x["weight"]
        month["rmr"] = helpers.mifflin_st_jeor(month["weight"], session["height"], helpers.calculate_age(
            session["birthday"]), session["sex"])
        month["basic_maint"] = month["rmr"] * 1.2
        for y in monthly_activity:
            if not any(month["month"] == y["month"] for month in monthly_diet):
                monthly_diet.append(
                    {"month": y["month"], "amount": 0, "energy": 0, "protein": 0, "carbohydrate": 0, "fat": 0})
            if month["month"] == y["month"]:
                month["energy_out"] = y["energy"]
            elif "energy_out" not in month:
                month["energy_out"] = 0

    monthly_diet = sorted(monthly_diet, key=lambda d: d["month"], reverse=True)

    for month in monthly_diet:
        month["month"] = datetime.strptime(
            month["month"], '%Y-%m').strftime("%b %Y")

    return render_template("overview.html", daily=daily_diet, monthly=monthly_diet)


# Adds user created food item into the custom_food table
@app.route("/customfood", methods=["GET", "POST"])
@helpers.login_required
def custom_food():
    if request.method == "POST":
        # Validate values
        try:
            values = helpers.check_values(request.form.to_dict(flat=True), string=["name"], zero=[
                "energy", "protein", "carbohydrate", "fat"], positive=["amount"])
        except Exception as e:
            print(f"/customfood ERROR: {e}")
            pass
        else:
            # Insert into custom_food table
            energy = round(values["energy"] / values["amount"] * 100, 2)
            protein = round(values["protein"] / values["amount"] * 100, 2)
            carbs = round(values["carbohydrate"] / values["amount"] * 100, 2)
            fat = round(values["fat"] / values["amount"] * 100, 2)
            cur = db.cursor()
            if cur.execute("INSERT INTO custom_food (user_id, food_name, food_type_id, energy, protein, carbohydrate, fat) VALUES (?, ?, ?, ?, ?, ?, ?)", (session["user_id"], request.form.get("name").title(), request.form.get("food_type"), energy, protein, carbs, fat)).rowcount == 1:
                helpers.add_toast(
                    f"{request.form.get('name').title()} created and added as a custom food item", 1)
                db.commit()
            else:
                helpers.add_toast(
                    f"Food not added to database, please try again")
            cur.close()
            session["meal_creation"] = []
        return redirect(request.referrer)

    # else:
    #     cur = db.cursor()
    #     custom_foods = cur.execute("SELECT custom_food.id, custom_food.food_name, custom_food.energy, custom_food.protein, custom_food.carbohydrate, custom_food.fat, food_type.type, food_type.id AS food_type_id FROM custom_food INNER JOIN food_type ON custom_food.food_type_id = food_type.id WHERE custom_food.user_id = ? ORDER BY food_name", ((
    #         session["user_id"]), )).fetchall()
    #     food_types = cur.execute(
    #         "SELECT * FROM food_type ORDER BY type").fetchall()
    #     cur.close()
    #     return render_template("diet_foodcreation.html", custom_foods=custom_foods, food_types=food_types)

# Removes user created food item from the custom_food table
@app.route("/removecustomfood", methods=["POST"])
@helpers.login_required
def remove_custom_food():
    cur = db.cursor()
    item = cur.execute("SELECT * FROM custom_food WHERE id = ?",
                       (request.form.get("id"), )).fetchone()
    if item:
        if cur.execute("DELETE FROM custom_food WHERE id = ?", (request.form.get("id"), )).rowcount == 1:
            helpers.add_toast(
                f"{item['food_name']} removed as a custom food item", 1)
    else:
        helpers.add_toast(
            "Food item not removed, please refresh and try again")
    db.commit()
    cur.close()
    return redirect(request.referrer)


# Allows a user to update their weight
@app.route("/updateweight", methods=["POST"])
@helpers.login_required
def update_weight():
    err = 0
    # Updates the user's recorded weight - if an update has already been logged today, the weight for that change is updated.
    try:
        values = helpers.check_values(request.form.to_dict(
            flat=True), positive=["weight"])
    except Exception as e:
        print(f"/updateweight ERROR: {e}")
    else:
        session["weight"] = values["weight"]
        cur = db.cursor()
        # Check if a weight update for the user has already been logged today
        # If entry for the user today is already present - update the weight field in that record
        if cur.execute("SELECT * FROM weight WHERE user_id = ? and date = ?", ((session["user_id"]), date.today())).fetchone():
            if cur.execute("UPDATE weight SET weight = ? WHERE user_id = ? AND date = ?", ((session["weight"]), (session["user_id"]), date.today())).rowcount != 1:
                helpers.add_toast(
                    f"Weight not updated, please try again, check {session['weight']} is a valid value")
                err = 1

        # If no update for today has been logged - create a new record
        else:
            if cur.execute("INSERT INTO weight (user_id, date, weight) VALUES (?, ?, ?)", ((session["user_id"]), date.today(), session["weight"])).rowcount != 1:
                helpers.add_toast(
                    f"Weight not updated, please try again, check {session['weight']} is a valid value")
                err = 1

        # If no update errors - Update the current weight in the user table
        if err == 0:
            cur.execute("UPDATE users SET weight = ? WHERE id = ?",
                        (session["weight"], session["user_id"]))
            helpers.add_toast(f"Weight updated to {session['weight']}Kg", 1)
        db.commit()
        cur.close()
    finally:
        return redirect(request.referrer)


### USER DIET DIARY & FUNCTIONS###

# Renders the "/diet_diary" page and allows diet items to be added
@app.route("/diet_diary", methods=["GET", "POST"])
@helpers.login_required
def diet_diary():
    # Add consumed food into the consumption table
    if request.method == "POST":
        try:
            values = helpers.check_values(request.form.to_dict(flat=True), string=["name"], zero=[
                "energy", "protein", "carbohydrate", "fat"], positive=["amount"])
        except Exception as e:
            print(f"/diet_diary ERROR: {e}")
            pass
        else:
            energy = round(values["energy"] * values["amount"] / 100, 2)
            protein = round(values["protein"] * values["amount"] / 100, 2)
            carbs = round(values["carbohydrate"] * values["amount"] / 100, 2)
            fat = round(values["fat"] * values["amount"] / 100, 2)
            cur = db.cursor()
            cur.execute("INSERT INTO consumption (user_id, date, food_name, amount, energy, protein, carbohydrate, fat) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (session["user_id"], session["date"], request.form.get("name"), request.form.get("amount"), energy, protein, carbs, fat))
            db.commit()
            cur.close()
        return redirect(request.referrer)

    # Produce the "/diet_diary" page
    else:
        cur = db.cursor()
        consumption = cur.execute("SELECT * FROM consumption WHERE user_id = ? AND date = ?",
                                  ((session["user_id"], session["date"]))).fetchall()
        foods = cur.execute("""SELECT standard_food.id, standard_food.food_name, standard_food.energy, standard_food.protein, standard_food.carbohydrate, standard_food.fat, food_type.type, food_type.id AS food_type_id 
                            FROM standard_food
                            INNER JOIN food_type ON standard_food.food_type_id = food_type.id
                            WHERE food_type_id LIKE ?
                            UNION
                            SELECT custom_food.id, custom_food.food_name, custom_food.energy, custom_food.protein, custom_food.carbohydrate, custom_food.fat, food_type.type, food_type.id AS food_type_id 
                            FROM custom_food INNER JOIN food_type ON custom_food.food_type_id = food_type.id 
                            WHERE food_type.id LIKE ?
                            AND custom_food.user_id = ?
                            ORDER BY food_name""", ((session["food_type"]), (session["food_type"]), (session["user_id"]))).fetchall()

        food_types = cur.execute(
            "SELECT * FROM food_type ORDER BY type").fetchall()
        cur.close()
        return render_template("diet_diary.html", consumption=consumption, foods=foods, food_types=food_types)

# Remove an item from the diet
@app.route("/remove_diet_item", methods=["POST"])
@helpers.login_required
def remove_from_diet():
    cur = db.cursor()
    cur.execute("DELETE FROM consumption WHERE id = ?",
                (request.form.get("consumption_id"), ))
    db.commit()
    cur.close()
    return redirect(request.referrer)

### MEAL CREATION PAGE AND ASSOCIATED FUNCTIONS ###

@app.route("/mealcreation", methods=["GET", "POST"])
@helpers.login_required
def meal_creation():
    if request.method == "POST":
        return redirect("/mealcreation")
    else:
        cur = db.cursor()
        # Retrieve all standard foods from the database along with any custom foods added by the session user which are not meals
        foods = cur.execute("""SELECT standard_food.id, standard_food.food_name, standard_food.energy, standard_food.protein, standard_food.carbohydrate, standard_food.fat, food_type.type, food_type.id AS food_type_id 
                            FROM standard_food
                            INNER JOIN food_type ON standard_food.food_type_id = food_type.id
                            WHERE food_type_id LIKE ?
                            UNION
                            SELECT custom_food.id, custom_food.food_name, custom_food.energy, custom_food.protein, custom_food.carbohydrate, custom_food.fat, food_type.type, food_type.id AS food_type_id 
                            FROM custom_food INNER JOIN food_type ON custom_food.food_type_id = food_type.id 
                            WHERE food_type.id LIKE ?
                            AND custom_food.user_id = ?
                            ORDER BY food_name""", ((session["food_type"]), (session["food_type"]), (session["user_id"]))).fetchall()

        food_types = cur.execute(
            "SELECT * FROM food_type ORDER BY type").fetchall()
        food_types_meal = cur.execute(
            "SELECT * FROM food_type WHERE type ='Meal'").fetchall()
        cur.close()
        return render_template("diet_mealcreation.html", standard_foods=foods, food_types_meal=food_types_meal, food_types=food_types, build_custom_food=session["meal_creation"])

# Adds ingredients as a dictionary to a list to create a meal
@app.route("/build_meal", methods=["POST"])
@helpers.login_required
def build_meal():
    item = {}
    item["food_name"] = request.form.get("food_name")
    item["amount"] = float(request.form.get("amount"))
    item["energy"] = float(request.form.get("energy")) * \
        float(request.form.get("amount")) / 100
    item["protein"] = float(request.form.get("protein")) * \
        float(request.form.get("amount")) / 100
    item["carbohydrate"] = float(request.form.get(
        "carbohydrate")) * float(request.form.get("amount")) / 100
    item["fat"] = float(request.form.get("fat")) * \
        float(request.form.get("amount")) / 100
    session["meal_creation"].append(item)
    x = 0
    for i in session["meal_creation"]:
        i["id"] = x
        x = x + 1
    return redirect("/mealcreation")

# Removes ingredients from a dictionary to a list
@app.route("/build_meal_remove", methods=["POST"])
@helpers.login_required
def build_meal_remove():
    del session["meal_creation"][int(request.form.get("id"))]
    x = 0
    for i in session["meal_creation"]:
        i["id"] = x
        x = x + 1
    return redirect("/mealcreation")


### EXERCISE DIARY AND ASSOCIATED FUNCTIONS ###
@app.route("/exercise_diary")
@helpers.login_required
def exercise_diary():
    cur = db.cursor()
    exercises = cur.execute(
        "SELECT * FROM standard_exercises ORDER BY exercise_name, energy_burn_factor").fetchall()
    activities = cur.execute("SELECT * FROM activity WHERE user_id = ? AND date = ?",
                             (session["user_id"], session["date"])).fetchall()
    cur.close()
    return render_template("exercise_diary.html", exercises=exercises, activities=activities)

# Add an exercise to the activity table to track a user's activity
@app.route("/activity_add", methods=["POST"])
@helpers.login_required
def activity_add():
    try:
        values = helpers.check_values(request.form.to_dict(
            flat=True), zero=["id"], positive=["time"])
    except Exception as e:
        print(f"/activity_add ERROR: {e}")
        pass
    else:
        cur = db.cursor()
        exercise = cur.execute(
            "SELECT * FROM standard_exercises WHERE id = ?", (values["id"], )).fetchone()
        energy = session["weight"] * \
            exercise["energy_burn_factor"] * (values["time"] / 60)
        cur.execute("""INSERT INTO activity (user_id, date, exercise_name, intensity, time, energy)
                    VALUES (?, ?, ?, ?, ?, ?)""", (session["user_id"], session["date"], exercise["exercise_name"], exercise["intensity"], values["time"], energy))
        db.commit()
        cur.close()
    return redirect(request.referrer)

# Add an adtivity not present in the exercise catalog
@app.route("/activity_custom_add", methods=["POST"])
@helpers.login_required
def activity_custom_add():
    try:
        values = helpers.check_values(request.form.to_dict(flat=True), string=[
            "name"], positive=["time", "energy"])
    except Exception as e:
        print(f"/activity_custom_add ERROR: {e}")
        pass
    else:
        cur = db.cursor()
        cur.execute("""INSERT INTO activity (user_id, date, exercise_name, intensity, time, energy)
                    VALUES (?, ?, ?, ?, ?, ?)""", (session["user_id"], session["date"], values["name"], request.form.get("intensity"), values["time"], values["energy"]))
        db.commit()
        cur.close()
    return redirect(request.referrer)

# Remove an activity previously logged in the activity table
@app.route("/activity_remove", methods=["POST"])
@helpers.login_required
def activity_remove():
    try:
        values = helpers.check_values(request.form.to_dict(
            flat=True), positive=["activity_id"])
    except Exception as e:
        print(f"/activity_custom_add ERROR: {e}")
        pass
    else:
        cur = db.cursor()
        cur.execute("DELETE FROM activity WHERE id = ?",
                    (values["activity_id"], ))
        db.commit()
        cur.close()
    return redirect(request.referrer)


### ADMIN SECTION AND ASSOCIATED FUNCTIONS ###
# Displays all standard_food items to admin
@app.route("/admin_food")
@helpers.admin_required
def admin_food():
    cur = db.cursor()
    standard_foods = cur.execute("SELECT standard_food.id, standard_food.food_name, standard_food.energy, standard_food.protein, standard_food.carbohydrate, standard_food.fat, food_type.type, food_type.id AS food_type_id FROM standard_food INNER JOIN food_type ON standard_food.food_type_id = food_type.id ORDER BY food_name").fetchall()
    food_types = cur.execute(
        "SELECT * FROM food_type ORDER BY type").fetchall()
    cur.close()
    return render_template("admin_food.html", standard_foods=standard_foods, food_types=food_types)

# Allows admin to add items to the standard foods table avaliabe to all users
@app.route("/add_standard_food", methods=["POST"])
@helpers.admin_required
def standard_food():
    try:
        values = helpers.check_values(request.form.to_dict(flat=True), string=["name"], zero=[
            "energy", "protein", "carbohydrate", "fat"], positive=["amount"])
    except Exception as e:
        print(f"/add_standard_food ERROR: {e}")
        pass
    else:
        energy = round(values["energy"] / values["amount"] * 100, 2)
        protein = round(values["protein"] / values["amount"] * 100, 2)
        carbs = round(values["carbohydrate"] / values["amount"] * 100, 2)
        fat = round(values["fat"] / values["amount"] * 100, 2)
        cur = db.cursor()
        if cur.execute("INSERT INTO standard_food (food_name, food_type_id, energy, protein, carbohydrate, fat) VALUES (?, ?, ?, ?, ?, ?)", (request.form.get("name"), request.form.get("food_type"), energy, protein, carbs, fat)).rowcount < 1:
            helpers.add_toast(f"Food not added to database, please try again")
        db.commit()
        cur.close()
    return redirect(request.referrer)

# Allows admin to update items in the standard foods table avaliabe to all users
@app.route("/update_standard_food", methods=["POST"])
@helpers.admin_required
def update_standard_food():
    cur = db.cursor()
    cur.execute("""UPDATE standard_food
                SET food_name = ?, food_type_id = ?, energy = ?, protein = ?, carbohydrate = ?, fat = ?
                WHERE id = ?""", (request.form.get("food_name"), request.form.get("food_type"), request.form.get("energy"), request.form.get("protein"), request.form.get("carbohydrate"), request.form.get("fat"), request.form.get("id")))
    db.commit()
    cur.close()
    return redirect(request.referrer)

# Allows admin to remove items from the standard foods table avaliabe to all users
@app.route("/delete_standard_food", methods=["POST"])
@helpers.admin_required
def delete_standard_food():
    cur = db.cursor()
    cur.execute("DELETE FROM standard_food WHERE id = ?",
                (request.form.get("id"), ))
    db.commit()
    cur.close()
    return redirect(request.referrer)

# User admin page
@app.route("/admin_users")
@helpers.admin_required
def admin_users():
    cur = db.cursor()
    users = cur.execute("SELECT * FROM users").fetchall()
    cur.close()
    return render_template("admin_users.html", users=users)

# Removes a user from the user's table along with linked records
@app.route("/delete_user", methods=["POST"])
@helpers.admin_required
def delete_user():
    deleted_rows = {}
    cur = db.cursor()
    id = request.form.get("id")
    user = cur.execute("SELECT * FROM users WHERE id = ?", (id, )).fetchone()
    deleted_rows["username"] = user["username"]
    deleted_rows["id"] = user["id"]
    cur.execute("DELETE FROM weight WHERE user_id = ?", (id, ))
    deleted_rows["weight"] = cur.rowcount
    cur.execute("DELETE FROM activity WHERE user_id = ?", (id, ))
    deleted_rows["activity"] = cur.rowcount
    cur.execute("DELETE FROM consumption WHERE user_id = ?", (id, ))
    deleted_rows["consumption"] = cur.rowcount
    cur.execute("DELETE FROM custom_food WHERE user_id = ?", (id, ))
    deleted_rows["custom_food"] = cur.rowcount
    cur.execute("DELETE FROM users WHERE id = ?", (id, ))
    db.commit()
    cur.close()
    return render_template("admin_user_deleted.html", deleted_rows=deleted_rows)

# Admin page for exercise catalog
@app.route("/admin_exercises")
@helpers.admin_required
def admin_exercises():
    cur = db.cursor()
    exercises = cur.execute(
        "SELECT * FROM standard_exercises ORDER BY exercise_name, energy_burn_factor").fetchall()
    cur.close()
    return render_template("admin_exercises.html", exercises=exercises)

# Admin exercise adjustment function
@app.route("/update_exercise", methods=["POST"])
@helpers.admin_required
def update_exercise():
    cur = db.cursor()
    cur.execute("""UPDATE standard_exercises
                SET exercise_name = ?, intensity = ?, energy_burn_factor = ?
                WHERE id = ?""", (request.form.get("exercise_name"), request.form.get("intensity"), request.form.get("energy_burn_factor"), request.form.get("id")))
    db.commit()
    cur.close()
    return redirect("/admin_exercises")

# Admin add a new exercise to the catalog
@app.route("/add_exercise", methods=["POST"])
@helpers.admin_required
def add_exercise():
    # Required: exercise_name & energy_burn_factor
    # Optional: intensity
    try:
        values = helpers.check_values(request.form.to_dict(flat=True), string=[
            "exercise_name"], positive=["energy_burn_factor"])
    except Exception as e:
        print(f"/add_exercise ERROR: {e}")
        pass
    else:
        cur = db.cursor()
        cur.execute("INSERT INTO standard_exercises (exercise_name, intensity, energy_burn_factor) VALUES (?, ?, ?)",
                    (values["exercise_name"], request.form.get("intensity"), values["energy_burn_factor"]))
        db.commit()
        cur.close()
    return redirect(request.referrer)

# Admin remove an exercise from the catalog

@app.route("/delete_exercise", methods=["POST"])
@helpers.admin_required
def delete_exercise():
    try:
        values = helpers.check_values(
            request.form.to_dict(flat=True), positive=["id"])
    except Exception as e:
        print(f"/delete_exercise ERROR: {e}")
        pass
    else:
        cur = db.cursor()
        cur.execute("DELETE FROM standard_exercises WHERE id = ?",
                    (values["id"], ))
        db.commit()
        cur.close()
    return redirect("/admin_exercises")


# Remove/acknowledge a "toast" notification from the system
@app.route("/rm_toast", methods=["POST"])
@helpers.login_required
def rm_toast():
    if request.form.get("id") == "*":
        session["toasts"] = []
    else:
        del session["toasts"][int(request.form.get("id"))]
        helpers.index_toasts()
    return redirect(request.referrer)


### NAVIGATION###
# Changes the selected food type used for navigation on the "/diet_diary" page
@app.route("/change_food_type", methods=["POST"])
@helpers.login_required
def change_food_type():
    session["food_type"] = request.form.get("id")
    return redirect(request.referrer)

# Changes the visible day used for navigation across the system
@app.route("/change_day", methods=["POST"])
@helpers.login_required
def change_day():
    if request.form.get("day") == "0":
        session["date"] = session["today"]
    else:
        session["date"] = session["date"] + \
            timedelta(days=int(request.form.get("day")))
    return redirect(request.referrer)
