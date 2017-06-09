from flask import Flask
import watchtower, logging

app = Flask(__name__)
from app import views
