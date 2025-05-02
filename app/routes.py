from flask import request, session, jsonify
from flask import request, session, jsonify,make_response
from app.extensions import db
from app.models import Slot, Drivers, Feedbacks, Bookings
from datetime import datetime
from math import ceil
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
from dotenv import load_dotenv

def init_routes(app):

    load_dotenv('.env')
    # Set up the Stripe publishable key
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    print("Stripe API Key:", stripe.api_key)
    
    @app.route('/')
    def index():
        return "Smart Parking API"
    
    # Authentication Routes
    @app.route('/login', methods=['POST'])
    def login():
        user_id = request.json.get('user_id')
        password = request.json.get('password')
        
        driver = Drivers.query.filter_by(user_id=user_id).first()
        
        if driver and driver.check_password(password):
            session['user_id'] = driver.user_id
            return jsonify({
                "message": "Login Success",
                "user": {
                    "user_id": driver.user_id,
                    "vehicleName": driver.vehicle_name,
                    "ownerName": driver.ownerName,
                    "bankNumber": driver.bankNumber,
                    "role": driver.role,
                    "slot": driver.slot.slot_number if driver.slot else None
                }
            })
        else:
            return jsonify({"message": "Login Failed"}), 401

    @app.route('/register', methods=['POST'])
    def register():
        try:
            data = request.json
            ownerName = data.get('ownerName')
            password = data.get('password')
            vehicle_name = data.get('vehicle_name')
            user_id = data.get('user_id')
            bankNumber = data.get('bankNumber')

            if not all([ownerName, password, vehicle_name, user_id, bankNumber]):
                return jsonify({"error": "All fields are required"}), 400

            existing_driver = Drivers.query.filter_by(user_id=user_id).first()
            if existing_driver:
                return jsonify({"error": "User ID already exists"}), 409

            driver = Drivers(
                ownerName=ownerName,
                vehicle_name=vehicle_name,
                user_id=user_id,
                bankNumber=bankNumber
            )
            driver.set_password(password)

            db.session.add(driver)
            db.session.commit()

            return jsonify({"message": "Driver Registered"}), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/logout', methods=['POST'])
    def logout():
        session.clear()
        return jsonify({"message": "Logout Success"})

    # Slot Routes
    @app.route('/get-slots', methods=['GET'])
    def get_slots():
        try:
            slots = Slot.query.all()
            slot_list = [
                {"id": slot.id, "slot_number": slot.slot_number, "status": slot.status}
                for slot in slots
            ]
            return jsonify(slot_list), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/get-booked-slot/<int:user_id>', methods=['GET'])
    def get_booked_slot(user_id):
        try:
            driver = Drivers.query.filter_by(user_id=user_id).first()
            if not driver:
                return jsonify({"error": "Driver not found"}), 404

            slot = Slot.query.filter_by(driver_id=driver.id).first()
            if not slot:
                return jsonify({"error": "No booked slot found"}), 404

            return jsonify({
                "slotId": slot.id,
                "slot_number": slot.slot_number,
                "status": slot.status,
                "bookedAt": driver.entry_time.isoformat() if driver.entry_time else None
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/get-slot/<int:slot_id>', methods=['GET'])
    def get_slot(slot_id):
        try:
            slot = (
                db.session.query(
                    Slot.id,
                    Slot.slot_number,
                    Slot.status,
                    Drivers.user_id
                )
                .outerjoin(Drivers, Slot.driver_id == Drivers.id)
                .filter(Slot.id == slot_id)
                .first()
            )

            if not slot:
                return jsonify({"error": "Slot not found"}), 404

            slot_data = {
                "id": slot.id,
                "slot_number": slot.slot_number,
                "status": slot.status,
                "driver_id": str(slot.user_id) if slot.user_id else None
            }

            return jsonify(slot_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/get-slots-args', methods=['GET'])
    def get_slots_args():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        slots_query = Slot.query.paginate(page=page, per_page=per_page, error_out=False)
        slots = slots_query.items

        slots_data = []
        for slot in slots:
            slots_data.append({
                'id': slot.id,
                'slot_number': slot.slot_number,
                'status': slot.status,
                'driver_id': slot.driver.id if slot.driver else None,
            })

        total_slots = Slot.query.count()
        total_pages = ceil(total_slots / per_page)

        response = {
            'slots': slots_data,
            'total': total_slots,
            'pages': total_pages,
            'current_page': page,
        }

        return jsonify(response), 200

    @app.route('/add-slot', methods=['POST'])
    def add_slot():    
        data = request.json
        slot_number = data.get('slot_number')
        if not slot_number:
            return jsonify({"error": "Slot number is required"}), 400

        existing_slot = Slot.query.filter_by(slot_number=slot_number).first()
        if existing_slot:
            return jsonify({"error": "Slot already exists"}), 409

        new_slot = Slot(slot_number=slot_number, status="free")
        db.session.add(new_slot)
        db.session.commit()

        return jsonify({"message": "Slot added successfully"}), 201

    @app.route('/edit-slot/<int:slot_id>', methods=['PUT'])
    def edit_slot(slot_id):
        data = request.json
        slot_number = data.get('slot_number')
        status = data.get('status')

        if not slot_number:
            return jsonify({"error": "Slot number is required"}), 400

        slot = Slot.query.get(slot_id)
        if not slot:
            return jsonify({"error": "Slot not found"}), 404

        slot.slot_number = slot_number
        slot.status = status
        db.session.commit()

        return jsonify({"message": "Slot updated successfully"}), 200

    @app.route('/delete-slot/<int:slot_id>', methods=['DELETE'])
    def delete_slot(slot_id):
        slot = Slot.query.get(slot_id)
        if not slot:
            return jsonify({"error": "Slot not found"}), 404

        db.session.delete(slot)
        db.session.commit()

        return jsonify({"message": "Slot deleted successfully"}), 200

    @app.route('/book-slot/<int:slot_id>/<int:user_id>', methods=['POST'])
    def book_slot(slot_id, user_id):
        try:
            slot = Slot.query.get(slot_id)
            if not slot:
                return jsonify({"error": "Slot not found"}), 404
            
            if slot.status == "occupied":
                return jsonify({"error": "Slot already booked"}), 400
            
            driver = Drivers.query.filter_by(user_id=user_id).first()
            if not driver:
                return jsonify({"error": "Driver not found"}), 404
            
            slot.status = "occupied"
            slot.driver_id = driver.id
            driver.entry_time = datetime.now()

            db.session.commit()

            return jsonify({"message": "Slot booked successfully", "entry_time": driver.entry_time})

        except Exception as e:
            db.session.rollback() 
            print(f"Error occurred: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route('/cancel-slot/<int:slot_id>', methods=['POST'])
    def cancel_slot(slot_id):
        try:
            slot = Slot.query.get(slot_id)

            if not slot:
                return jsonify({"error": "Slot not found"}), 404
    
            slot.status = "free"
            slot.driver_id = None
            db.session.commit()

            return jsonify({"message": "Slot cancelled successfully"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/exit-slot/<int:slot_id>/<int:user_id>', methods=['POST'])
    def exit_slot(slot_id, user_id):
        try:
            driver = Drivers.query.filter_by(user_id=user_id).first()
            if not driver:
                return jsonify({"error": "Driver not found"}), 404

            slot = Slot.query.filter_by(id=slot_id, driver_id=driver.id).first()
            if not slot:
                return jsonify({"error": "Slot not found or not booked by this user"}), 404

            driver.exit_time = datetime.now()

            new_booking = Bookings(
                slot_number=slot.slot_number,
                user_id=driver.user_id,
                ownerName=driver.ownerName,
                vehicle_name=driver.vehicle_name,
                entry_time=driver.entry_time,
                exit_time=driver.exit_time  
            )
            db.session.add(new_booking)

            slot.status = "free"
            slot.driver_id = None

            db.session.commit()

            return jsonify({"message": "Slot exited successfully, booking record created!"}), 200

        except Exception as e:
            db.session.rollback()  
            print(f"Error: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # Booking Routes
    @app.route('/booking-history', methods=['GET'])
    def get_booking_history():
        try:
            user_id = request.args.get('user_id', type=int)

            if user_id == 1000:
                bookings = Bookings.query.all()
            else:
                bookings = Bookings.query.filter_by(user_id=user_id).all()

            booking_data = []
            for booking in bookings:
                booking_data.append({
                    "slot_number": booking.slot_number,
                    "user_id": booking.user_id,
                    "ownerName": booking.ownerName,
                    "vehicle_name": booking.vehicle_name,
                    "entry_time": booking.entry_time,
                    "exit_time": booking.exit_time,
                })

            return jsonify(booking_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Feedback Routes
    @app.route('/submit-feedback', methods=['POST'])
    def submit_feedback():
        try:
            data = request.json  
            feedback_by = data.get("feedback_by")
            feedback_desc = data.get("feedback_desc")
            rate = data.get("rate")

            if not feedback_by or not feedback_desc or rate is None:
                return jsonify({"error": "Missing required fields"}), 400

            new_feedback = Feedbacks(
                Feedback_by=feedback_by,
                Feedback_desc=feedback_desc,
                rate=rate
            )
            db.session.add(new_feedback)
            db.session.commit()

            return jsonify({"message": "Feedback submitted successfully!"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # User Routes
    @app.route('/get-user-id/<string:user_id>', methods=['GET'])
    def get_user_id(user_id):
        driver = Drivers.query.filter_by(user_id=user_id).first()
        print(driver)
        if not driver:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({"id": driver.id}), 200

    @app.route('/update-user', methods=['POST'])
    def update_user():
        try:
            data = request.get_json()
            print(data)
            user_id = data.get('user_id')
            owner_name = data.get('ownerName')
            vehicle_name = data.get('vehicleName')
            bank_number = data.get('bankNumber')
            old_password = data.get('oldPassword')
            new_password = data.get('newPassword')

            driver = Drivers.query.filter_by(user_id=user_id).first()
            if not driver:
                return jsonify({"error": "User not found"}), 404

            if old_password and not check_password_hash(driver.password, old_password):
                return jsonify({"error": "Incorrect old password"}), 401

            driver.ownerName = owner_name
            driver.vehicle_name = vehicle_name
            driver.bankNumber = bank_number
            if new_password:
                driver.password = generate_password_hash(new_password)

            db.session.commit()
            return jsonify({"success": True, "message": "User information updated successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/drivers', methods=['GET'])
    def get_drivers():
        try:
            drivers = Drivers.query.all()
            driver_list = []
            
            for driver in drivers:
                driver_list.append({
                    "id": driver.id,
                    "ownerName": driver.ownerName,
                    "vehicle_name": driver.vehicle_name,
                    "user_id": driver.user_id,
                    "entry_time": driver.entry_time,
                    "exit_time": driver.exit_time,
                    "created_at": driver.created_at,
                    "BankNumber": driver.bankNumber,
                    "slot_id": driver.slot.id if driver.slot else None,  
                    "slot_number": driver.slot.slot_number if driver.slot else None,  
                    "slot_status": driver.slot.status if driver.slot else None  
                })
            
            return jsonify(driver_list), 200
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/get-feedbacks', methods=['GET'])
    def get_feedbacks():
        try:
            user_id = request.args.get("user_id")
            
            if not user_id:
                return jsonify({"error": "User ID is required"}), 400

            if user_id != "1000":
                return jsonify({"error": "Unauthorized access"}), 403

            feedbacks = Feedbacks.query.all()
            feedback_list = [
                {"id": f.id, "feedback_by": f.Feedback_by, "feedback_desc": f.Feedback_desc, "rate": f.rate}
                for f in feedbacks
            ]

            return jsonify({"feedbacks": feedback_list}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    @app.route('/calculate-fee/<int:user_id>', methods=['GET'])
    def calculate_fee(user_id):
        # Retrieve the most recent booking for the user
        booking = Bookings.query.filter_by(user_id=user_id).order_by(Bookings.entry_time.desc()).first()

        if not booking:
            return jsonify({'message': 'No booking found for the user'}), 404

        # Calculate the time difference between entry and exit
        if booking.entry_time and booking.exit_time:
            time_diff = booking.exit_time - booking.entry_time
            # Convert time_diff to hours (you can adjust the calculation logic as needed)
            hours = time_diff.total_seconds() / 3600
            tarif = 1.2
            amount = hours * tarif

            return jsonify({'amount': amount, 'message': 'Fee calculated successfully'}), 200
        else:
            return jsonify({'message': 'Entry time or exit time not available'}), 400
        
    @app.route('/get-booking-details/<int:user_id>', methods=['GET'])
    def get_booking_details(user_id):
        # Retrieve the most recent booking for the user
        booking = Bookings.query.filter_by(user_id=user_id).order_by(Bookings.entry_time.desc()).first()

        if not booking:
            return jsonify({'message': 'No booking found for the user'}), 404

        return jsonify({
            'entry_time': booking.entry_time.isoformat() if booking.entry_time else None,
            'exit_time': booking.exit_time.isoformat() if booking.exit_time else None,
            'tarif': booking.tarif if hasattr(booking, 'tarif') else 5  # Default to 5 if tarif not set
        }), 200
    
    @app.route('/config', methods=['GET'])
    def get_config():
        return jsonify({
            'publishableKey': os.getenv('STRIPE_PUBLISHABLE_KEY')
        })

    @app.route('/create-payment-intent', methods=['POST'])
    def create_payment_intent():
        try:
            data = request.get_json()
            amount = data['amount']
            
            # Validate amount
            if not isinstance(amount, int) or amount <= 0:
                return jsonify({'error': 'Invalid amount'}), 400

            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                automatic_payment_methods={
                    'enabled': True,
                },
                metadata={
                    'integration_check': 'accept_a_payment'
                }
            )
            print('Data',intent)
            return jsonify({
                'clientSecret': intent.client_secret
            })
            
            
        except stripe.error.StripeError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Server error'}), 500

    @app.after_request
    def add_security_headers(response):
        response.headers['Content-Security-Policy'] = "script-src 'self' https://js.stripe.com 'unsafe-inline'"
        return response
    


    @app.route('/transactions', methods=['GET'])  # Added /api prefix
    def get_transactions():
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({"success": False, "error": "user_id parameter is required"}), 400
            
            # Fixed typo from "1000" to "100"
            query = Bookings.query if user_id == "1000" else Bookings.query.filter_by(user_id=user_id)
            bookings = query.all()
            
            transactions = []
            for booking in bookings:
                # Handle null exit_time case
                exit_time = booking.exit_time or datetime.utcnow()
                duration_hours = (exit_time - booking.entry_time).total_seconds() / 3600
                
                transactions.append({
                    "transaction_id": booking.id,
                    "user_id": booking.user_id,
                    "slot_number": booking.slot_number,
                    "vehicle_name": booking.vehicle_name,
                    "entry_time": booking.entry_time.isoformat(),
                    "exit_time": booking.exit_time.isoformat() if booking.exit_time else None,
                    "duration_hours": round(duration_hours, 2),
                    "amount": round(duration_hours * 1.2, 2),
                    "status": "completed" if booking.exit_time else "pending"
                })
            
            response = make_response(jsonify({
                "success": True,
                "transactions": transactions,
                "count": len(transactions)
            }))
            response.headers['Content-Type'] = 'application/json'
            return response
            
        except Exception as e:
            error_response = make_response(jsonify({
                "success": False,
                "error": str(e)
            }), 500)
            error_response.headers['Content-Type'] = 'application/json'
            return error_response
