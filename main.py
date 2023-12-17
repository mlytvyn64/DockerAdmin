from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import docker

app = Flask(__name__)
app.secret_key = os.urandom(24)
docker_client = docker.from_env()

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)''')
conn.commit()
conn.close()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error_message = "Wrong login or password"
            return render_template('login.html', error=error_message)

    if not session.get('logged_in'):
        return render_template('login.html')

    return redirect(url_for('dashboard'))

@app.route('/test')
def dashboard():
    try:
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        containers_info = []

        if docker_client.ping():
            containers = docker_client.containers.list()
            for container in containers:
                container_info = {
                    'id': container.id,
                    'name': container.name,
                    'status': container.status
                }
                containers_info.append(container_info)
            return jsonify({'containers': containers_info})
        else:
            return jsonify({'error': 'No connection to Docker API'})

    except docker.errors.APIError as e:
        return jsonify({'error': f"Docker API error: {str(e)}"})



@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
