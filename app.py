from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'mpms_secure_key_2026' # Required for flashing messages

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Here you would typically connect to your MySQL database to verify credentials
        # For demonstration, we will just print them to the console
        print(f"Login Attempt - User: {username}, Role: {role}")
        
        # Simulated successful login
        if username and password:
            return f"Welcome {username}! Logged in successfully as {role}."
            
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)