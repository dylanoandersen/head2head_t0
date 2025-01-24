#  Steps to setting up project

1. Clone the Repository:\
git clone <repository_url>\
cd <repository_name>

2. Set Up a Virtual Environment:\
python -m venv env\
source env/bin/activate  # On macOS/Linux\
env\Scripts\activate  # On Windows

3. Install Dependencies:\
pip install -r requirements.txt

4. Configure settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'h2h',               
        'USER': 'dandersen',    
        'PASSWORD': 'xxx', 
        'HOST': 'xxx',      
        'PORT': '3306',              
    }
}\
contact me for the HOST and PASSWORD

5. Set Up the Database:\
python manage.py makemigrations\
python manage.py migrate

6. Create a Superuser:\
python manage.py createsuperuser

7. Run the Development Server:\
python manage.py runserver
