import random
import json
from classes import *

def generate_random_string(length=10):
    letters = 'abcdefghijklmnopqrstuvwxyz'
    return ''.join(random.choice(letters) for i in range(length))

def generate_random_project():
    title = generate_random_string(15)
    description = generate_random_string(50)
    owner = generate_random_string(10)
    return Project(title, description, owner)

def generate_projects(n=10):
    projects = [generate_random_project() for _ in range(n)]
    return projects

if __name__ == "__main__":
    projects = generate_projects(50)
    with open('projects.txt', 'a') as f:
        for proj in projects:
            f.write(str(proj))
            print(json.dumps(proj.serialize(), indent=4))
