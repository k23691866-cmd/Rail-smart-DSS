import random
import string
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func

from app import db, bcrypt
from app.models import User, Train, Booking

main = Blueprint("main", __name__)


# ────────────────────────────── Helpers ──────────────────────────────
def generate_pnr():
    while True:
        pnr = "".join(random.choices(string.digits, k=10))
        if not Booking.query.filter_by(pnr=pnr).first():
            return pnr


def admin_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)

    return wrapper


# ────────────────────────────── Public ──────────────────────────────
@main.route("/")
def index():
    trains = Train.query.limit(6).all()
    return render_template("index.html", trains=trains)


# ────────────────────────────── Auth ──────────────────────────────
@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
        else:
            hashed = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(username=username, email=email, password_hash=hashed)
            db.session.add(user)
            db.session.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("main.login"))

    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))
        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("main.index"))


# ────────────────────────────── Dashboard ──────────────────────────────
@main.route("/dashboard")
@login_required
def dashboard():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    total_trips = len(user_bookings)
    active_trips = sum(1 for b in user_bookings if b.status == "CONFIRMED")
    total_spent = sum(b.total_fare for b in user_bookings if b.status != "CANCELLED")
    recent = user_bookings[:5]

    stats = {
        "total_trips": total_trips,
        "active_trips": active_trips,
        "total_spent": round(total_spent, 2),
        "trains_available": Train.query.count(),
    }

    if current_user.role == "admin":
        return redirect(url_for("main.admin"))

    return render_template("dashboard.html", stats=stats, recent=recent)


# ────────────────────────────── Booking ──────────────────────────────
@main.route("/booking", methods=["GET", "POST"])
@login_required
def booking():
    trains = Train.query.all()

    if request.method == "POST":
        train_id = request.form.get("train_id", type=int)
        passenger_name = request.form.get("passenger_name", "").strip()
        passenger_age = request.form.get("passenger_age", type=int)
        passenger_gender = request.form.get("passenger_gender", "").strip()
        seats = request.form.get("seats_booked", 1, type=int)

        train = Train.query.get(train_id)

        if not train:
            flash("Train not found.", "danger")
        elif not passenger_name or not passenger_age or not passenger_gender:
            flash("Please fill all passenger details.", "danger")
        elif passenger_age <= 0 or passenger_age > 120:
            flash("Invalid age.", "danger")
        elif seats < 1 or seats > 6:
            flash("You can book 1-6 seats per transaction.", "danger")
        elif train.available_seats < seats:
            flash(f"Only {train.available_seats} seats available on {train.train_name}.", "danger")
        else:
            total_fare = train.fare * seats
            new_booking = Booking(
                pnr=generate_pnr(),
                user_id=current_user.id,
                train_id=train.id,
                passenger_name=passenger_name,
                passenger_age=passenger_age,
                passenger_gender=passenger_gender,
                seats_booked=seats,
                total_fare=total_fare,
                status="CONFIRMED",
            )
            train.available_seats -= seats
            db.session.add(new_booking)
            db.session.commit()
            flash(f"🎉 Booking confirmed! Your PNR: {new_booking.pnr}", "success")
            return redirect(url_for("main.my_bookings"))

    return render_template("booking.html", trains=trains)


@main.route("/my-bookings")
@login_required
def my_bookings():
    bookings = (
        Booking.query
        .filter_by(user_id=current_user.id)
        .order_by(Booking.booking_date.desc())
        .all()
    )
    return render_template("my_bookings.html", bookings=bookings)


@main.route("/pnr-status", methods=["GET", "POST"])
def pnr_status():
    booking = None
    if request.method == "POST":
        pnr = request.form.get("pnr", "").strip()
        booking = Booking.query.filter_by(pnr=pnr).first()
        if not booking:
            flash("No booking found for that PNR.", "danger")
    return render_template("pnr_status.html", booking=booking)


# ═══════════════════════════════════════════════════════════════════════════
#  🎟️ CANCEL TICKET — Single Definition (No Duplicate ✅)
# ═══════════════════════════════════════════════════════════════════════════

