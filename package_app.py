import zipfile
import os

def zip_directory(folder_path, zip_file):
    for root, dirs, files in os.walk(folder_path):
        # Skip __pycache__
        if '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.pyc'):
                continue
                
            file_path = os.path.join(root, file)
            # Archive name should be relative to the project root, e.g. python/session.py
            arcname = os.path.relpath(file_path, '.')
            print(f"Adding {arcname}")
            zip_file.write(file_path, arcname)

with zipfile.ZipFile('app_data.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zip_directory('python', zipf)
    zip_directory('pyscript_app', zipf)

print("Created app_data.zip")
