from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from classes import *
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'
app.config['UPLOAD_DIR'] = 'static/uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///collab_db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# Root route: homepage with two options
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
        p = Project(title=title, description=description, owner=owner, category=category, deadline=deadline)
        if 'images' in request.files:
            for image in request.files.getlist('images'):
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_DIR'], filename)
                    image.save(image_path)
                    p.add_image(filename)
        db.session.add(p)
        db.session.commit()
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
        return render_template('view_project.html', project=project)
    else:
        return "Project not found", 404

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
