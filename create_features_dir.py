import os

# Create the features directory
features_dir = r'c:\PROJECTS\eden-framework\eden\features'
os.makedirs(features_dir, exist_ok=True)

# Create the __init__.py file
init_file = os.path.join(features_dir, '__init__.py')
open(init_file, 'w').close()

print(f"Directory created: {features_dir}")
print(f"File created: {init_file}")
