import flask

application = flask.Flask(__name__)

#Set application.debug=true to enable tracebacks on Beanstalk log output.
#Make sure to remove this line before deploying to production.
application.debug=True

@application.route('/')
def hello_world():
    return "Hello! This is the VTHacks server."

@application.route('/get_credentials')
def get_credentials():
    return 'this should return temporary credentials'

    #response = _sts.get_federation_token(policy=policy)
    #return {'accessKeyID': response.credentials.access_key,
            #'secretAccessKey': response.credentials.secret_key,
            #'securityToken': response.credentials.session_token,
            #'expiration': response.credentials.expiration}

if __name__ == '__main__':
    application.run(host='0.0.0.0', debug=True)
