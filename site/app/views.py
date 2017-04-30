from flask import render_template
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