from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Complaint
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_tables():
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin_user = User(
                student_id='admin001',
                name='Administrator',
                email='admin@college.edu',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit() 
        print("Database tables created successfully!")

@app.route('/') # Home Route / Main Page
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        user = User.query.filter_by(student_id=student_id).first()
        if user:
            flash('Student ID already exists!', 'danger')
            return redirect(url_for('register'))
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            student_id=student_id,
            name=name,
            email=email,
            password=hashed_password
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(student_id=student_id).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=remember)
        
        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    complaints = Complaint.query.filter_by(user_id=current_user.id)\
        .order_by(Complaint.created_at.desc()).all()
    return render_template('student_dashboard.html', complaints=complaints)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('student_dashboard'))
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')
    search_query = request.args.get('search', '')
    
    # Build query
    query = Complaint.query
    
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    if category_filter:
        query = query.filter(Complaint.category == category_filter)
    if search_query:
        query = query.filter(Complaint.title.ilike(f'%{search_query}%'))
    
    complaints = query.order_by(Complaint.created_at.desc()).all()
    
    # Get unique categories for filter dropdown
    categories = db.session.query(Complaint.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('admin_dashboard.html', 
                         complaints=complaints,
                         categories=categories,
                         status_filter=status_filter,
                         category_filter=category_filter,
                         search_query=search_query)

@app.route('/complaint/submit', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        
        new_complaint = Complaint(
            title=title,
            description=description,
            category=category,
            user_id=current_user.id
        )
        
        db.session.add(new_complaint)
        db.session.commit()
        
        flash('Complaint submitted successfully!', 'success')
        return redirect(url_for('student_dashboard'))
    
    return render_template('submit_complaint.html')

@app.route('/complaint/<int:complaint_id>')
@login_required
def view_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check if user has permission to view this complaint
    if not current_user.is_admin and complaint.user_id != current_user.id:
        flash('You do not have permission to view this complaint.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    return render_template('view_complaint.html', complaint=complaint)

@app.route('/admin/update_status/<int:complaint_id>', methods=['POST'])
@login_required
def update_complaint_status(complaint_id):
    if not current_user.is_admin:
        return redirect(url_for('student_dashboard'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    new_status = request.form.get('status')
    remarks = request.form.get('remarks', '')
    
    complaint.status = new_status
    complaint.admin_remarks = remarks
    complaint.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Complaint status updated successfully!', 'success')
    return redirect(url_for('view_complaint', complaint_id=complaint_id))

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)