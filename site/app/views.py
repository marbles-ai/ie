from flask import render_template
from flask import jsonify
from app import app
import logging
#import wordcloud

i = 0

# For now, let's use this for examples
def getGlobalCount():
    global i
    i = i + 1
    return i - 1

# Generates a wordcloud background
def generate_background():
    print "Generating a new background"
#    wordcloud.generate_wordcloud()

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',
                           title='Home')

@app.route('/getData', methods= ['GET'])
def stuff():
    i = getGlobalCount()
    return jsonify(article="Article: "+ str(i), content="Content: " + str(i))

@app.route('/getBackground', methods= ['GET'])
def background():
    background_name = generate_background()
    return jsonify(background=background_name)