import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'dev-secret-key-123'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'complaints.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False