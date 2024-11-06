from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from classes import *
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from flask_migrate import Migrate  # Ensure this is imported
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
app.config['UPLOAD_DIR'] = 'static/uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///collab_db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)  # Ensure this is initialized

with app.app_context():
    db.create_all()

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

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            print('Username already exists.', 'error')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        print('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            flash('Logged in successfully.', 'success')
            session['username'] = username
            return redirect(url_for('homepage'))
        else:
            flash('Login failed. Check your username and password.', 'error')
    return render_template('login.html')

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

        # Remove existing milestones
        project.milestones.clear()
        db.session.commit()
        # Add updated milestones
        milestones_descriptions = request.form.getlist('milestone_descriptions')
        milestones_deadlines = request.form.getlist('milestone_deadlines')
        for desc, dl in zip(milestones_descriptions, milestones_deadlines):
            if desc.strip():
                deadline = datetime.strptime(dl, '%Y-%m-%d') if dl else None
                milestone = Milestone(description=desc.strip(), deadline=deadline)
                project.milestones.append(milestone)

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

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    projects = Project.query.filter(
        (Project.title.ilike(f'%{query}%')) | 
        (Project.description.ilike(f'%{query}%'))
    ).all()
    return jsonify([p.serialize() for p in projects])

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
