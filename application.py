import flask
import json
import boto.sts
import os
from flask import Response

application = flask.Flask(__name__)
application.debug=True

# connect using the IAM user credentials (required)
_sts = boto.sts.connect_to_region('us-east-1', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'))

# temporary security credentials will lasts for 36 hours (3 days)
TOKEN_SESSION_DURATION = 129600

# current sns policy that allows all sns actions (testing purposes right now)
VT_SNS_POLICY = json.dumps(
{
  "Statement": [
      {
            "Sid": "Stmt1396058572300",
            "Action": "sns:*",
            "Effect": "Allow",
            "Resource": "arn:aws:sns:us-east-1:860000342007:VTHacksTopic"
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
@application.route('/get_credentials/<name>')
def get_credentials(name):
    response = _sts.get_federation_token(name, duration=TOKEN_SESSION_DURATION, policy=VT_SNS_POLICY)
    dict_response = {
      'accessKeyID': response.credentials.access_key,
      'secretAccessKey': response.credentials.secret_key,
      'securityToken': response.credentials.session_token,
      'expiration': response.credentials.expiration
    }
    return Response(json.dumps(dict_response), status=201, mimetype='application/json')

if __name__ == '__main__':
    application.run(host='0.0.0.0', debug=True)

