from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from config import Config
import functools

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(20), unique=True, nullable=False)
    blood_group = db.Column(db.String(3), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    last_donation_date = db.Column(db.Date)
    is_available = db.Column(db.Boolean, default=True)
    photo_path = db.Column(db.String(255))
    document_path = db.Column(db.String(255))

class BloodRequest(db.Model):
    __tablename__ = 'blood_requests'
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    blood_group = db.Column(db.String(3), nullable=False)
    units_required = db.Column(db.Integer, nullable=False)
    hospital_name = db.Column(db.String(100), nullable=False)
    urgency = db.Column(db.String(20), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    request_date = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    status = db.Column(db.String(20), default='pending')
    requester = db.relationship('User', backref='blood_requests')

# DonationDrive model
class DonationDrive(db.Model):
    __tablename__ = 'donation_drives'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    status = db.Column(db.String(20), default=None)

class DonationHistory(db.Model):
    __tablename__ = 'donation_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    donation_date = db.Column(db.Date, nullable=False)
    amount_ml = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(255))
    drive_id = db.Column(db.Integer, db.ForeignKey('donation_drives.id'))
    drive = db.relationship('DonationDrive', backref='donations')
    user = db.relationship('User', backref='donation_history')

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(role=None):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        confirm_password = request.form['confirm_password']
        phone = request.form['phone']
        if not phone.isdigit() or len(phone) != 10:
            flash('Phone number must be exactly 10 digits.', 'danger')
            return render_template('register.html')
        
        try:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Username or email already exists.', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        user = User.query.filter_by(username=username, role=role).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'coordinator':
                return redirect(url_for('coordinator_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username, password, or role.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required()
def user_dashboard():
    user = User.query.get(session['user_id'])
    profile = user.profile
    
    if not profile:
        flash('Please complete your profile.', 'warning')
        return redirect(url_for('complete_profile'))
    
    return render_template('dashboard.html', user=user, profile=profile)

@app.route('/admin')
@login_required('admin')
def admin_dashboard():
    # Get the requested section from the query parameters, default to 'users'
    current_section = request.args.get('section', 'users')
    print(f"Debug: Current section is {current_section}") # Debug print

    users = []
    blood_requests = []
    donation_drives = []
    reports = []
    # --- Reports Data ---
    available_donors = UserProfile.query.filter_by(is_available=True).count()
    total_drives = DonationDrive.query.count()
    total_units_donated = 0  # TODO: Replace with actual sum from DonationHistory if available
    total_requests = BloodRequest.query.count()
    pending_requests = BloodRequest.query.filter_by(status='pending').count()
    fulfilled_requests = BloodRequest.query.filter_by(status='fulfilled').count() if hasattr(BloodRequest, 'status') else 0
    rejected_requests = BloodRequest.query.filter_by(status='rejected').count() if hasattr(BloodRequest, 'status') else 0

    # Example: Blood group distribution for donors
    blood_group_distribution = {bg: UserProfile.query.filter_by(blood_group=bg).count() for bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']}
    # Example: Requests by blood group
    requests_by_group = {bg: BloodRequest.query.filter_by(blood_group=bg).count() for bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']}

    # Example: Monthly trends (dummy data, replace with real aggregation)
    monthly_trends = []  # TODO: Fill with real data
    donor_availability_trend = []  # TODO: Fill with real data

    # Example: Recent blood requests
    recent_blood_requests = [
        {
            'id': r.id,
            'requester': r.requester.username if r.requester else '',
            'blood_group': r.blood_group,
            'units_required': r.units_required,
            'status': r.status,
            'request_date': r.request_date.strftime('%Y-%m-%d') if r.request_date else ''
        }
        for r in BloodRequest.query.order_by(BloodRequest.request_date.desc()).limit(5).all()
    ]
    # Example: Recent donation drives
    recent_drives = [
        {
            'name': d.name,
            'date': d.date.strftime('%Y-%m-%d') if d.date else '',
            'location': d.location,
            'participation': 0  # TODO: Replace with actual participation count
        }
        for d in DonationDrive.query.order_by(DonationDrive.date.desc()).limit(5).all()
    ]
    # Example: Top donors (dummy data, replace with real aggregation)
    top_donors = [
        {'name': 'John Doe', 'donations': 5},
        {'name': 'Jane Smith', 'donations': 4},
        {'name': 'Alice Brown', 'donations': 3},
    ]
    # Example: Actionable insights
    actionable_insights = [
        'O- blood group is low in stock.',
        '3 pending requests need urgent attention.'
    ]

    # Fetch data based on the current section to avoid unnecessary queries
    if current_section == 'users':
        users = User.query.all()
    elif current_section == 'requests':
        blood_requests = BloodRequest.query.all()
    elif current_section == 'drives':
        donation_drives = DonationDrive.query.order_by(DonationDrive.date.desc()).all()
    elif current_section == 'reports':
        pass
    elif current_section == 'add_user':
        pass

    total_users = User.query.count()

    return render_template(
        'admin.html',
        current_section=current_section,
        users=users,
        total_users=total_users,
        available_donors=available_donors,
        total_drives=total_drives,
        total_units_donated=total_units_donated,
        total_requests=total_requests,
        pending_requests=pending_requests,
        fulfilled_requests=fulfilled_requests,
        rejected_requests=rejected_requests,
        blood_group_distribution=blood_group_distribution,
        requests_by_group=requests_by_group,
        monthly_trends=monthly_trends,
        donor_availability_trend=donor_availability_trend,
        recent_blood_requests=recent_blood_requests,
        recent_drives=recent_drives,
        top_donors=top_donors,
        actionable_insights=actionable_insights,
        blood_requests=blood_requests,
        donation_drives=donation_drives,
        reports=reports
    )

@app.route('/coordinator', methods=['GET', 'POST'])
@login_required('coordinator')
def coordinator_dashboard():
    current_section = request.args.get('section', 'donors')
    donors = []
    donation_drives = []
    blood_requests = []
    quick_stats = {}


    if current_section == 'donors':
        # Filtering logic
        query = UserProfile.query.filter_by(is_available=True)
        search = request.args.get('search', '').strip()
        blood_group = request.args.get('blood_group', '').strip()
        branch = request.args.get('branch', '').strip()
        year = request.args.get('year', '').strip()

        if blood_group:
            query = query.filter_by(blood_group=blood_group)
        if branch:
            query = query.filter_by(branch=branch)
        if year:
            query = query.filter_by(year=int(year))
        if search:
            query = query.filter(
                (UserProfile.full_name.ilike(f"%{search}%")) |
                (UserProfile.roll_no.ilike(f"%{search}%"))
            )
        donors = query.all()
        # Quick stats for donors
        quick_stats['total_donors'] = UserProfile.query.filter_by(is_available=True).count()
        for bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
            quick_stats[f'{bg}_donors'] = UserProfile.query.filter_by(blood_group=bg, is_available=True).count()

    elif current_section == 'drives':
        from datetime import date
        today = date.today()
        # Only show non-cancelled drives by default
        donation_drives = DonationDrive.query.order_by(DonationDrive.date.desc()).all()
        # Quick stats for drives
        quick_stats['total_drives'] = DonationDrive.query.count()
        quick_stats['completed'] = DonationDrive.query.filter(DonationDrive.date < today, (DonationDrive.status == None) | (DonationDrive.status != 'cancelled')).count()
        quick_stats['upcoming'] = DonationDrive.query.filter(DonationDrive.date >= today, (DonationDrive.status == None) | (DonationDrive.status != 'cancelled')).count()
        quick_stats['cancelled'] = DonationDrive.query.filter_by(status='cancelled').count()

    elif current_section == 'add_drive':
        pass

    elif current_section == 'requests':
        blood_requests = BloodRequest.query.all()
        # Quick stats for blood requests
        quick_stats['total_requests'] = BloodRequest.query.count()
        quick_stats['fulfilled'] = BloodRequest.query.filter_by(status='fulfilled').count()
        quick_stats['pending'] = BloodRequest.query.filter_by(status='pending').count()
        quick_stats['cancelled'] = BloodRequest.query.filter_by(status='cancelled').count()
        # Add: status change form handling
        if request.method == 'POST' and 'request_id' in request.form and 'new_status' in request.form:
            req_id = int(request.form['request_id'])
            new_status = request.form['new_status']
            req_obj = BloodRequest.query.get(req_id)
            if req_obj and req_obj.status == 'pending' and new_status in ['fulfilled', 'cancelled']:
                req_obj.status = new_status
                db.session.commit()
                flash(f'Request status updated to {new_status}.', 'success')
            return redirect(url_for('coordinator_dashboard', section='requests'))

    return render_template(
        'coordinator.html',
        current_section=current_section,
        donors=donors,
        donation_drives=donation_drives,
        blood_requests=blood_requests,
        quick_stats=quick_stats
    )

@app.route('/complete-profile', methods=['GET', 'POST'])
@login_required()
def complete_profile():
    if request.method == 'POST':
        full_name = request.form['full_name']
        roll_no = request.form['roll_no']
        blood_group = request.form['blood_group']
        phone = request.form['phone']
        branch = request.form['branch']
        year = request.form['year']
        
        # Handle file uploads
        photo = request.files['photo']
        document = request.files['document']
        
        photo_path = None
        document_path = None
        
        if photo and allowed_file(photo.filename):
            filename = secure_filename(f"{session['user_id']}_photo.{photo.filename.rsplit('.', 1)[1].lower()}")
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
            photo_path = filename
        
        if document and allowed_file(document.filename):
            filename = secure_filename(f"{session['user_id']}_document.{document.filename.rsplit('.', 1)[1].lower()}")
            document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            document.save(document_path)
            document_path = filename
        
        if not phone.isdigit() or len(phone) != 10:
            flash('Phone number must be exactly 10 digits.', 'danger')
            return render_template('complete_profile.html')
        
        try:
            profile = UserProfile(
                user_id=session['user_id'],
                full_name=full_name,
                roll_no=roll_no,
                blood_group=blood_group,
                phone=phone,
                branch=branch,
                year=year,
                photo_path=photo_path,
                document_path=document_path
            )
            db.session.add(profile)
            db.session.commit()
            
            flash('Profile completed successfully!', 'success')
            return redirect(url_for('user_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error completing profile. Please try again.', 'danger')
    
    return render_template('complete_profile.html')

@app.route('/search-donors', methods=['GET', 'POST'])
def search_donors():
    if request.method == 'POST':
        blood_group = request.form['blood_group']
        branch = request.form.get('branch')
        year = request.form.get('year')
        
        query = UserProfile.query.filter_by(blood_group=blood_group, is_available=True)
        
        if branch:
            query = query.filter_by(branch=branch)
        if year:
            query = query.filter_by(year=year)
        
        donors = query.all()
        return render_template('search.html', donors=donors, search=True)
    
    return render_template('search.html', search=False)

@app.route('/request-blood', methods=['GET', 'POST'])
@login_required()
def request_blood():
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        blood_group = request.form['blood_group']
        units_required = request.form['units_required']
        hospital_name = request.form['hospital_name']
        urgency = request.form['urgency']
        contact_number = request.form['contact_number']
        try:
            blood_request = BloodRequest(
                requester_id=session['user_id'],
                patient_name=patient_name,
                blood_group=blood_group,
                units_required=units_required,
                hospital_name=hospital_name,
                urgency=urgency,
                contact_number=contact_number
            )
            db.session.add(blood_request)
            db.session.commit()
            flash('Blood request submitted successfully!', 'success')
            return redirect(url_for('user_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting request: {e}', 'danger')
    return render_template('request_blood.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        new_password = request.form['new_password']
        user = User.query.filter_by(username=username, email=email).first()
        if user and user.profile and user.profile.phone == phone:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid details. Please check your information.', 'danger')
    return render_template('forgot_password.html')

@app.route('/blood-donation-info')
def blood_donation_info():
    return render_template('blood_donation_info.html')

@app.route('/user/donation-drives')
@login_required()
def user_donation_drives():
    drives = DonationDrive.query.order_by(DonationDrive.date.desc()).all()
    return render_template('user_donation_drives.html', drives=drives)

@app.route('/user/donation-info')
@login_required()
def user_donation_info():
    user = User.query.get(session['user_id'])
    donations = DonationHistory.query.filter_by(user_id=user.id).order_by(DonationHistory.donation_date.desc()).all()
    total_donations = len(donations)
    total_amount = sum(d.amount_ml for d in donations)
    return render_template('user_donation_info.html', donations=donations, total_donations=total_donations, total_amount=total_amount)

@app.route('/user/report-donation', methods=['POST'])
@login_required()
def report_donation():
    from datetime import datetime
    user = User.query.get(session['user_id'])
    date_str = request.form['donation_date']
    amount_ml = int(request.form['amount_ml'])
    location = request.form.get('location')
    drive_id = request.form.get('drive_id')
    donation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    new_donation = DonationHistory(user_id=user.id, donation_date=donation_date, amount_ml=amount_ml, location=location, drive_id=drive_id or None)
    db.session.add(new_donation)
    user.profile.last_donation_date = donation_date
    db.session.commit()
    flash('Donation reported successfully!', 'success')
    return redirect(url_for('user_donation_info'))

# Admin routes
@app.route('/admin/users/<int:user_id>/edit-role', methods=['POST'])
@login_required('admin')
def edit_user_role(user_id):
    new_role = request.form['role']
    
    try:
        user = User.query.get(user_id)
        user.role = new_role
        db.session.commit()
        flash('User role updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating user role.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required('admin')
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-user', methods=['GET', 'POST'])
@login_required('admin')
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        try:
            new_user = User(username=username, email=email, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('New user added successfully!', 'success')
            return redirect(url_for('admin_dashboard', section='users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding user: {e}', 'danger')

    # For GET request, render the add user form within the admin layout
    # We will handle rendering this within admin.html based on a section parameter
    # This route will primarily be used for the POST submission.
    # The GET request will be handled by the admin_dashboard route with section='add_user'
    return redirect(url_for('admin_dashboard', section='add_user'))

@app.route('/coordinator/drives/add', methods=['GET', 'POST'])
@login_required('coordinator')
def add_donation_drive():
    if request.method == 'POST':
        name = request.form['name']
        date_str = request.form['date']
        location = request.form['location']
        description = request.form.get('description')
        from datetime import datetime
        try:
            drive_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            new_drive = DonationDrive(name=name, date=drive_date, location=location, description=description)
            db.session.add(new_drive)
            db.session.commit()
            flash('Donation drive added successfully!', 'success')
            return redirect(url_for('coordinator_dashboard', section='drives'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding donation drive: {e}', 'danger')
            return redirect(url_for('coordinator_dashboard', section='add_drive'))
    return redirect(url_for('coordinator_dashboard', section='add_drive'))

# Cancel drive route for coordinator
def cancel_drive(drive_id):
    from flask import redirect, url_for, flash
    drive = DonationDrive.query.get_or_404(drive_id)
    if drive.status == 'cancelled':
        flash('Drive already cancelled.', 'info')
    else:
        drive.status = 'cancelled'
        db.session.commit()
        flash('Donation drive cancelled.', 'success')
    return redirect(url_for('coordinator_dashboard', section='drives'))

app.add_url_rule(
    '/coordinator/drives/<int:drive_id>/cancel',
    view_func=login_required('coordinator')(cancel_drive),
    methods=['POST'],
    endpoint='cancel_drive'
)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)