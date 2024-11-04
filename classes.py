import json
import hashlib
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

project_users = db.Table('project_users',
    db.Column('project_id', db.String(64), db.ForeignKey('projects.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    owner = db.Column(db.String(80), nullable=False)
    project_images = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    users = db.relationship('User', secondary=project_users, lazy='subquery',
                            backref=db.backref('projects', lazy=True))

    def __init__(self, title="unnamed project", description="No description", owner="none", project_images="", category=None, deadline=None):
        unique_string = f"{title}{owner}{description}"
        self.id = hashlib.sha256(unique_string.encode()).hexdigest()  # Consistent unique id
        self.title = title
        self.description = description
        self.owner = owner
        self.project_images = project_images
        self.category = category
        self.deadline = deadline

    def read_from_string(self, s):
        try:
            data = s.strip().split(',')
            if len(data) < 4:
                print(f"Incomplete project data: {s}")
                return
            self.id = data[0]
            self.title = data[1]
            self.description = data[2]
            self.owner = data[3]
            self.project_images = data[4] if (len(data) > 4) else ""
        except Exception as e:
            print(f"Unable to read project from string: {s}, Error: {e}")

    def __str__(self):
        return f"{self.id},{self.title},{self.description},{self.owner},{self.project_images}\n"

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "owner": self.owner,
            "images": self.project_images,
            "date_created": self.date_created.isoformat() if self.date_created else None,
            "category": self.category,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "users": [user.username for user in self.users]
        }

    def add_image(self, image_path):
        if self.project_images:
            self.project_images += f",{image_path}"
        else:
            self.project_images = image_path

    def remove_image(self, image_path):
        images = self.project_images.split(',') if self.project_images else []
        if image_path in images:
            images.remove(image_path)
            self.project_images = ','.join(images) if images else ""

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        project = cls(
            data.get('title', "unnamed project"), 
            data.get('description', "No description"),
            data.get('owner', "none"),
            data.get('images', ""),
            data.get('category', None),
            data.get('deadline', None)
        )
        return project

