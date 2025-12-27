from dotenv import load_dotenv
import os
load_dotenv()
from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import datetime, date
import math
import os
from werkzeug.utils import secure_filename
from bill_verifier import extract_text_from_bill, extract_units, verify_units

# ================== APP SETUP ==================
app = Flask(__name__)
app.secret_key = "carbon_secret"
DB = "database.db"

# ================== FILE UPLOAD ==================
UPLOAD_FOLDER = "static/bills"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ================== EMISSION FACTORS ==================
EMISSION_FACTORS = {
    "Car": 0.192,
    "Bike": 0.103,
    "Bus": 0.082,
    "Train": 0.041
}

ELECTRICITY_FACTOR = 0.82  # kg CO₂ per kWh (India)

# ================== DB HELPER ==================
import psycopg2

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


# ================== ACHIEVEMENT ENGINE ==================

LEVELS = [
    ("🌱 Seed", 0),
    ("🌿 Sprout", 300),
    ("🌳 Tree", 1000),
    ("🌲 Forest", 3000),
    ("🏆 Guardian", 8000),
    ("👑 Legend", 20000)
]

ACHIEVEMENT_CATEGORIES = {
    "consistency": {
        "stat": "active_days",
        "unit": "days",
        "desc": "Stay active on the app",
        "tiers": [(7, 50), (30, 150), (90, 400), (180, 1000), (365, 3000)]
    },
    "travel": {
        "stat": "total_trips",
        "unit": "trips",
        "desc": "Log your daily travel",
        "tiers": [(10, 40), (50, 120), (200, 350), (500, 1000), (2000, 3000)]
    },
    "public_transport": {
        "stat": "public_trips",
        "unit": "eco trips",
        "desc": "Use low-emission transport",
        "tiers": [(10, 80), (50, 250), (200, 900)]
    },
    "cycling": {
        "stat": "bike_trips",
        "unit": "rides",
        "desc": "Choose cycling over vehicles",
        "tiers": [(5, 50), (25, 150), (100, 500)]
    },
    "electricity": {
        "stat": "electricity_months",
        "unit": "months",
        "desc": "Log electricity usage",
        "tiers": [(3, 60), (6, 200), (12, 600)]
    }
}

def get_user_stats(user):
    db = get_db()
    c = db.cursor()

    c.execute("SELECT COUNT(DISTINCT date) FROM trips WHERE user=?", (user,))
    active_days = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM trips WHERE user=?", (user,))
    total_trips = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM trips WHERE user=? AND vehicle IN ('Bus','Train')", (user,))
    public_trips = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM trips WHERE user=? AND vehicle='Bike'", (user,))
    bike_trips = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT month) FROM electricity WHERE user=?", (user,))
    electricity_months = c.fetchone()[0]

    db.close()

    return {
        "active_days": active_days,
        "total_trips": total_trips,
        "public_trips": public_trips,
        "bike_trips": bike_trips,
        "electricity_months": electricity_months
    }

def calculate_achievements(user):
    stats = get_user_stats(user)
    achievements = []
    points = 0

    for category in ACHIEVEMENT_CATEGORIES.values():
        value = stats.get(category["stat"], 0)

        for target, reward in category["tiers"]:
            if value >= target:
                achievements.append((f"{target} {category['unit']}", reward))
                points += reward

    return achievements, points

def calculate_achievement_progress(user):
    stats = get_user_stats(user)
    progress = []

    for name, category in ACHIEVEMENT_CATEGORIES.items():
        value = stats.get(category["stat"], 0)
        tiers = category["tiers"]

        # Find which tier is currently active
        active_tier = None
        for target, reward in tiers:
            if value < target:
                active_tier = (target, reward)
                break
        else:
            active_tier = tiers[-1]

        target, reward = active_tier
        current = min(value, target)
        percent = int((current / target) * 100)

        progress.append({
            "name": f"{target} {category['unit']}",
            "desc": category["desc"],
            "current": current,
            "target": target,
            "unit": category["unit"],
            "points": reward,
            "percent": percent,
            "unlocked": value >= target
        })

    return progress

def get_user_level(points):
    current = LEVELS[0]
    next_level = None

    for i in range(len(LEVELS)):
        if points >= LEVELS[i][1]:
            current = LEVELS[i]
            if i + 1 < len(LEVELS):
                next_level = LEVELS[i + 1]

    return current, next_level


# ================== LOGIN ==================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()

        if not username:
            return render_template("login.html", error="Username required")

        db = get_db()
        c = db.cursor()

        c.execute("SELECT username FROM users WHERE username=?", (username,))
        user = c.fetchone()

        db.close()

        if not user:
            return render_template("login.html", error="User not found. Please sign up first.")

        session["user"] = username
        return redirect("/home")

    return render_template("login.html")

# ================== HOME ==================
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")
    return render_template("home.html", page="home")