@main.route("/cancel/<int:booking_id>", methods=["POST"])
@login_required
def cancel_ticket(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != current_user.id and current_user.role != "admin":
        flash("❌ You cannot cancel this booking.", "danger")
        return redirect(url_for("main.my_bookings"))

    if booking.status == "CANCELLED":
        flash("⚠️ This booking is already cancelled.", "warning")
        return redirect(request.referrer or url_for("main.my_bookings"))

    refund_amount = round(booking.total_fare * 0.80, 2)
    cancellation_charge = round(booking.total_fare - refund_amount, 2)

    booking.status = "CANCELLED"
    booking.train.available_seats += booking.seats_booked
    db.session.commit()

    flash(
        f"✅ Booking {booking.pnr} cancelled. "
        f"Refund: ₹{refund_amount} (Cancellation charge: ₹{cancellation_charge})",
        "success"
    )
    return redirect(request.referrer or url_for("main.my_bookings"))


@main.route("/cancel-ticket", methods=["GET", "POST"])
@login_required
def cancel_ticket_page():
    booking = None
    refund_info = None

    if request.method == "POST":
        pnr = request.form.get("pnr", "").strip()

        if not pnr:
            flash("⚠️ Please enter a PNR number.", "warning")
        elif len(pnr) != 10 or not pnr.isdigit():
            flash("❌ PNR must be exactly 10 digits.", "danger")
        else:
            booking = Booking.query.filter_by(pnr=pnr, user_id=current_user.id).first()

            if not booking:
                flash("❌ No booking found for that PNR under your account.", "danger")
            elif booking.status == "CANCELLED":
                flash("⚠️ This booking is already cancelled.", "warning")
            else:
                refund_amount = round(booking.total_fare * 0.80, 2)
                cancellation_charge = round(booking.total_fare - refund_amount, 2)
                refund_info = {
                    "refund": refund_amount,
                    "charge": cancellation_charge,
                    "total": booking.total_fare,
                }

    return render_template("cancel_ticket.html", booking=booking, refund_info=refund_info)


# ────────────────────────────── Admin ──────────────────────────────
@main.route("/admin")
@login_required
@admin_required
def admin():
    users = User.query.order_by(User.created_at.desc()).all()
    trains = Train.query.all()
    bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(20).all()

    total_revenue = db.session.query(func.coalesce(func.sum(Booking.total_fare), 0)).filter(
        Booking.status == "CONFIRMED"
    ).scalar()

    stats = {
        "total_users": len(users),
        "total_trains": len(trains),
        "total_bookings": Booking.query.count(),
        "total_revenue": round(float(total_revenue), 2),
    }
    return render_template("admin.html", users=users, trains=trains, bookings=bookings, stats=stats)


@main.route("/admin/add-train", methods=["POST"])
@login_required
@admin_required
def add_train():
    data = request.form
    tn = data.get("train_number", "").strip()

    if not tn or not data.get("train_name") or not data.get("source") or not data.get("destination"):
        flash("Please fill all required train fields.", "danger")
        return redirect(url_for("main.admin"))

    if Train.query.filter_by(train_number=tn).first():
        flash("Train number already exists.", "danger")
        return redirect(url_for("main.admin"))

    seats = int(data.get("total_seats", 100) or 100)
    fare = float(data.get("fare", 0) or 0)

    train = Train(
        train_number=tn,
        train_name=data.get("train_name").strip(),
        source=data.get("source").strip(),
        destination=data.get("destination").strip(),
        departure_time=data.get("departure_time", "00:00"),
        arrival_time=data.get("arrival_time", "00:00"),
        total_seats=seats,
        available_seats=seats,
        fare=fare,
    )
    db.session.add(train)
    db.session.commit()
    flash(f"Train {train.train_name} added successfully.", "success")
    return redirect(url_for("main.admin"))


@main.route("/admin/delete-train/<int:train_id>", methods=["POST"])
@login_required
@admin_required
def delete_train(train_id):
    train = Train.query.get_or_404(train_id)
    active = Booking.query.filter_by(train_id=train_id).filter(Booking.status == "CONFIRMED").count()
    if active:
        flash("Cannot delete train with active bookings.", "danger")
    else:
        db.session.delete(train)
        db.session.commit()
        flash("Train deleted.", "info")
    return redirect(url_for("main.admin"))


@main.route("/admin/toggle-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot modify your own role.", "danger")
        return redirect(url_for("main.admin"))
    user.role = "user" if user.role == "admin" else "admin"
    db.session.commit()
    flash(f"{user.username} is now {user.role}.", "info")
    return redirect(url_for("main.admin"))


# ────────────────────────────── Reports ──────────────────────────────
@main.route("/reports")
@login_required
@admin_required
def reports():
    confirmed = Booking.query.filter_by(status="CONFIRMED").all()
    cancelled = Booking.query.filter_by(status="CANCELLED").all()

    revenue_by_train = (
        db.session.query(Train.train_name, func.sum(Booking.total_fare), func.count(Booking.id))
        .join(Booking, Booking.train_id == Train.id)
        .filter(Booking.status == "CONFIRMED")
        .group_by(Train.id)
        .order_by(func.sum(Booking.total_fare).desc())
        .all()
    )

    total_revenue = sum(b.total_fare for b in confirmed)
    total_refund = sum(b.total_fare for b in cancelled)

    summary = {
        "confirmed_count": len(confirmed),
        "cancelled_count": len(cancelled),
        "total_revenue": round(total_revenue, 2),
        "total_refund": round(total_refund, 2),
        "net_revenue": round(total_revenue - total_refund, 2),
    }

    return render_template("reports.html", summary=summary, revenue_by_train=revenue_by_train)


# ────────────────────────────── API (AJAX) ──────────────────────────────
@main.route("/api/train/<int:train_id>")
def api_train(train_id):
    train = Train.query.get_or_404(train_id)
    return jsonify({
        "id": train.id,
        "name": train.train_name,
        "number": train.train_number,
        "source": train.source,
        "destination": train.destination,
        "fare": train.fare,
        "available_seats": train.available_seats,
        "departure": train.departure_time,
        "arrival": train.arrival_time,
    })