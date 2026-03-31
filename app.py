import math
from functools import wraps
from collections import defaultdict

import markdown2
from flask import (
    Flask, render_template, redirect, url_for, request, flash, abort, jsonify
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

from config import Config
from models import db, User, Course, Module, Question, QuizAttempt, Enrollment, ModuleCompletion
from email_service import send_invite_email


# ── Helpers ──────────────────────────────────────────────────────────────

def admin_required(f):
    """Decorator: restrict route to admin users only."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def employee_required(f):
    """Decorator: restrict route to employee users only."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "employee":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def get_module_progress(user_id, course):
    """Return set of module IDs the user has passed for the given course."""
    passed_ids = set()
    completions = ModuleCompletion.query.filter_by(user_id=user_id).all()
    module_ids = {m.id for m in course.modules}
    for c in completions:
        if c.module_id in module_ids:
            passed_ids.add(c.module_id)
    return passed_ids


def can_access_module(user_id, module):
    """Check if user can access this module (first module or previous passed)."""
    course = module.course
    ordered_modules = sorted(course.modules, key=lambda m: m.order_index)
    idx = next((i for i, m in enumerate(ordered_modules) if m.id == module.id), None)
    if idx is None:
        return False
    if idx == 0:
        return True  # first module always accessible
    prev_module = ordered_modules[idx - 1]
    best = (
        ModuleCompletion.query
        .filter_by(user_id=user_id, module_id=prev_module.id)
        .first()
    )
    return best is not None


# ── App Factory ──────────────────────────────────────────────────────────

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Auth Routes ──────────────────────────────────────────────────

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("employee_dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Welcome back!", "success")
                return redirect(url_for("index"))
            flash("Invalid username or password.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    # ── Admin: Dashboard ─────────────────────────────────────────────

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        courses = Course.query.order_by(Course.created_at.desc()).all()
        total_employees = User.query.filter_by(role="employee").count()
        total_courses = len(courses)
        total_attempts = QuizAttempt.query.count()
        total_passed = QuizAttempt.query.filter_by(passed=True).count()
        pass_rate = round((total_passed / total_attempts) * 100) if total_attempts > 0 else 0
        return render_template(
            "admin/dashboard.html",
            courses=courses,
            total_employees=total_employees,
            total_courses=total_courses,
            total_attempts=total_attempts,
            pass_rate=pass_rate,
        )

    # ── Admin: Manage Employees ──────────────────────────────────────

    @app.route("/admin/employees")
    @admin_required
    def admin_employees():
        employees = User.query.filter_by(role="employee").order_by(User.created_at.desc()).all()
        return render_template("admin/employees.html", employees=employees)

    @app.route("/admin/employees/create", methods=["GET", "POST"])
    @admin_required
    def admin_create_employee():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")

            if not username or not email or not password:
                flash("All fields are required.", "danger")
                return render_template("admin/employee_form.html")

            if User.query.filter_by(username=username).first():
                flash("Username already taken.", "danger")
                return render_template("admin/employee_form.html")

            if User.query.filter_by(email=email).first():
                flash("Email already registered.", "danger")
                return render_template("admin/employee_form.html")

            user = User(username=username, email=email, role="employee")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"Employee '{username}' created successfully.", "success")
            return redirect(url_for("admin_employees"))

        return render_template("admin/employee_form.html")

    # ── Admin: Courses CRUD ──────────────────────────────────────────

    @app.route("/admin/courses/new", methods=["GET", "POST"])
    @admin_required
    def admin_create_course():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            if not title:
                flash("Course title is required.", "danger")
                return render_template("admin/course_form.html")
            course = Course(title=title, description=description, created_by=current_user.id)
            db.session.add(course)
            db.session.commit()
            flash("Course created!", "success")
            return redirect(url_for("admin_course_detail", course_id=course.id))
        return render_template("admin/course_form.html")

    @app.route("/admin/courses/<int:course_id>")
    @admin_required
    def admin_course_detail(course_id):
        course = Course.query.get_or_404(course_id)
        modules = sorted(course.modules, key=lambda m: m.order_index)
        enrolled = (
            db.session.query(User)
            .join(Enrollment)
            .filter(Enrollment.course_id == course_id)
            .all()
        )
        all_employees = User.query.filter_by(role="employee").all()
        not_enrolled = [e for e in all_employees if e not in enrolled]
        return render_template(
            "admin/course_detail.html",
            course=course,
            modules=modules,
            enrolled=enrolled,
            not_enrolled=not_enrolled,
        )

    @app.route("/admin/courses/<int:course_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_course(course_id):
        course = Course.query.get_or_404(course_id)
        if request.method == "POST":
            course.title = request.form.get("title", "").strip()
            course.description = request.form.get("description", "").strip()
            db.session.commit()
            flash("Course updated!", "success")
            return redirect(url_for("admin_course_detail", course_id=course.id))
        return render_template("admin/course_form.html", course=course)

    @app.route("/admin/courses/<int:course_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_course(course_id):
        course = Course.query.get_or_404(course_id)
        db.session.delete(course)
        db.session.commit()
        flash("Course deleted.", "info")
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/courses/<int:course_id>/enroll", methods=["POST"])
    @admin_required
    def admin_enroll_employee(course_id):
        course = Course.query.get_or_404(course_id)
        user_id = request.form.get("user_id", type=int)
        if user_id:
            existing = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
            if not existing:
                enrollment = Enrollment(user_id=user_id, course_id=course_id)
                db.session.add(enrollment)
                db.session.commit()
                flash("Employee enrolled!", "success")
            else:
                flash("Employee already enrolled.", "warning")
        return redirect(url_for("admin_course_detail", course_id=course_id))

    @app.route("/admin/courses/<int:course_id>/unenroll/<int:user_id>", methods=["POST"])
    @admin_required
    def admin_unenroll_employee(course_id, user_id):
        enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
        if enrollment:
            db.session.delete(enrollment)
            db.session.commit()
            flash("Employee unenrolled.", "info")
        return redirect(url_for("admin_course_detail", course_id=course_id))

    @app.route("/admin/courses/<int:course_id>/invite", methods=["POST"])
    @admin_required
    def admin_send_invite(course_id):
        course = Course.query.get_or_404(course_id)
        user_id = request.form.get("user_id", type=int)
        if not user_id:
            flash("No employee selected.", "danger")
            return redirect(url_for("admin_course_detail", course_id=course_id))

        employee = User.query.get_or_404(user_id)
        modules = sorted(course.modules, key=lambda m: m.order_index)
        first_module = modules[0] if modules else None

        if first_module:
            course_url = f"{Config.BASE_URL}/module/{first_module.id}"
        else:
            course_url = f"{Config.BASE_URL}/dashboard"

        success, error = send_invite_email(
            to_email=employee.email,
            employee_name=employee.username,
            course_title=course.title,
            course_url=course_url,
        )

        if success:
            flash(f"Invite email sent to {employee.email}!", "success")
        else:
            flash(f"Failed to send email: {error}", "danger")

        return redirect(url_for("admin_course_detail", course_id=course_id))

    # ── Admin: Modules CRUD ──────────────────────────────────────────

    @app.route("/admin/courses/<int:course_id>/modules/new", methods=["GET", "POST"])
    @admin_required
    def admin_create_module(course_id):
        course = Course.query.get_or_404(course_id)
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content_md = request.form.get("content_md", "")
            order_index = request.form.get("order_index", 0, type=int)
            if not title:
                flash("Module title is required.", "danger")
                return render_template("admin/module_form.html", course=course)
            module = Module(
                course_id=course.id,
                title=title,
                content_md=content_md,
                order_index=order_index,
            )
            db.session.add(module)
            db.session.commit()
            flash("Module created!", "success")
            return redirect(url_for("admin_course_detail", course_id=course.id))
        next_order = len(course.modules)
        return render_template("admin/module_form.html", course=course, next_order=next_order)

    @app.route("/admin/modules/<int:module_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_module(module_id):
        module = Module.query.get_or_404(module_id)
        if request.method == "POST":
            module.title = request.form.get("title", "").strip()
            module.content_md = request.form.get("content_md", "")
            module.order_index = request.form.get("order_index", 0, type=int)
            db.session.commit()
            flash("Module updated!", "success")
            return redirect(url_for("admin_course_detail", course_id=module.course_id))
        return render_template("admin/module_form.html", course=module.course, module=module)

    @app.route("/admin/modules/<int:module_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_module(module_id):
        module = Module.query.get_or_404(module_id)
        course_id = module.course_id
        db.session.delete(module)
        db.session.commit()
        flash("Module deleted.", "info")
        return redirect(url_for("admin_course_detail", course_id=course_id))

    # ── Admin: Quiz Questions CRUD ───────────────────────────────────

    @app.route("/admin/courses/<int:course_id>/quiz", methods=["GET", "POST"])
    @admin_required
    def admin_quiz(course_id):
        course = Course.query.get_or_404(course_id)
        if request.method == "POST":
            question_text = request.form.get("question_text", "").strip()
            option_a = request.form.get("option_a", "").strip()
            option_b = request.form.get("option_b", "").strip()
            option_c = request.form.get("option_c", "").strip()
            option_d = request.form.get("option_d", "").strip()
            correct_option = request.form.get("correct_option", "").strip().lower()

            if not all([question_text, option_a, option_b, option_c, option_d, correct_option]):
                flash("All fields are required.", "danger")
            elif correct_option not in ("a", "b", "c", "d"):
                flash("Correct option must be a, b, c, or d.", "danger")
            else:
                q = Question(
                    course_id=course.id,
                    question_text=question_text,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_option=correct_option,
                )
                db.session.add(q)
                db.session.commit()
                flash("Question added!", "success")
            return redirect(url_for("admin_quiz", course_id=course.id))

        questions = Question.query.filter_by(course_id=course.id).all()
        return render_template("admin/quiz_form.html", course=course, questions=questions)

    @app.route("/admin/questions/<int:question_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_question(question_id):
        q = Question.query.get_or_404(question_id)
        course_id = q.course_id
        db.session.delete(q)
        db.session.commit()
        flash("Question deleted.", "info")
        return redirect(url_for("admin_quiz", course_id=course_id))

    # ── Admin: Results Tracker ────────────────────────────────────────

    @app.route("/admin/scores")
    @admin_required
    def admin_scores():
        # All attempts for Detailed History tab
        attempts = (
            QuizAttempt.query
            .join(User)
            .join(Course)
            .order_by(QuizAttempt.taken_at.desc())
            .all()
        )

        # Aggregated data for Overview tab
        enrollments = Enrollment.query.all()
        overview = []
        for enrollment in enrollments:
            user = enrollment.user
            course = enrollment.course
            modules = sorted(course.modules, key=lambda m: m.order_index)
            total_modules = len(modules)

            if total_modules == 0:
                overview.append({
                    "user": user,
                    "course": course,
                    "completed": 0,
                    "total": 0,
                    "progress": 0,
                    "best_avg": 0,
                    "status": "No Content",
                })
                continue

            # Check modules completed by user
            module_ids = [m.id for m in modules]
            if module_ids:
                completed = ModuleCompletion.query.filter_by(user_id=user.id).filter(ModuleCompletion.module_id.in_(module_ids)).count()
            else:
                completed = 0

            # Get best quiz attempt for course
            best_course_attempt = (
                QuizAttempt.query
                .filter_by(user_id=user.id, course_id=course.id)
                .order_by(QuizAttempt.score.desc())
                .first()
            )

            progress = math.floor((completed / total_modules) * 100) if total_modules > 0 else 0
            best_avg = best_course_attempt.score if best_course_attempt else 0

            if best_course_attempt and best_course_attempt.passed:
                status = "Completed"
            elif completed > 0 or best_course_attempt:
                status = "In Progress"
            else:
                status = "Not Started"

            overview.append({
                "user": user,
                "course": course,
                "completed": completed,
                "total": total_modules,
                "progress": progress,
                "best_avg": best_avg,
                "status": status,
            })

        # Stats
        total_passed = sum(1 for a in attempts if a.passed)
        pass_rate = round((total_passed / len(attempts)) * 100) if attempts else 0

        return render_template(
            "admin/scores.html",
            attempts=attempts,
            overview=overview,
            pass_rate=pass_rate,
        )

    # ── Employee: Dashboard ──────────────────────────────────────────

    @app.route("/dashboard")
    @employee_required
    def employee_dashboard():
        enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
        courses_data = []
        for enrollment in enrollments:
            course = enrollment.course
            modules = sorted(course.modules, key=lambda m: m.order_index)
            total = len(modules)
            passed_ids = get_module_progress(current_user.id, course)
            completed = len(passed_ids)
            progress = math.floor((completed / total) * 100) if total > 0 else 0
            
            best_attempt = QuizAttempt.query.filter_by(user_id=current_user.id, course_id=course.id).order_by(QuizAttempt.score.desc()).first()

            courses_data.append({
                "course": course,
                "modules": modules,
                "total": total,
                "completed": completed,
                "progress": progress,
                "passed_ids": passed_ids,
                "best_attempt": best_attempt,
            })
        return render_template("employee/dashboard.html", courses_data=courses_data)

    # ── Employee: Module View (Read Lesson + Take Quiz) ──────────────

    @app.route("/module/<int:module_id>")
    @employee_required
    def employee_module(module_id):
        module = Module.query.get_or_404(module_id)
        course = module.course

        # Check enrollment
        enrollment = Enrollment.query.filter_by(
            user_id=current_user.id, course_id=course.id
        ).first()
        if not enrollment:
            abort(403)

        # Check sequential access
        if not can_access_module(current_user.id, module):
            flash("You need to pass the previous module first.", "warning")
            return redirect(url_for("employee_dashboard"))

        content_html = markdown2.markdown(
            module.content_md,
            extras=["fenced-code-blocks", "tables", "strike", "task_list"]
        )

        completed = ModuleCompletion.query.filter_by(
            user_id=current_user.id, module_id=module.id
        ).first() is not None

        # Find next module
        ordered_modules = sorted(course.modules, key=lambda m: m.order_index)
        idx = next((i for i, m in enumerate(ordered_modules) if m.id == module.id), None)
        next_module = ordered_modules[idx + 1] if idx is not None and idx + 1 < len(ordered_modules) else None

        return render_template(
            "employee/module_view.html",
            module=module,
            course=course,
            content_html=content_html,
            completed=completed,
            next_module=next_module,
        )

    # ── Employee: Submit Quiz / Complete Module ────────────────────

    @app.route("/module/<int:module_id>/complete", methods=["POST"])
    @employee_required
    def employee_complete_module(module_id):
        module = Module.query.get_or_404(module_id)
        
        # Check permissions
        if not can_access_module(current_user.id, module):
            abort(403)
            
        existing = ModuleCompletion.query.filter_by(user_id=current_user.id, module_id=module.id).first()
        if not existing:
            mc = ModuleCompletion(user_id=current_user.id, module_id=module.id)
            db.session.add(mc)
            db.session.commit()
            
        # Find next module
        course = module.course
        ordered_modules = sorted(course.modules, key=lambda m: m.order_index)
        idx = next((i for i, m in enumerate(ordered_modules) if m.id == module.id), None)
        next_module = ordered_modules[idx + 1] if idx is not None and idx + 1 < len(ordered_modules) else None

        if next_module:
            return redirect(url_for("employee_module", module_id=next_module.id))
        else:
            return redirect(url_for("employee_course_quiz", course_id=course.id))

    @app.route("/course/<int:course_id>/quiz", methods=["GET"])
    @employee_required
    def employee_course_quiz(course_id):
        course = Course.query.get_or_404(course_id)
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        if not enrollment:
            abort(403)

        passed_ids = get_module_progress(current_user.id, course)
        if len(passed_ids) < len(course.modules):
            flash("You must complete all modules before taking the final quiz.", "warning")
            return redirect(url_for("employee_dashboard"))

        questions = Question.query.filter_by(course_id=course_id).all()
        best_attempt = QuizAttempt.query.filter_by(user_id=current_user.id, course_id=course_id).order_by(QuizAttempt.score.desc()).first()

        return render_template(
            "employee/course_quiz.html",
            course=course,
            questions=questions,
            best_attempt=best_attempt,
        )

    @app.route("/course/<int:course_id>/quiz/submit", methods=["POST"])
    @employee_required
    def employee_submit_course_quiz(course_id):
        course = Course.query.get_or_404(course_id)
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        if not enrollment:
            abort(403)

        passed_ids = get_module_progress(current_user.id, course)
        if len(passed_ids) < len(course.modules):
            abort(403)

        questions = Question.query.filter_by(course_id=course_id).all()
        if not questions:
            flash("This course has no quiz questions.", "warning")
            return redirect(url_for("employee_dashboard"))

        correct = 0
        total = len(questions)
        results = []

        for q in questions:
            answer = request.form.get(f"q_{q.id}", "").strip().lower()
            is_correct = answer == q.correct_option
            if is_correct:
                correct += 1
            results.append({
                "question": q,
                "selected": answer,
                "is_correct": is_correct,
            })

        score = math.floor((correct / total) * 100) if total > 0 else 0
        passed = score >= Config.PASS_THRESHOLD

        attempt = QuizAttempt(user_id=current_user.id, course_id=course_id, score=score, passed=passed)
        db.session.add(attempt)
        db.session.commit()

        return render_template(
            "employee/quiz_result.html",
            course=course,
            score=score,
            passed=passed,
            correct=correct,
            total=total,
            results=results,
        )

    # ── Error Handlers ───────────────────────────────────────────────

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="Access Denied"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page Not Found"), 404

    return app


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
