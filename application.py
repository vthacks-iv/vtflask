import flask
import json
import boto.sts
import os
import string
import random

from flask import jsonify, Response
from flask import send_file

application = flask.Flask(__name__)
application.debug=True

# connect using the IAM user credentials (required)
_sts = boto.sts.connect_to_region('us-east-1', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'))

# temporary security credentials will lasts for 36 hours (3 days)
TOKEN_SESSION_DURATION = 129600
MAP_IMAGE_FILE = 'vthacks_map.png'

# current sns policy that allows all sns actions (testing purposes right now)
VT_SNS_POLICY = json.dumps(
{
  "Statement": [
      {
            "Sid": "AllAccess",
            "Action": "*",
            "Effect": "Allow",
            "Resource":"*"
      }
    ]
})



@application.route('/')
def hello_world():
    return "Hello! This is the VTHacks server."

'''
Returns temporary security credentials as defined in VT_SNS_POLICY lasting for
TOKEN_SESSION_DURATION. Token session identified with provided <name> argument.
'''
@application.route('/get_credentials')
def get_credentials():
    name = produce_random_str()
    response = _sts.get_federation_token(name, duration=TOKEN_SESSION_DURATION, policy=VT_SNS_POLICY)
    dict_response = {
      'accessKeyID': response.credentials.access_key,
      'secretAccessKey': response.credentials.secret_key,
      'securityToken': response.credentials.session_token,
      'expiration': response.credentials.expiration
    }
    return jsonify(**dict_response)

@application.route('/get_map')
def get_map():
    return send_file(MAP_IMAGE_FILE, mimetype='image/png')

@application.route('/get_welcome')
def get_welcome():
  with open('welcome.json') as json_file:
    json_data = json.load(json_file)
    return jsonify(**json_data)

@application.route('/get_schedule')
def get_schedule():
  with open('schedule.json') as json_file:
    json_data = json.load(json_file)
    return jsonify(**json_data)

@application.route('/get_awards')
def get_awards():
  with open('awards.json') as json_file:
    json_data = json.load(json_file)
    return jsonify(**json_data)

@application.route('/get_contacts')
def get_contacts():
  with open('contacts.json') as json_file:
    json_data = json.load(json_file)
    return jsonify(**json_data)

# used to produce random name identifier needed in token request
def produce_random_str():
  return ''.join(random.choice(string.ascii_uppercase) for i in range(12))

if __name__ == '__main__':
    application.run(host='0.0.0.0', debug=True)

