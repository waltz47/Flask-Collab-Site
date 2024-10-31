import random
from classes import *
from app import *
from classes import *

def generate_random_string(length=10):
    letters = 'abcdefghijklmnopqrstuvwxyz'
    return ''.join(random.choice(letters) for i in range(length))

def generate_random_project():
    title = generate_random_string(15)
    description = generate_random_string(50)
    owner = generate_random_string(10)
    category = random.choice(['hackathons', 'game jams', 'events'])
    deadline = datetime.utcnow() if random.choice([True, False]) else None
    return Project(title=title, description=description, owner=owner, category=category, deadline=deadline)

def generate_projects(n=10):
    projects = [generate_random_project() for _ in range(n)]
    return projects

if __name__ == "__main__":
    with app.app_context():
        projects = generate_projects(50)
        for proj in projects:
            db.session.add(proj)
        db.session.commit()
        print(f"Generated and added {len(projects)} projects to the database.")
