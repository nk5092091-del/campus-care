from flask import Flask, render_template, request, redirect, session, flash
import json, os, uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "campus_secret_123"
ADMIN_EMAIL = "admin@college.com"   # is email se register karoge to admin banoge
FILE = "data.json"
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_photo(file):
    if not file or file.filename == "":
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXT:
        return None
    name = uuid.uuid4().hex + "." + ext
    file.save(os.path.join(UPLOAD_FOLDER, name))
    return name

# ---------- data load / save ----------
def load():
    if not os.path.exists(FILE):
        return {"users": [], "complaints": []}
    with open(FILE) as f:
        return json.load(f)

def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)

def stats(complaints):
    return {
        "total": len(complaints),
        "pending": len([c for c in complaints if c["status"] == "Pending"]),
        "resolved": len([c for c in complaints if c["status"] == "Resolved"]),
    }

# ---------- pages ----------
@app.route("/")
def home():
    session.clear()          
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = load()
        email = request.form["email"]
        for u in data["users"]:
            if u["email"] == email:
                flash("Email already registered.")
                return render_template("register.html")
        data["users"].append({
            "id": len(data["users"]) + 1,
            "name": request.form["name"],
            "email": email,
            "password": request.form["password"]
        })
        save(data)
        flash("Registered successfully! Please login.")
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = load()
        email = request.form["email"]
        password = request.form["password"]
        for u in data["users"]:
            if u["email"] == email and u["password"] == password:
                session.permanent = bool(request.form.get("remember"))
                session["user_id"] = u["id"]
                session["name"] = u["name"]
                session["is_admin"] = (email == ADMIN_EMAIL)
                return redirect("/admin" if session["is_admin"] else "/complaint")
        flash("Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/complaint", methods=["GET", "POST"])
def complaint():
    if "user_id" not in session:
        return redirect("/login")
    data = load()
    if request.method == "POST":
        f = request.form
        photo = save_photo(request.files.get("photo"))
        data["complaints"].append({
            "id": len(data["complaints"]) + 1,
            "user_id": session["user_id"],
            "name": f["name"],
            "department": f["department"],
            "roll_no": f["roll_no"],
            "category": f["category"],
            "location": f["location"],
            "description": f["description"],
            "photo": photo,
            "status": "Pending",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        save(data)
        count = len([c for c in data["complaints"] if c["user_id"] == session["user_id"]])
        flash(f"Complaint submitted successfully! This is your complaint #{count}.")
        return redirect("/my_complaints")
    mine = [c for c in data["complaints"] if c["user_id"] == session["user_id"]]
    return render_template("complaint.html", s=stats(mine))

@app.route("/my_complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect("/login")
    data = load()
    mine = [c for c in data["complaints"] if c["user_id"] == session["user_id"]]
    s = stats(mine)
    mine.reverse()
    return render_template("my_complaints.html", complaints=mine, s=s)

@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect("/login")
    data = load()
    counts = {}
    for c in data["complaints"]:
        counts[c["user_id"]] = counts.get(c["user_id"], 0) + 1
    return render_template("admin.html",
                           complaints=data["complaints"][::-1],
                           counts=counts,
                           s=stats(data["complaints"]))

@app.route("/resolve/<int:cid>")
def resolve(cid):
    if not session.get("is_admin"):
        return redirect("/login")
    data = load()
    for c in data["complaints"]:
        if c["id"] == cid:
            c["status"] = "Resolved"
    save(data)
    return redirect("/admin")

if __name__ == "__main__":
    app.run(debug=True)