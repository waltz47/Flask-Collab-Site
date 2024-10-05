import json
class project:
    def __init__(self,title="unnamed project",description="No description",owner="none"):
        self.title = title
        self.description = description
        self.owner = owner
        self.project_images = [] #paths to all images attached to the project 
    
    def read_from_string(self, s):
        try:
            data = s.strip().split(',')
            self.title = data[0]
            self.description = data[1]
            self.owner = data[2]
            if len(data) > 3:
                self.project_images = data[3]
        except:
            print("Unable to read user from string:", s)
    
    def __str__(self):
        return f"{self.title}, {self.description}, {self.owner},{self.project_images}\n"

    def serialize(self):
        return {
            "title":self.title,
            "description":self.description,
            "owner":self.owner,
            "images":self.project_images
        }
    
    def add_image(self, image_path):
        # if image_path not in self.project_images:
            self.project_images = image_path
    
    def remove_image(self, image_path):
        # if image_path in self.project_images:
            self.project_images = None

    @classmethod
    def from_json(cls, json_str):
        # Class method to create a Project instance from a JSON string
        data = json.loads(json_str)
        project = cls(data.get('title', "unnamed project"), 
                      data.get('description', "No description"),
                      data.get('owner', "none"))
        project.project_images = data.get('images', [])
        return project