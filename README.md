## Steps to run:
	1. Run `pip3 install -r requirements.txt`
	2. Run `python3 -m textblob.download_corpora`
	3. Migrate the database using `python3 manage.py migrate` inside the oauthProject directory.
	4. Inside the oauthProject directory, run `python3 manage.py runserver` to run the application.
	5. Go to localhost:8000 on your browser.

