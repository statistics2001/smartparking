from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class Slot(db.Model):
    __tablename__ = 'slots'
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(255), nullable=False, default="free")
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id', ondelete="SET NULL"), unique=True, nullable=True)
    driver = db.relationship('Drivers', back_populates='slot')

class Drivers(db.Model):
    __tablename__ = 'drivers'
    id = db.Column(db.Integer, primary_key=True)
    ownerName = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    vehicle_name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.String(255), unique=True, nullable=False)
    bankNumber = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=False, default="user")
    created_at = db.Column(db.DateTime, default=datetime.now)
    entry_time = db.Column(db.DateTime, nullable=True)
    exit_time = db.Column(db.DateTime, nullable=True)
    slot = db.relationship('Slot', back_populates='driver', uselist=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Feedbacks(db.Model):
    __tablename__ = 'feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    Feedback_by = db.Column(db.String(255), nullable=False)
    Feedback_desc = db.Column(db.String(255), nullable=False)
    rate = db.Column(db.Integer, nullable=False)

class Bookings(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    slot_number = db.Column(db.String(50))
    ownerName = db.Column(db.String(100))
    vehicle_name = db.Column(db.String(100))
    entry_time = db.Column(db.DateTime)  
    exit_time = db.Column(db.DateTime)   

    def __init__(self, user_id, slot_number, ownerName, vehicle_name, entry_time, exit_time):
        self.slot_number = slot_number
        self.ownerName = ownerName
        self.vehicle_name = vehicle_name
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.user_id = user_id
