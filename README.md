Steps to setting up project

# This is to create a virutal environment if on macOS/Linux
python3 -m venv venv
source venv/bin/activate

# This is to create a virutal environment if on Windows
python -m venv venv
venv\Scripts\activate

# This install all dependencies
pip install -r requirements.txt

# Migrates all models 
python manage.py migrate

# run server to check if working
python manage.py runserver
