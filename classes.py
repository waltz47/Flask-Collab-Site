import json
import hashlib
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

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


class Project:
    def __init__(self, title="unnamed project", description="No description", owner="none", project_images=""):
        unique_string = f"{title}{owner}{description}"
        self.id = hashlib.sha256(unique_string.encode()).hexdigest()  # Consistent unique id
        self.title = title
        self.description = description
        self.owner = owner
        self.project_images = project_images  # paths to all images attached to the project 
    
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
        # Include id in storage
        return f"{self.id},{self.title},{self.description},{self.owner},{self.project_images}\n"

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "owner": self.owner,
            "images": self.project_images
        }
    
    def add_image(self, image_path):
        if self.project_images:
            self.project_images += f",{image_path}"
        else:
            self.project_images = image_path
    
    def remove_image(self, image_path):
        # Implement proper image removal if needed
        images = self.project_images.split(',') if self.project_images else []
        if image_path in images:
            images.remove(image_path)
            self.project_images = ','.join(images) if images else ""
    
    @classmethod
    def from_json(cls, json_str):
        # Class method to create a Project instance from a JSON string
        data = json.loads(json_str)
        project = cls(
            data.get('title', "unnamed project"), 
            data.get('description', "No description"),
            data.get('owner', "none"),
            data.get('images', "")
        )
        return project