# ================== DAILY TRAVEL ==================
@app.route("/daily-travel", methods=["GET", "POST"])
def daily_travel():
    if "user" not in session:
        return redirect("/")

    user = session["user"]
    today = date.today().isoformat()

    db = get_db()
    c = db.cursor()

    if request.method == "POST":
        vehicle = request.form["vehicle"]
        distance = float(request.form["distance"])

        c.execute("""
            INSERT INTO trips (user, mode, vehicle, distance, date)
            VALUES (?, 'manual', ?, ?, ?)
        """, (user, vehicle, distance, today))
        db.commit()

    c.execute("""
        SELECT id, vehicle, distance, mode
        FROM trips
        WHERE user=? AND date=?
    """, (user, today))

    trips = c.fetchall()
    db.close()

    return render_template("daily_travel.html", trips=trips, page="daily_travel")

# ================== AUTOMATIC TRIP ==================
@app.route("/start-trip", methods=["POST"])
def start_trip():
    data = request.json
    session["auto_trip"] = {
        "lat": data["lat"],
        "lon": data["lon"],
        "time": datetime.now().strftime("%H:%M:%S")
    }
    return jsonify({"status": "started"})

@app.route("/end-trip", methods=["POST"])
def end_trip():
    data = request.json
    start = session["auto_trip"]

    vehicle = data["vehicle"]
    end_lat = data["lat"]
    end_lon = data["lon"]

    distance = haversine(start["lat"], start["lon"], end_lat, end_lon)

    db = get_db()
    c = db.cursor()

    c.execute("""
        INSERT INTO trips (
            user, mode, vehicle, distance, date,
            start_lat, start_lon, end_lat, end_lon,
            start_time, end_time
        )
        VALUES (?, 'automatic', ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user"],
        vehicle,
        distance,
        date.today().isoformat(),
        start["lat"],
        start["lon"],
        end_lat,
        end_lon,
        start["time"],
        datetime.now().strftime("%H:%M:%S")
    ))

    db.commit()
    db.close()
    session.pop("auto_trip")

    return jsonify({"distance": distance})

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat/2)**2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon/2)**2
    )
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

# ================== DELETE TRIP ==================
@app.route("/delete-trip/<int:trip_id>", methods=["POST"])
def delete_trip(trip_id):
    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM trips WHERE id=? AND user=?", (trip_id, session["user"]))
    db.commit()
    db.close()
    return redirect("/daily-travel")

# ================== EMISSIONS ==================
@app.route("/emissions")
def emissions():
    if "user" not in session:
        return redirect("/")

    user = session["user"]
    today = date.today().isoformat()

    db = get_db()
    c = db.cursor()

    c.execute("SELECT vehicle, distance, mode FROM trips WHERE user=? AND date=?",
              (user, today))
    rows = c.fetchall()

    trips = []
    vehicle_totals = {}
    travel_emission = 0.0

    for v, d, m in rows:
        emission = round(d * EMISSION_FACTORS.get(v, 0), 2)
        travel_emission += emission

        trips.append({"vehicle": v, "distance": d, "mode": m, "emission": emission})
        vehicle_totals[v] = round(vehicle_totals.get(v, 0) + emission, 2)

    travel_emission = round(travel_emission, 2)

    current_month = date.today().strftime("%Y-%m")
    c.execute("SELECT SUM(co2) FROM electricity WHERE user=? AND month=?",
              (user, current_month))
    electricity_emission = round(c.fetchone()[0] or 0, 2)

    db.close()

    total_combined_emission = round(travel_emission + electricity_emission, 2)

    emission_level = "low" if total_combined_emission <= 5 else "medium" if total_combined_emission <= 10 else "high"

    return render_template("emissions.html",
                           trips=trips,
                           travel_emission=travel_emission,
                           electricity_emission=electricity_emission,
                           total_combined_emission=total_combined_emission,
                           vehicle_totals=vehicle_totals,
                           emission_level=emission_level,
                           page="emissions")

# ================== FINISH DAY ==================
@app.route("/finish-day", methods=["POST"])
def finish_day():
    if "user" not in session:
        return redirect("/")

    # All emissions already saved via trips + electricity
    # This endpoint simply closes the day and moves user forward

    return redirect("/emissions")



# ================== ELECTRICITY ==================
@app.route("/electricity", methods=["GET", "POST"])
def electricity():
    if "user" not in session:
        return redirect("/")

    message = verification = detected_units = None

    if request.method == "POST":
        units = float(request.form["units"])
        month = request.form["month"]
        bill = request.files["bill"]

        filename = secure_filename(bill.filename)
        bill_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        bill.save(bill_path)

        text = extract_text_from_bill(bill_path)
        detected_units = extract_units(text)
        verification = verify_units(units, detected_units)

        co2 = round(units * ELECTRICITY_FACTOR, 2)

        db = get_db()
        c = db.cursor()
        c.execute("""INSERT INTO electricity (user, month, units, co2, bill_file, uploaded_at)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (session["user"], month, units, co2, filename, datetime.now().isoformat()))
        db.commit()
        db.close()

        message = "Electricity bill uploaded successfully ✅"

    return render_template("electricity.html", page="electricity",
                           message=message, verification=verification,
                           detected_units=detected_units)

