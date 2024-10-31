import random
import os
from classes import *
from app import *
from classes import *
import json

data = []

def read():
    with open('instance/examples.json','r') as f:
        global data
        data = json.load(f)['projects']

def generate_random_string(length=10):
    letters = 'abcdefghijklmnopqrstuvwxyz'
    return ''.join(random.choice(letters) for i in range(length))

def get_random_images(num_images=1):
    images_path = 'static/uploads'
    images = [img for img in os.listdir(images_path) if os.path.isfile(os.path.join(images_path, img))]
    return random.sample(images, min(num_images, len(images))) if images else []

def generate_random_project():
    rproj = random.choice(data)
    title = rproj['title']
    description = rproj['description']
    owner = generate_random_string(10)
    category = random.choice(['hackathons', 'game jams', 'events'])
    deadline = datetime.utcnow() if random.choice([True, False]) else None
    num_images = random.randint(1, 5)  # Randomly decide the number of images (1 to 5)
    images = get_random_images(num_images)
    return Project(title=title, description=description, owner=owner, category=category, deadline=deadline, project_images=','.join(images))

def generate_projects(n=10):
    projects = [generate_random_project() for _ in range(n)]
    return projects

if __name__ == "__main__":
    read()
    with app.app_context():
        projects = generate_projects(50)
        for proj in projects:
            db.session.add(proj)
        db.session.commit()
        print(f"Generated and added {len(projects)} projects to the database.")
