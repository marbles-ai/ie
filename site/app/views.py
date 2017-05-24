from flask import render_template
from app import app

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',
                           title='Home')

@app.route('/demo')
def demo():
    return render_template('demo.html',
                           title='Demo')

@app.route('/fakenews')
def fakenews():
    return render_template('fakenews.html',
                           title='Fake News')

@app.route('/contact')
def contact():
    return render_template('contact.html',
                           title='Contact')

# @app.route('/submit', methods=['GET', 'OPTIONS'])
# def submit():
#     sent = request.args.get('textarea')
#     print "Got: ", sent
#     return sent + " returned!!"


# @app.route('/signin')
# def signin():
#     return render_template('signin.html',
#                            title='Sign In')
