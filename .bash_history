unzip deploy.zip
mkvirtualenv --python=/usr/bin/python3.10 myenv
pip install -r requirements.txt
python manage.py collectstatic --noinput
rmvirtualenv myenv
exit
