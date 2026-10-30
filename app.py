import os, json
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-before-deploy")
db_url = os.environ.get("DATABASE_URL", "sqlite:///sczb_tryout.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_no = db.Column(db.String(40), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="participant", nullable=False)

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title_id = db.Column(db.String(180), nullable=False)
    title_zh = db.Column(db.String(180), nullable=False, default="")
    duration_minutes = db.Column(db.Integer, default=90)
    is_active = db.Column(db.Boolean, default=True)
    questions = db.relationship("Question", backref="exam", cascade="all, delete-orphan", order_by="Question.id")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    text_id = db.Column(db.Text, nullable=False)
    text_zh = db.Column(db.Text, default="")
    a_id = db.Column(db.Text, nullable=False)
    b_id = db.Column(db.Text, nullable=False)
    c_id = db.Column(db.Text, nullable=False)
    d_id = db.Column(db.Text, nullable=False)
    a_zh = db.Column(db.Text, default="")
    b_zh = db.Column(db.Text, default="")
    c_zh = db.Column(db.Text, default="")
    d_zh = db.Column(db.Text, default="")
    correct = db.Column(db.String(1), nullable=False)

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    score = db.Column(db.Float, default=0)
    total = db.Column(db.Integer, default=0)
    answers_json = db.Column(db.Text, default="{}")
    finished_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")
    exam = db.relationship("Exam")

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Akses khusus administrator / 仅限管理员访问")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def common():
    return {"lang": session.get("lang", "id")}

@app.route("/language/<value>")
def language(value):
    session["lang"] = "zh" if value == "zh" else "id"
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        emp = request.form.get("employee_no", "").strip()
        user = User.query.filter_by(employee_no=emp).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            session.update(user_id=user.id, employee_no=user.employee_no, full_name=user.full_name, role=user.role)
            return redirect(url_for("dashboard"))
        flash("Nomor karyawan atau password salah / 工号或密码错误")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    exams = Exam.query.filter_by(is_active=True).all()
    attempts = Attempt.query.filter_by(user_id=session["user_id"]).order_by(Attempt.finished_at.desc()).all()
    return render_template("dashboard.html", exams=exams, attempts=attempts)

@app.route("/exam/<int:exam_id>", methods=["GET", "POST"])
@login_required
def take_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if not exam.is_active:
        flash("Ujian tidak aktif / 考试未开放")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        answers = request.form.to_dict()
        questions = exam.questions
        correct = sum(1 for q in questions if answers.get(str(q.id)) == q.correct)
        total = len(questions)
        score = round((correct / total) * 100, 2) if total else 0
        attempt = Attempt(user_id=session["user_id"], exam_id=exam.id, score=score,
                          total=total, answers_json=json.dumps(answers, ensure_ascii=False))
        db.session.add(attempt); db.session.commit()
        return redirect(url_for("result", attempt_id=attempt.id))
    return render_template("exam.html", exam=exam, questions=exam.questions)

@app.route("/result/<int:attempt_id>")
@login_required
def result(attempt_id):
    attempt = Attempt.query.get_or_404(attempt_id)
    if attempt.user_id != session["user_id"] and session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    return render_template("result.html", attempt=attempt)

@app.route("/ranking")
@login_required
def ranking():
    rows = db.session.query(User.full_name, db.func.max(Attempt.score).label("best")).join(
        Attempt, Attempt.user_id == User.id).group_by(User.id).order_by(db.desc("best")).all()
    return render_template("ranking.html", rows=rows)

@app.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "user":
            emp = request.form["employee_no"].strip()
            if User.query.filter_by(employee_no=emp).first():
                flash("Nomor karyawan sudah terdaftar / 工号已存在")
            else:
                u = User(employee_no=emp, full_name=request.form["full_name"].strip(),
                         password_hash=generate_password_hash(request.form["password"]),
                         role=request.form.get("role", "participant"))
                db.session.add(u); db.session.commit()
                flash("Peserta berhasil ditambahkan / 考生添加成功")
        elif action == "exam":
            e = Exam(title_id=request.form["title_id"], title_zh=request.form.get("title_zh",""),
                     duration_minutes=int(request.form.get("duration",90)))
            db.session.add(e); db.session.commit()
            flash("Ujian berhasil dibuat / 考试创建成功")
        elif action == "question":
            q = Question(exam_id=int(request.form["exam_id"]), text_id=request.form["text_id"],
                text_zh=request.form.get("text_zh",""), a_id=request.form["a_id"], b_id=request.form["b_id"],
                c_id=request.form["c_id"], d_id=request.form["d_id"], a_zh=request.form.get("a_zh",""),
                b_zh=request.form.get("b_zh",""), c_zh=request.form.get("c_zh",""),
                d_zh=request.form.get("d_zh",""), correct=request.form["correct"])
            db.session.add(q); db.session.commit()
            flash("Soal berhasil ditambahkan / 题目添加成功")
        return redirect(url_for("admin"))
    return render_template("admin.html", users=User.query.order_by(User.id.desc()).all(),
        exams=Exam.query.order_by(Exam.id.desc()).all())

@app.route("/admin/exam/<int:exam_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_exam(exam_id):
    e = Exam.query.get_or_404(exam_id); e.is_active = not e.is_active
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/health")
def health():
    return {"status": "ok"}

with app.app_context():
    db.create_all()
    # Initial admin is created only when environment variables are supplied.
    admin_user = os.environ.get("ADMIN_USER")
    admin_pass = os.environ.get("ADMIN_PASSWORD")
    if admin_user and admin_pass and not User.query.filter_by(employee_no=admin_user).first():
        db.session.add(User(employee_no=admin_user, full_name="Administrator",
            password_hash=generate_password_hash(admin_pass), role="admin"))
        db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
