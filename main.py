from flask import Flask, make_response, render_template, request, redirect, url_for, session, jsonify
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

@app.route('/index', methods=['GET'])
def routeToDef():
    return redirect('/')

@app.route('/', methods=['GET'])
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
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
            return redirect(url_for('index'))
            

    if not session.get('logged_in'):
        return redirect(url_for('index'))

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    else:
        return render_template('dashboard.html')


@app.route("/getContainers", methods=['GET'])
def get_all_containers():
    try:
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        containers_info = []

        if docker_client.ping():
            containers = docker_client.containers.list(all=True)
            for container in containers:
                container_info = {
                    'id': container.id,
                    'name': container.name,
                    'status': container.status,
                    'port': list(container.ports.keys())[0] if container.ports else "none",
                }
                containers_info.append(container_info)
            response = make_response(jsonify({'containers': containers_info}))
        else:
            response = make_response(jsonify({'error': 'No connection to Docker API'}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Content-Type'] = 'json'
        return response

    except docker.errors.APIError as e:
        return jsonify({'error': f"Docker API error: {str(e)}"})

@app.route('/getLogs', methods=['GET'])
def get_logs():
    if not session.get('logged_in'):
            return redirect(url_for('login'))

    container_id = request.args.get('containerID')
    
    try:
        container = docker_client.containers.get(container_id)
        logs = container.logs().decode('utf-8')
        return jsonify({'logs': logs})
    except docker.errors.NotFound as e:
        return jsonify({'error': f"Container with ID {container_id} not found."})


@app.route('/logs.html')
def logs():
    if not session.get('logged_in'):
            return redirect(url_for('index'))
    else:
        containerID = request.args.get('containerID')
        return render_template('logs.html', containerID=containerID)

@app.route('/startStopContainer', methods=['GET'])
def start_stop_container():
    if not session.get('logged_in'):
            return redirect(url_for('login'))
    
    container_id = request.args.get('containerID')
    try:
        container = docker_client.containers.get(container_id)
        if container.status == 'running':
            container.stop()
            return jsonify({'success': 'Container stopped'})
        else:
            container.start()
            return jsonify({'success': 'Container started'})
    except docker.errors.NotFound as e:
        return jsonify({'error': f"Container with ID {container_id} not found."})
    
@app.route('/deleteContainer', methods=['DELETE'])
def delete_container():
    if not session.get('logged_in'):
            return redirect(url_for('login'))

    container_id = request.args.get('containerID')
    try:
        container = docker_client.containers.get(container_id)
        container.remove(force=True)
        return jsonify({'success': 'Container deleted successfully'})
    except docker.errors.NotFound as e:
        return jsonify({'error': f"Container with ID {container_id} not found."})
    except docker.errors.APIError as e:
        return jsonify({'error': f"Error deleting container: {str(e)}"})
    
@app.route('/startAllContainers', methods=['GET'])
def start_all_containers():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        stopped_containers = docker_client.containers.list(filters={'status': 'exited'})
        for container in stopped_containers:
            container.start()

        return jsonify({'success': 'All stopped containers started'})
    except docker.errors.APIError as e:
        return jsonify({'error': f"Error starting containers: {str(e)}"})



@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
