from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ── Users ────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")  # admin | employee
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships
    created_courses = db.relationship("Course", backref="creator", lazy=True)
    enrollments = db.relationship("Enrollment", backref="user", lazy=True)
    quiz_attempts = db.relationship("QuizAttempt", backref="user", lazy=True)
    module_completions = db.relationship("ModuleCompletion", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ── Courses ──────────────────────────────────────────────────────────────
class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships
    modules = db.relationship(
        "Module", backref="course", lazy=True, order_by="Module.order_index",
        cascade="all, delete-orphan"
    )
    enrollments = db.relationship(
        "Enrollment", backref="course", lazy=True, cascade="all, delete-orphan"
    )
    questions = db.relationship(
        "Question", backref="course", lazy=True, cascade="all, delete-orphan"
    )
    quiz_attempts = db.relationship(
        "QuizAttempt", backref="course", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Course {self.title}>"


# ── Modules (Text Lessons) ──────────────────────────────────────────────
class Module(db.Model):
    __tablename__ = "modules"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content_md = db.Column(db.Text, default="")  # Markdown source
    order_index = db.Column(db.Integer, nullable=False, default=0)

    # relationships
    completions = db.relationship(
        "ModuleCompletion", backref="module", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Module {self.title} (order={self.order_index})>"


# ── Quiz Questions (MCQ) ────────────────────────────────────────────────
class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # a, b, c, or d

    def __repr__(self):
        return f"<Question {self.id} for Course {self.course_id}>"


# ── Quiz Attempts ────────────────────────────────────────────────────────
class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)  # percentage 0-100
    passed = db.Column(db.Boolean, nullable=False, default=False)
    taken_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<QuizAttempt user={self.user_id} course={self.course_id} score={self.score}>"


# ── Module Completions ───────────────────────────────────────────────────
class ModuleCompletion(db.Model):
    __tablename__ = "module_completions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id"), nullable=False)
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "module_id", name="unique_module_completion"),
    )

    def __repr__(self):
        return f"<ModuleCompletion user={self.user_id} module={self.module_id}>"


# ── Enrollments ──────────────────────────────────────────────────────────
class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # prevent duplicate enrollments
    __table_args__ = (
        db.UniqueConstraint("user_id", "course_id", name="unique_enrollment"),
    )

    def __repr__(self):
        return f"<Enrollment user={self.user_id} course={self.course_id}>"
