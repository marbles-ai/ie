from flask import Flask, send_file, render_template, jsonify
import os
import logging
#import watchtower
# import marbles, marbles.ie, marbles.ie.core, marbles.ie.utils, marbles.ie.ccg, marbles.log
from marbles.ie.core.constants import *
from marbles.ie import grpc

app = Flask(__name__)

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
def main():
    return render_template('index.html',
                           title='Home')


@app.route('/demo')
def demo():
    return render_template('demo.html',
                           title='Demo')


@app.route('/getData', methods=['GET'])
def stuff():
    i = getGlobalCount()
    return jsonify(article="Article: " + str(i), content="Content: " + str(i))


@app.route('/getBackground', methods=['GET'])
def background():
    background_name = generate_background()
    return jsonify(background=background_name)

@app.route('/infox', methods=['GET'])
def infox():

    stub, _ = grpc.get_infox_client_transport('infox')
    gtext = grpc.GText()
    gtext.text = 'The boy wants to believe the girl'
    gtext.options = CO_VERIFY_SIGNATURES | CO_NO_VERBNET | CO_NO_WIKI_SEARCH
    gsentence = stub.parse(gtext)

    return jsonify(infox=gsentence)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False, port=80)
