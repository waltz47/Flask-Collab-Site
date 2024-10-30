from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from classes import *
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
import os

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
app.config['UPLOAD_DIR'] = 'static/uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///collab_db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

# Files for user and project data
USER_FILE = 'login.txt'
PROJECT_FILE = 'projects.txt'

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# Function to save user to the text file
def save_user(form):
    username = form['username']
    password = form['password']
    full_name = form['full name']
    user_location = form['location']

    with open(USER_FILE, 'a') as f:
        f.write(f"{username},{password},{full_name},{user_location}\n")

# Function to save a project to the text file
def save_project(p):
    with open(PROJECT_FILE, 'a') as f:
        f.write(str(p))

# Function to read all projects
def get_all_projects():
    projects = []
    try:
        with open(PROJECT_FILE, 'r') as f:
            for line in f:
                p = Project()
                p.read_from_string(line)
                if p.id:  # Ensure project has an ID
                    projects.append(p)
    except FileNotFoundError:
        pass
    return projects

def get_search_results(q):
    if len(q) == 0:
        return []
    projects = get_all_projects()
    matching = []
    for p in projects:
        if q in p.title.lower() or q in p.description.lower():
            matching.append(p.serialize())

    return matching


# Root route: homepage with two options
@app.route('/')
@app.route('/home')
def homepage():
    return render_template('homepage.html')

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
            # Here you might want to start a session for the user
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
        p = Project(title=title, description=description, owner=owner)
        if 'images' in request.files:
            for image in request.files.getlist('images'):
                if image and allowed_file(image.filename):  # Ensure you have an allowed_file function
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_DIR'], filename)
                    image.save(image_path)
                    p.add_image(filename)  # Or full path if needed
        else:
            print("No images attached")

        save_project(p)
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
    items_per_page = 10 if initial_load else 5  # Load more items initially
    all_projects = get_all_projects()
    
    # Sort projects by title or another attribute to ensure consistent ordering
    all_projects.sort(key=lambda x: x.title)
    
    # Calculate indices
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(all_projects))  # Prevent going beyond list bounds
    
    # Return empty list if start_idx is beyond available projects
    if start_idx >= len(all_projects):
        return jsonify([])
    print(f"loading more project: {start_idx}:{end_idx}")
    projects = all_projects[start_idx:end_idx]
    return jsonify([p.serialize() for p in projects])

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    results = get_search_results(query)
    # print(results)
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
