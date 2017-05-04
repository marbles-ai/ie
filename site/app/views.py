from flask import render_template
from flask import request
from app import app

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',
                           title='Home')

@app.route('/examples', methods=['GET', 'POST'])
def examples():
    return render_template('examples.html',
                           title='Examples')

@app.route('/submit', methods=['GET', 'OPTIONS'])
def submit():
    sent = request.args.get('textarea')
    print "Got: ", sent
    return sent + " returned!!"