from flask import render_template
from flask import request
from app import app

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',
                           title='Home')

@app.route('/examples')
def examples():
    return render_template('examples.html',
                           title='Examples')

@app.route('/examples', methods=['POST'])
def submit_post():
    text = request.form['textarea']
    return "Apple"
