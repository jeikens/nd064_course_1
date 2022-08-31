from cgi import test
import sqlite3
import logging

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort
from os.path import exists
from os import access, W_OK
from sys import stderr, stdout

# configure logging
handlers = [
    logging.StreamHandler(stdout),
    logging.StreamHandler(stderr)
]
logging.basicConfig(format='[%(levelname)s:%(asctime)s:%(name)s] %(message)s', level=logging.DEBUG, handlers=handlers)

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    app.connection_counter += 1
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'afsMWYQJ6B77z7QDZULB'

# attach a counter variable to the flask app
app.connection_counter = 0

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
        logging.info(f'Article with ID {post_id} not found')
        return render_template('404.html'), 404
    else:
        logging.info(f'Article "{post[2]}" retrieved!')
        return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    logging.info(f'About Us page retrieved!')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()
            logging.info(f'Article "{title}" created')
            return redirect(url_for('index'))

    return render_template('create.html')

# Define healthcheck endpoint
@app.route('/healthz')
def healthcheck():
    # check if database file exists
    if not exists('database.db'):
        logging.error('database file is missing')
        return (jsonify({'result': 'ERROR - unhealty', 'message': 'database file missing'}), 500)
    # check if database is writable
    if not access('database.db', W_OK):
        logging.error('no write access to database file')
        return (jsonify({'result': 'ERROR - unhealty', 'message': 'database file not writable'}), 500)
    # try access to the db
    connection = get_db_connection()
    try:
        connection.execute('SELECT * FROM posts').fetchone()
    except sqlite3.sqlite3.OperationalError as e:
        logging.exception(e)
        return (jsonify({'result': 'ERROR - unhealty', 'message': 'database corrupt'}), 500)
    # Return JSON with http status 200
    return jsonify({'result': 'OK - healty'})

# Define metrics endpoint returning the number of posts and db connections
@app.route('/metrics')
def get_metrics():
    connection = get_db_connection()
    post_count = connection.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    return jsonify({
        'db_connection_count': app.connection_counter,
        'post_count' : post_count,
    })

def test_health():
    with app.test_client() as test_client:
        assert exists('database.db')
        resp = test_client.get('/healthz')
        assert resp.status_code == 200
        metric = resp.get_json()
        assert metric is not None
        assert metric['result'] == 'OK - healty'

def test_metrics():
    with app.test_client() as test_client:
        resp = test_client.get('/metrics')
        assert resp.status_code == 200
        metric = resp.get_json()
        assert metric is not None
        assert metric['post_count'] > 0
        db_connection_count = metric['db_connection_count']
        # query another time to see if the db counter increases
        resp = test_client.get('/metrics')
        assert resp.status_code == 200
        metric = resp.get_json()
        assert metric is not None
        assert metric['db_connection_count'] > db_connection_count

# start the application on port 3111
if __name__ == "__main__":
    app.run(host='0.0.0.0', port='3111')
