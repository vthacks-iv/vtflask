import flask
import json
import boto.sts


application = flask.Flask(__name__)
_sts = boto.sts.connect_to_region('us-east-1')

# Current sns policy that allows a lot of actions (testing purposes right now)
sns_policy = json.dumps(
{
  "Id": "Policy1396058584833",
  "Statement": [
      {
            "Sid": "Stmt1396058572300",
            "Action": "sns:*",
            "Effect": "Allow",
            "Resource": "arn:aws:sns:us-east-1:860000342007:VTHacksTopic",
            "Principal": {
                    "AWS": "*"
                  }
          }
    ]
}
)

#Set application.debug=true to enable tracebacks on Beanstalk log output.
#Make sure to remove this line before deploying to production.
application.debug=True

@application.route('/')
def hello_world():
    return "Hello! This is the VTHacks server."

@application.route('/get_credentials')
def get_credentials():
    response = _sts.get_federation_token(policy=sns_policy)
    return {'accessKeyID': response.credentials.access_key,
            'secretAccessKey': response.credentials.secret_key,
            'securityToken': response.credentials.session_token,
            'expiration': response.credentials.expiration}

if __name__ == '__main__':
    application.run(host='0.0.0.0', debug=True)
