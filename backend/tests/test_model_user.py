import sys
import os
import pathlib

# Change to backend directory
backend_dir = str(pathlib.Path(__file__).parent.parent.absolute())
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from app.models.user import User

u = User(name="Test User")
# Test if it's a property or method
print(type(User.full_name))
try:
    print(u.full_name)
except Exception as e:
    print(f"Error accessing as property: {e}")
