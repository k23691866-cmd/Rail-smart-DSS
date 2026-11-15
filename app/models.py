from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="passenger", lazy=True, cascade="all, delete-orphan")


class Train(db.Model):
    __tablename__ = "trains"

    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.String(10), unique=True, nullable=False)
    train_name = db.Column(db.String(120), nullable=False)
    source = db.Column(db.String(80), nullable=False)
    destination = db.Column(db.String(80), nullable=False)
    departure_time = db.Column(db.String(10), nullable=False)
    arrival_time = db.Column(db.String(10), nullable=False)
    total_seats = db.Column(db.Integer, default=100, nullable=False)
    available_seats = db.Column(db.Integer, default=100, nullable=False)
    fare = db.Column(db.Float, nullable=False, default=0.0)

    bookings = db.relationship("Booking", backref="train", lazy=True)


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    pnr = db.Column(db.String(10), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    train_id = db.Column(db.Integer, db.ForeignKey("trains.id"), nullable=False)
    passenger_name = db.Column(db.String(120), nullable=False)
    passenger_age = db.Column(db.Integer, nullable=False)
    passenger_gender = db.Column(db.String(10), nullable=False)
    seats_booked = db.Column(db.Integer, default=1, nullable=False)
    total_fare = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(20), default="CONFIRMED", nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)