# ================== SUGGESTIONS ==================
@app.route("/suggestions")
def suggestions():
    if "user" not in session:
        return redirect("/")

    user = session["user"]
    today = date.today().isoformat()

    db = get_db()
    c = db.cursor()
    c.execute("SELECT vehicle, distance FROM trips WHERE user=? AND date=?", (user, today))
    rows = c.fetchall()

    travel_emission = round(sum(d * EMISSION_FACTORS.get(v, 0) for v, d in rows), 2)

    c.execute("SELECT SUM(co2) FROM electricity WHERE user=?", (user,))
    electricity_emission = round(c.fetchone()[0] or 0, 2)
    db.close()

    if travel_emission >= electricity_emission:
        suggestions = ["Use public transport", "Walk for short distances", "Carpool"]
        reduction_labels = ["Car → Bus", "Car → Walk", "Carpool"]
        reduction_values = [
            round(travel_emission * 0.4, 2),
            round(travel_emission * 0.7, 2),
            round(travel_emission * 0.25, 2)
        ]
    else:
        suggestions = ["Reduce AC usage", "Switch to LED", "Avoid standby power"]
        reduction_labels = ["Reduce AC", "LED", "No Standby"]
        reduction_values = [
            round(electricity_emission * 0.3, 2),
            round(electricity_emission * 0.2, 2),
            round(electricity_emission * 0.15, 2)
        ]

    total_current = travel_emission + electricity_emission
    best_reduction = max(reduction_values)
    improved_emission = round(total_current - best_reduction, 2)

    return render_template(
        "suggestions.html",
        suggestions=suggestions,
        travel=travel_emission,
        electricity=electricity_emission,
        reduction_labels=reduction_labels,
        reduction_values=reduction_values,
        improved_emission=improved_emission,
        page="suggestions"
    )

# ================== ACHIEVEMENTS ==================
@app.route("/achievements")
def achievements():
    if "user" not in session:
        return redirect("/")

    user = session["user"]
    achievements, points = calculate_achievements(user)
    progress = calculate_achievement_progress(user)
    current_level, next_level = get_user_level(points)

    return render_template(
        "achievements.html",
        achievements=achievements,
        progress=progress,
        current_level=current_level,
        next_level=next_level,
        points=points,
        page="achievements"
    )


# ================== LEADERBOARD ==================
@app.route("/leaderboard")
def leaderboard():
    if "user" not in session:
        return redirect("/")

    db = get_db()
    c = db.cursor()

    # Get all real users
    c.execute("SELECT username FROM users")
    users = [u[0] for u in c.fetchall()]

    leaderboard = []

    for username in users:
        # Points from achievements system
        _, points = calculate_achievements(username)

        # Calculate total travel emission from trips
        c.execute("SELECT vehicle, distance FROM trips WHERE user=?", (username,))
        rows = c.fetchall()

        travel_emission = 0
        for v, d in rows:
            travel_emission += d * EMISSION_FACTORS.get(v, 0)

        travel_emission = round(travel_emission, 2)

        # Electricity emission
        c.execute("SELECT SUM(co2) FROM electricity WHERE user=?", (username,))
        electricity_emission = round(c.fetchone()[0] or 0, 2)

        total_emission = round(travel_emission + electricity_emission, 2)

        leaderboard.append({
            "username": username,
            "points": points,
            "emission": total_emission
        })

    # Sort by points (highest first)
    leaderboard.sort(key=lambda x: x["points"], reverse=True)

    # Current user stats
    usernames = [u["username"] for u in leaderboard]
    your_rank = usernames.index(session["user"]) + 1 if session["user"] in usernames else "-"
    your_data = next(u for u in leaderboard if u["username"] == session["user"])

    db.close()

    return render_template(
        "leaderboard.html",
        leaderboard=leaderboard,
        your_rank=your_rank,
        your_points=your_data["points"],
        your_emission=your_data["emission"],
        total_users=len(leaderboard),
        page="leaderboard"
    )


# ================== SIGNUP ==================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()

        db = get_db()
        c = db.cursor()

        c.execute("SELECT username FROM users WHERE username=?", (username,))
        if c.fetchone():
            db.close()
            return render_template("signup.html", error="Username already exists")

        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        db.commit()
        db.close()

        session["user"] = username
        return redirect("/home")

    return render_template("signup.html")
# ================== LOGOUT ==================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================== RUN ==================
if __name__ == "__main__":
    app.run(debug=True)
