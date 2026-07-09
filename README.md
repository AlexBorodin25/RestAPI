# RestAPI
This is a RestAPI for tasks CRUD. 
It allows to GET, POST, PUT, and DELETE. 
To run the app, first generate your_secret_token with "python -c "import secrets; print(secrets.token_urlsafe(32))"
Then, run the app with "$env:API_TOKEN="your-secret-token" uvicorn main:app --host 127.0.0.1 --port 8000"
