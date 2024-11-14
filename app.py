import argparse  # Add this import
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from classes import db, User, Project, Milestone  # Ensure these imports are present
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from flask_migrate import Migrate  # Ensure this is imported
import os
from datetime import datetime, timedelta
from flask_mail import Mail, Message  # Ensure Flask-Mail is installed
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth  # Update this import
from urllib.parse import quote as url_quote  # Update this import

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
app.config['UPLOAD_DIR'] = 'static/uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///collab_db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Secure session cookies
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_DURATION=timedelta(days=14)
)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize the database
db.init_app(app)

with app.app_context():
    db.create_all()

migrate = Migrate(app, db)  # Ensure this is initialized

# Initialize Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.example.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 587  # Update if different
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@example.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your_email_password'  # Replace with your email password
mail = Mail(app)

# Initialize Flask-Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='DD',
    client_secret='DD',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri='http://localhost:5000/login/authorized',  # Ensure this matches the registered URI
    client_kwargs={'scope': 'email'},
)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.route('/')
@app.route('/home')
def homepage():
    # Read 'about.txt' content
    with open(os.path.join('static', 'about.txt'), 'r',encoding='utf-8') as f:
        about_text = f.read()
    # Pass 'about_text' to the template
    return render_template('homepage.html', about_text=about_text)

@app.route('/about')
def about():
    # Read 'about.txt' content
    with open(os.path.join('static', 'about.txt'), 'r') as f:
        about_text = f.read()
    # Pass 'about_text' to the template
    return render_template('about.html', about_text=about_text)

# Remove the existing registration route
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     # ...existing code...

@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    session.pop('google_token', None)
    session.pop('username', None)
    session.pop('email', None)
    return redirect(url_for('homepage'))

@app.route('/login/authorized')
def authorized():
    token = google.authorize_access_token()
    if token is None:
        flash('Access denied: reason={} error={}'.format(
            request.args['error_reason'],
            request.args['error_description']
        ), 'error')
        return redirect(url_for('homepage'))

    session['google_token'] = token
    user_info = google.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
    session['email'] = user_info['email']

    user = User.query.filter_by(email=session['email']).first()
    if user:
        session['username'] = user.username
        return redirect(url_for('homepage'))
    else:
        return redirect(url_for('ask_username'))

@app.route('/ask-username', methods=['GET', 'POST'])
@csrf.exempt  # Add CSRF protection
def ask_username():
    if request.method == 'POST':
        username = request.form['username']
        print(f"Received username: {username}")  # Debugging statement
        if User.query.filter_by(username=username).first():
            flash('Username already taken, please choose another one.', 'error')
        else:
            try:
                user = User(username=username, email=session['email'])
                db.session.add(user)
                db.session.commit()
                session['username'] = username
                print(f"User {username} added to the database")  # Debugging statement
                return redirect(url_for('homepage'))
            except Exception as e:
                print(f"Error adding user: {e}")  # Debugging statement
                flash('An error occurred while creating your account. Please try again.', 'error')
    return render_template('ask_username.html')

# Post a project route
@app.route('/post-project', methods=['GET', 'POST'])
def post_project():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        owner = session['username']
        category = request.form.get('category')
        deadline = request.form.get('deadline')
        deadline = datetime.strptime(deadline, '%Y-%m-%d') if deadline else None
        other_users = request.form.get('users', '').split(',')
        invalid_usernames = []
        valid_users = []

        # Validate all usernames
        for username in other_users:
            username = username.strip()

            if username == owner:
                continue

            if username:
                user = User.query.filter_by(username=username).first()
                if user:
                    valid_users.append(user)
                else:
                    invalid_usernames.append(username)

        if invalid_usernames:
            flash(f"Invalid usernames: {', '.join(invalid_usernames)}", 'error')
            return render_template('post_project.html', title=title, description=description, category=category, deadline=deadline, users=request.form['users'])

        # Create and add the project to the session
        p = Project(title=title, description=description, owner=owner, category=category, deadline=deadline)
        db.session.add(p)
        user = User.query.filter_by(username=owner).first()
        if user:
            p.users.append(user)
        for user in valid_users:
            if user not in p.users:
                p.users.append(user)

        if 'images' in request.files:
            for image in request.files.getlist('images'):
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_DIR'], filename)
                    image.save(image_path)
                    p.add_image(filename)

        # Handle milestones
        milestones_descriptions = request.form.getlist('milestone_descriptions')
        milestones_deadlines = request.form.getlist('milestone_deadlines')
        for desc, dl in zip(milestones_descriptions, milestones_deadlines):
            if desc.strip():
                deadline = datetime.strptime(dl, '%Y-%m-%d') if dl else None
                milestone = Milestone(description=desc.strip(), deadline=deadline)
                milestone.completed = request.form.get('milestone_completed_new') == 'on'
                p.milestones.append(milestone)

        db.session.commit()  # Commit the session after all modifications
        return redirect(url_for('browse_projects'))

    return render_template('post_project.html')

# Browse projects route
@app.route('/browse-projects')
def browse_projects():
    return render_template('browse_projects.html')

