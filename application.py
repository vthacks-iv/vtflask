import flask
import json
import boto.sts
import boto.sns
import os
import string
import random
from datetime import datetime
from functools import wraps

from flask import jsonify, Response, request, render_template
from flask.ext.pymongo import PyMongo
from bson import json_util
from bson.objectid import ObjectId
from flask.ext.bcrypt import Bcrypt
from flask import send_file

application = flask.Flask(__name__)
application.debug=True



IOS_PLATFORM_ARN = "arn:aws:sns:us-east-1:860000342007:app/APNS_SANDBOX/VTHacks"

# connect using the IAM user credentials (required)
_sts = boto.sts.connect_to_region('us-east-1', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'))
_sns = boto.sns.connect_to_region('us-east-1', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'))

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

# Get MongoDB client
mongo = PyMongo(application)
# Get Bcrypt client
bcrypt = Bcrypt(application)

def check_auth(username, password):
  return username == 'admin' and password == ''

def authenticate():
  return Response('Could not verify your access level for that URL.\n'
  'You have to login with proper credentials', 401,
  {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
      return authenticate()
    return f(*args, **kwargs)
  return decorated

@application.route('/')
@requires_auth
def hello_world():
    return "Hello! This is the VTHacks server."

@application.route('/hi')
@requires_auth
def hi_world():
    return "Hi! This is the VTHacks server."

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
      'expiration': response.credentials.expiration,
      'iosPlatformARN': IOS_PLATFORM_ARN
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

@application.route('/get_map_markers')
def get_map_markers():
  with open('map_markers.json') as json_file:
    json_data = json.load(json_file)
    return jsonify(**json_data)

@application.route("/submit_push", methods=['POST'])
@requires_auth
def submit_push():
  return 'post worked hello', 200

@application.route("/push_form", methods=['GET'])
@requires_auth
def push_form():
  render_template('index.html')

@application.route('/announcements', methods=['GET'])
def get_announcements():
  result = mongo.db.announcements.find()
  return str(json.dumps({'announcements':list(result)}, default=json_util.default)), 200

@application.route('/announcements', methods=['POST'])
def post_announcement():
  title = request.form.get('title')
  message = request.form.get('message')
  if not title or not message:
    return 'required elements not present', 400

  delta = datetime.now() - datetime.utcfromtimestamp(0)
  timestamp = int(delta.total_seconds() * 1000)

  announcement = {'Subject': title, 'Message': message, 'Timestamp': timestamp}
  mongo.db.announcements.insert(announcement)

  json_string = json.dumps({'GCM': json.dumps({'data': {'title': title, 'message': message, 'timestamp': timestamp}}, ensure_ascii=False), 'APNS': json.dumps({'aps': {'alert': title + '|' + message}}, ensure_ascii=False), 'sqs': title + '|' + message, 'default': title + '|' + message}, ensure_ascii=False)

  _sns.publish(target_arn='arn:aws:sns:us-east-1:860000342007:VTHacksTopic',
      message=json_string,
      subject=title,
      message_structure='json')

  return 'success', 200

@application.route('/groups', methods=['GET'])
def get_groups():
  # return all groups with no password field
  result = mongo.db.groups.find({}, {'password': False})
  return str(json.dumps({'groups':list(result)}, default=json_util.default)), 200

@application.route('/groups', methods=['POST'])
def post_group():
  # password, members, email, twitter, phone, ideas
  password = request.form.get('password')
  members = request.form.get('members')
  email = request.form.get('email')
  twitter = request.form.get('twitter')
  phone = request.form.get('phone')
  ideas = request.form.get('ideas')

  # make sure at least one contact method exists
  if (not password
      or not members
      or (not email and not twitter and not phone)
      or not ideas):
        return 'required elements not present', 400

  group = {'password': bcrypt.generate_password_hash(password),
           'members': members,
           'ideas': ideas}
  if email:
    group.update({'email': email})
  if twitter:
    group.update({'twitter': twitter})
  if phone:
    group.update({'phone': phone})

  mongo.db.groups.insert(group)

  return 'success', 200

@application.route('/groups', methods=['DELETE'])
def delete_group():
  # need groupID and matching password
  request_password = request.form.get('password')
  groupID = request.form.get('groupID')

  if not request_password or not groupID:
    return 'required elements not present', 400

  group = mongo.db.groups.find_one({'_id': ObjectId(groupID)})
  if not group:
    return 'group not found', 404

  db_password = group.get('password')
  if not db_password:
    return 'password not in db', 500

  if not bcrypt.check_password_hash(db_password, request_password):
    return 'invalid password', 401

  mongo.db.groups.remove({'_id': ObjectId(groupID)})

  return 'success', 200

# used to produce random name identifier needed in token request
def produce_random_str():
  return ''.join(random.choice(string.ascii_uppercase) for i in range(12))

if __name__ == '__main__':
    application.run(host='0.0.0.0', debug=True)

