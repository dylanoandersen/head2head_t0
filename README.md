#  Steps to setting up project

1. Clone the Repository:\
git clone <repository_url>\
cd <repository_name>

2. Set Up a Virtual Environment:\
python -m venv env\
source env/bin/activate  # On macOS/Linux\
env\Scripts\activate  # On Windows\

3. Install Dependencies:\
pip install -r requirements.txt

4. MySql:\
create a db in Workbench\
CREATE DATABASE h2h CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;\

Verify the Database is created\
SHOW DATABASES;\

Create user and password, replace the djangouser and securepassword123\
CREATE USER 'djangouser'@'%' IDENTIFIED BY 'securepassword123';\

Give yourself privileges\
GRANT ALL PRIVILEGES ON h2h.* TO 'djangouser'@'%';\
FLUSH PRIVILEGES;\

Configure settings.py\
DATABASES = {\
    'default': {\
        'ENGINE': 'django.db.backends.mysql',\
        'NAME': 'xxx',\              
        'USER': 'xxx',\    
        'PASSWORD': 'xxx',\ 
        'HOST': '127.0.0.1',\      
        'PORT': '3306',\              
    }\
}\

Set Up the Database:\

python manage.py makemigrations\
python manage.py migrate\
daphne -b 0.0.0.0 -p 8000 head2head.asgi:application\

This loads all data from dbb.json into the tables. Please check tables in Workbench to make sure.\
python manage.py loaddata dbb.json

5. Create a Superuser:\
python manage.py createsuperuser

6. Run the Development Server:\
daphne -b 0.0.0.0 -p 8000 head2head.asgi:application

7. Ask Chat with errors, usually works