@app.route('/load-more-projects')
def load_more_projects():
    page = request.args.get('page', 1, type=int)
    initial_load = request.args.get('initialLoad', 'false').lower() == 'true'
    items_per_page = 10 if initial_load else 5
    projects = Project.query.order_by(Project.title).paginate(page=page, per_page=items_per_page, error_out=False).items
    return jsonify([p.serialize() for p in projects])

@app.route('/view-project/<project_id>')
def view_project(project_id):
    project = Project.query.get(project_id)
    if project:
        # Determine milestone statuses
        for milestone in project.milestones:
            if milestone.completed:
                milestone.status = 'completed'
            elif milestone.deadline and milestone.deadline < datetime.utcnow():
                milestone.status = 'overdue'
            else:
                milestone.status = 'upcoming'
        return render_template('view_project.html', project=project)
    else:
        return "Project not found", 404

@app.route('/edit-project/<project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return "Project not found", 404

    if 'username' not in session or (session['username'] != project.owner and session['username'] not in [user.username for user in project.users]):
        return "You do not have permission to edit this project", 403

    if request.method == 'POST':
        project.title = request.form['title']
        project.description = request.form['description']
        project.category = request.form.get('category')
        deadline = request.form.get('deadline')
        project.deadline = datetime.strptime(deadline, '%Y-%m-%d') if deadline else None
        other_users = request.form.get('users', '').split(',')
        invalid_usernames = []
        valid_users = []

        # Validate all usernames
        for username in other_users:
            username = username.strip()

            if username == project.owner:
                continue

            if username:
                user = User.query.filter_by(username=username).first()
                if user:
                    valid_users.append(user)
                else:
                    invalid_usernames.append(username)

        if invalid_usernames:
            flash(f"Invalid usernames: {', '.join(invalid_usernames)}", 'error')
            return render_template('edit_project.html', project=project)

        # Ensure the owner is always included
        project.users = [User.query.filter_by(username=project.owner).first()]
        for user in valid_users:
            if user not in project.users:
                project.users.append(user)

        if 'images' in request.files:
            for image in request.files.getlist('images'):
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_DIR'], filename)
                    image.save(image_path)
                    project.add_image(filename)

        # Get milestone data from form
        milestone_ids = request.form.getlist('milestone_ids')
        milestones_descriptions = request.form.getlist('milestone_descriptions')
        milestones_deadlines = request.form.getlist('milestone_deadlines')

        # Ensure all lists are of the same length
        if not (len(milestone_ids) == len(milestones_descriptions) == len(milestones_deadlines)):
            flash("Mismatch in milestone data.", 'error')
            return render_template('edit_project.html', project=project)

        # Update existing milestones
        for m_id, desc, dl in zip(milestone_ids, milestones_descriptions, milestones_deadlines):
            deadline = datetime.strptime(dl, '%Y-%m-%d') if dl else None
            if m_id:
                # Update existing milestone
                milestone = Milestone.query.get(int(m_id))
                if milestone and milestone in project.milestones:
                    milestone.description = desc.strip()
                    milestone.deadline = deadline
                    milestone.completed = request.form.get(f'milestone_completed_{m_id}') == 'on'
            else:
                # Add new milestone
                if desc.strip():
                    new_milestone = Milestone(description=desc.strip(), deadline=deadline)
                    new_milestone.completed = request.form.get('milestone_completed_new') == 'on'
                    project.milestones.append(new_milestone)
                    db.session.add(new_milestone)  # Ensure new milestone is added to the session

        # Remove milestones that were deleted in the form
        form_milestone_ids = [int(mid) for mid in milestone_ids if mid]
        for milestone in project.milestones[:]:
            if milestone.id not in form_milestone_ids and str(milestone.id) not in milestone_ids:
                project.milestones.remove(milestone)
                db.session.delete(milestone)

        db.session.commit()
        return redirect(url_for('view_project', project_id=project.id))

    return render_template('edit_project.html', project=project)

@app.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first()
    if user:
        return render_template('user_profile.html', user=user)
    else:
        return "User not found", 404

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    projects = Project.query.filter(
        (Project.title.ilike(f'%{query}%')) | 
        (Project.description.ilike(f'%{query}%'))
    ).all()
    return jsonify([p.serialize() for p in projects])

@app.route('/complete-milestone/<int:milestone_id>', methods=['POST'])
def complete_milestone(milestone_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    milestone = Milestone.query.get(milestone_id)
    if not milestone:
        return "Milestone not found", 404
    project = Project.query.get(milestone.project_id)
    if session['username'] != project.owner:
        return "You do not have permission to complete this milestone", 403
    milestone.completed = True
    milestone.completed_date = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('view_project', project_id=project.id))

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/contact-us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        # Gather form data
        name = request.form['name']
        email = request.form['email']
        message_content = request.form['message']

        # Send email (configure mail settings properly)
        msg = Message(subject=f"Contact Us Message from {name}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['support@example.com'])  # Replace with your support email
        msg.body = f"From: {name} <{email}>\n\n{message_content}"
        mail.send(msg)
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact_us'))
    return render_template('contact_us.html')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Flask application.')
    parser.add_argument('--debug', action='store_true', help='Run the application in debug mode')
    args = parser.parse_args()

    app.run(debug=args.debug)
