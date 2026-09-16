import os, sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB = os.path.join(BASE_DIR, "database.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED = {"png", "jpg", "jpeg", "webp", "gif"}

app = Flask(__name__, template_folder=".", static_folder="static")
app.secret_key = "change-this-secret-key-in-production"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
os.makedirs(UPLOAD_DIR, exist_ok=True)

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK(id=1),
        college_name TEXT NOT NULL DEFAULT 'MPIT College Amroha',
        tagline TEXT DEFAULT 'Excellence in Education',
        about TEXT DEFAULT 'Welcome to MPIT College Amroha.',
        address TEXT DEFAULT 'Amroha, Uttar Pradesh, India',
        phone TEXT DEFAULT '+91 00000 00000',
        email TEXT DEFAULT 'info@mpitcollege.example',
        logo TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS faculty (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        designation TEXT NOT NULL,
        qualification TEXT DEFAULT '',
        photo TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT DEFAULT '',
        image TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        duration TEXT DEFAULT '',
        description TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT DEFAULT '',
        course TEXT DEFAULT '',
        message TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    if con.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
        con.execute("INSERT INTO settings (id) VALUES (1)")
    if con.execute("SELECT COUNT(*) FROM faculty").fetchone()[0] == 0:
        con.executemany("INSERT INTO faculty(name,designation,qualification) VALUES(?,?,?)", [
            ("Dr. Principal Name", "Principal", "Ph.D."),
            ("Faculty Member", "Assistant Professor", "M.A., B.Ed."),
            ("Faculty Member", "Lecturer", "M.Sc.")
        ])
    if con.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        con.executemany("INSERT INTO courses(name,duration,description) VALUES(?,?,?)", [
            ("Course / Program 1", "3 Years", "Add your course description from Admin Panel."),
            ("Course / Program 2", "2 Years", "Add your course description from Admin Panel."),
            ("Course / Program 3", "1 Year", "Add your course description from Admin Panel.")
        ])
    con.commit()
    con.close()

def allowed_file(name):
    return "." in name and name.rsplit(".",1)[1].lower() in ALLOWED

def save_upload(file):
    if not file or not file.filename:
        return ""
    if not allowed_file(file.filename):
        return ""
    filename = secure_filename(file.filename)
    base, ext = os.path.splitext(filename)
    i=1
    final=filename
    while os.path.exists(os.path.join(UPLOAD_DIR, final)):
        final=f"{base}_{i}{ext}"; i+=1
    file.save(os.path.join(UPLOAD_DIR, final))
    return final

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_common():
    con=db()
    settings=con.execute("SELECT * FROM settings WHERE id=1").fetchone()
    con.close()
    return {"site": settings}

@app.route("/")
def home():
    con=db()
    faculty=con.execute("SELECT * FROM faculty ORDER BY id DESC LIMIT 6").fetchall()
    courses=con.execute("SELECT * FROM courses ORDER BY id DESC LIMIT 6").fetchall()
    gallery=con.execute("SELECT * FROM gallery ORDER BY id DESC LIMIT 8").fetchall()
    notices=con.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 5").fetchall()
    con.close()
    return render_template("index.html", faculty=faculty, courses=courses, gallery=gallery, notices=notices)

@app.route("/about")
def about(): return render_template("about.html")

@app.route("/courses")
def courses():
    con=db(); rows=con.execute("SELECT * FROM courses ORDER BY id DESC").fetchall(); con.close()
    return render_template("courses.html", courses=rows)

@app.route("/faculty")
def faculty():
    con=db(); rows=con.execute("SELECT * FROM faculty ORDER BY id DESC").fetchall(); con.close()
    return render_template("faculty.html", faculty=rows)

@app.route("/gallery")
def gallery():
    con=db(); rows=con.execute("SELECT * FROM gallery ORDER BY id DESC").fetchall(); con.close()
    return render_template("gallery.html", gallery=rows)

@app.route("/admission", methods=["GET","POST"])
def admission():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        phone=request.form.get("phone","").strip()
        email=request.form.get("email","").strip()
        course=request.form.get("course","").strip()
        message=request.form.get("message","").strip()
        if not name or not phone:
            flash("Name and phone are required.", "error")
        else:
            con=db(); con.execute("INSERT INTO enquiries(name,phone,email,course,message) VALUES(?,?,?,?,?)",
                (name,phone,email,course,message)); con.commit(); con.close()
            flash("Your enquiry has been submitted successfully.", "success")
            return redirect(url_for("admission"))
    con=db(); courses=con.execute("SELECT * FROM courses ORDER BY name").fetchall(); con.close()
    return render_template("admission.html", courses=courses)

@app.route("/contact")
def contact(): return render_template("contact.html")

@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        # Default login: admin / admin123
        if request.form.get("username")=="admin" and request.form.get("password")=="admin123":
            session["admin"]=True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear(); return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
@admin_required
def dashboard():
    con=db()
    stats={
        "faculty":con.execute("SELECT COUNT(*) FROM faculty").fetchone()[0],
        "gallery":con.execute("SELECT COUNT(*) FROM gallery").fetchone()[0],
        "courses":con.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        "enquiries":con.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0],
    }
    enquiries=con.execute("SELECT * FROM enquiries ORDER BY id DESC LIMIT 10").fetchall()
    con.close()
    return render_template("admin/dashboard.html", stats=stats, enquiries=enquiries)

@app.route("/admin/settings", methods=["GET","POST"])
@admin_required
def settings():
    con=db()
    if request.method=="POST":
        logo=save_upload(request.files.get("logo"))
        old=con.execute("SELECT logo FROM settings WHERE id=1").fetchone()["logo"]
        values=(request.form.get("college_name",""),request.form.get("tagline",""),request.form.get("about",""),
                request.form.get("address",""),request.form.get("phone",""),request.form.get("email",""))
        if logo: con.execute("UPDATE settings SET college_name=?,tagline=?,about=?,address=?,phone=?,email=?,logo=? WHERE id=1", values+(logo,))
        else: con.execute("UPDATE settings SET college_name=?,tagline=?,about=?,address=?,phone=?,email=? WHERE id=1", values)
        con.commit(); flash("College settings updated.", "success")
        return redirect(url_for("settings"))
    row=con.execute("SELECT * FROM settings WHERE id=1").fetchone(); con.close()
    return render_template("admin/settings.html", settings=row)

@app.route("/admin/faculty", methods=["GET","POST"])
@admin_required
def admin_faculty():
    con=db()
    if request.method=="POST":
        fid=request.form.get("id")
        photo=save_upload(request.files.get("photo"))
        name=request.form.get("name","").strip(); designation=request.form.get("designation","").strip()
        qualification=request.form.get("qualification","").strip()
        if fid:
            if photo: con.execute("UPDATE faculty SET name=?,designation=?,qualification=?,photo=? WHERE id=?",(name,designation,qualification,photo,fid))
            else: con.execute("UPDATE faculty SET name=?,designation=?,qualification=? WHERE id=?",(name,designation,qualification,fid))
        else: con.execute("INSERT INTO faculty(name,designation,qualification,photo) VALUES(?,?,?,?)",(name,designation,qualification,photo))
        con.commit(); flash("Faculty saved.", "success"); return redirect(url_for("admin_faculty"))
    rows=con.execute("SELECT * FROM faculty ORDER BY id DESC").fetchall(); con.close()
    return render_template("admin/faculty.html", faculty=rows)

@app.route("/admin/faculty/delete/<int:fid>")
@admin_required
def delete_faculty(fid):
    con=db(); con.execute("DELETE FROM faculty WHERE id=?",(fid,)); con.commit(); con.close()
    return redirect(url_for("admin_faculty"))

@app.route("/admin/gallery", methods=["GET","POST"])
@admin_required
def admin_gallery():
    con=db()
    if request.method=="POST":
        title=request.form.get("title","").strip()
        image=save_upload(request.files.get("image"))
        if image:
            con.execute("INSERT INTO gallery(title,image) VALUES(?,?)",(title,image)); con.commit()
            flash("Gallery image uploaded.", "success")
        else: flash("Please select a valid image.", "error")
        con.close(); return redirect(url_for("admin_gallery"))
    rows=con.execute("SELECT * FROM gallery ORDER BY id DESC").fetchall(); con.close()
    return render_template("admin/gallery.html", gallery=rows)

@app.route("/admin/gallery/delete/<int:gid>")
@admin_required
def delete_gallery(gid):
    con=db(); row=con.execute("SELECT image FROM gallery WHERE id=?",(gid,)).fetchone()
    if row:
        try: os.remove(os.path.join(UPLOAD_DIR,row["image"]))
        except OSError: pass
        con.execute("DELETE FROM gallery WHERE id=?",(gid,)); con.commit()
    con.close(); return redirect(url_for("admin_gallery"))

@app.route("/admin/notices", methods=["GET","POST"])
@admin_required
def admin_notices():
    con=db()
    if request.method=="POST":
        nid=request.form.get("id"); title=request.form.get("title","").strip(); content=request.form.get("content","").strip()
        if nid: con.execute("UPDATE notices SET title=?,content=? WHERE id=?",(title,content,nid))
        else: con.execute("INSERT INTO notices(title,content) VALUES(?,?)",(title,content))
        con.commit(); flash("Notice saved.", "success"); return redirect(url_for("admin_notices"))
    rows=con.execute("SELECT * FROM notices ORDER BY id DESC").fetchall(); con.close()
    return render_template("admin/notices.html", notices=rows)

@app.route("/admin/notices/delete/<int:nid>")
@admin_required
def delete_notice(nid):
    con=db(); con.execute("DELETE FROM notices WHERE id=?",(nid,)); con.commit(); con.close()
    return redirect(url_for("admin_notices"))

@app.route("/admin/courses", methods=["GET","POST"])
@admin_required
def admin_courses():
    con=db()
    if request.method=="POST":
        cid=request.form.get("id"); name=request.form.get("name","").strip(); duration=request.form.get("duration","").strip(); description=request.form.get("description","").strip()
        if cid: con.execute("UPDATE courses SET name=?,duration=?,description=? WHERE id=?",(name,duration,description,cid))
        else: con.execute("INSERT INTO courses(name,duration,description) VALUES(?,?,?)",(name,duration,description))
        con.commit(); flash("Course saved.", "success"); return redirect(url_for("admin_courses"))
    rows=con.execute("SELECT * FROM courses ORDER BY id DESC").fetchall(); con.close()
    return render_template("admin/courses.html", courses=rows)

@app.route("/admin/courses/delete/<int:cid>")
@admin_required
def delete_course(cid):
    con=db(); con.execute("DELETE FROM courses WHERE id=?",(cid,)); con.commit(); con.close()
    return redirect(url_for("admin_courses"))

if __name__=="__main__":
    init_db()
    app.run(debug=True)
