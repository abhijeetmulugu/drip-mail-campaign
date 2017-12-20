import json
import flask
import email
import os
import base64
import logging
import re
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
from datetime import datetime,timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import discovery, errors
from oauth2client import client
from flask import render_template
from flask import request,redirect
from flask_sqlalchemy import SQLAlchemy



SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
    # Add other requested scopes.
]

CLIENTSECRETS_LOCATION = 'client_secret.json'
REDIRECT_URI = 'http://localhost:5000/oauth2callback'

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "sqlLite.db"))

app = flask.Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = database_file
db = SQLAlchemy(app)

class Campaign(db.Model):
    campaignId = db.Column(db.Integer,autoincrement=True,primary_key=True)
    userId=db.Column(db.String,nullable=False)
    campaignName=db.Column(db.String(80),unique=True,nullable=False)
    stages = db.Column(db.Integer,nullable=False)
    days=db.Column(db.Integer,nullable=False)
    subscribers = db.Column(db.Integer)

class Templates(db.Model):
    id = db.Column(db.Integer,autoincrement=True,primary_key=True)
    campaignName=db.Column(db.String(80),nullable=False)
    stages = db.Column(db.Integer,nullable=False)
    emailTemplate=db.Column(db.String(400),nullable=False)
    timeToSend = db.Column(db.DateTime)
    mailStatus = db.Column(db.Integer,default=0)

class Users(db.Model):
    userId = db.Column(db.String,primary_key=True,unique=True,nullable=False)
    emailId=db.Column(db.String)
    credentials = db.Column(db.String,nullable=False)

class Subscribers(db.Model):
    emailId = db.Column(db.String,primary_key=True,unique=True,nullable=False)
    name = db.Column(db.String)
    campaignName = db.Column(db.String, nullable=False)





@app.route('/',methods=["GET", "POST"])
def index():
    if 'credentials' not in flask.session:
        return flask.redirect(flask.url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
    if credentials.access_token_expired:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        # http_auth = credentials.authorize(httplib2.Http())
        # gmail_service = discovery.build('gmail', 'v1', http_auth)
        # threads = gmail_service.users().threads().list(userId='me').execute()
        if request.form:

            campaign = Campaign(
                userId = request.form.get("userId"),
                campaignName=request.form.get("campaignName"),
                stages=request.form.get("stages"),
                days = request.form.get("days"),
                subscribers = request.form.get("subscribers")
            )
            db.session.add(campaign)
            db.session.commit()
            return render_template("emailTemplates.html",stages=campaign.stages,campaignName=campaign.campaignName,days=campaign.days,subscribers=campaign.subscribers)



        return render_template("home.html")

@app.route('/addTemplates',methods=["POST"])
def addTemplates():
    if 'credentials' not in flask.session:
        return flask.redirect(flask.url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
    if credentials.access_token_expired:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        if(request.form):
            stages = int(request.form.get("stages"))
            days = int(request.form.get("days"))
            subscribers = int(request.form.get("subscribers"))
            now = datetime.now()+timedelta(days=1)

            for k in range(1,subscribers+1):
                subscriber=Subscribers(
                    emailId = request.form.get("email-"+str(k)),
                    name = request.form.get("subcriber-"+str(k)),
                    campaignName = request.form.get("campaignName")
                )
                db.session.add(subscriber)

            for i in range(1,stages+1):
                template = Templates(
                    campaignName = request.form.get("campaignName"),
                    stages = i,
                    emailTemplate = request.form.get("stage-"+str(i)),
                    timeToSend= now
                )
                db.session.add(template)
                now=now+timedelta(days=days)

            db.session.commit()
            print (request.form)
        return render_template("thankyou.html")




@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        'client_secret.json',
        ' '.join(SCOPES),
        redirect_uri=flask.url_for('oauth2callback', _external=True)
    )
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        credentials = exchange_code(auth_code)
        user_info = get_user_info(credentials)
        email_address = user_info.get('email')
        user_id = user_info.get('id')
        if credentials.refresh_token is not None:
            store_credentials(user_id, credentials,email_address)

        flask.session['credentials'] = credentials.to_json()
        return render_template("home.html",userId=user_id)



# @app.route('/sendmail')
def SendMessage():

        templates = Templates.query.filter_by(mailStatus=0).all()

        for template in templates:
            if (datetime.now().day == template.timeToSend.day) and (template.mailStatus==0):
                campaign=Campaign.query.filter_by(campaignName=template.campaignName).first()

                user=get_stored_credentials(campaign.userId)
                credentials = client.Credentials.new_from_json(user.credentials)

                subscribers = Subscribers.query.filter_by(campaignName=template.campaignName).all()


                sender = user.emailId
                mail=template.emailTemplate

                for subscriber in subscribers:

                    customMail = mail.format(name=subscriber.name)
                    message = CreateMessage(sender,subscriber.emailId,campaign.campaignName,customMail,'')
                    gmail_service = discovery.build('gmail', 'v1', credentials.authorize(httplib2.Http()))
                    try:
                        sentmessage = (gmail_service.users().messages().send(userId='me', body=message)
                                   .execute())
                        print('Message Id: %s' % sentmessage['id'])

                    except:
                        pass
                template.mailStatus=1
        db.session.commit()

def CreateMessage(sender, to, subject, msgHtml, msgPlain):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    msg.attach(MIMEText(msgPlain, 'plain'))
    msg.attach(MIMEText(msgHtml, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes())
    raw = raw.decode()
    body = {'raw': raw}
    return body

# @app.route('/getmail')
def getmail():

    campaigns = Campaign.query.all()

    for campaign in campaigns:

        user=get_stored_credentials(campaign.userId)
        credentials = client.OAuth2Credentials.new_from_json(user.credentials)
        http_auth = credentials.authorize(httplib2.Http())
        gmail_service = discovery.build('gmail', 'v1', http_auth)

        subscribers = Subscribers.query.filter_by(campaignName=campaign.campaignName).all()

        for subscriber in subscribers:
            print(subscriber)
            query = 'from:' + subscriber.emailId
            try:
                response = gmail_service.users().messages().list(userId='me', q=query).execute()
                messages = []
                if 'messages' in response:
                    messages.extend(response['messages'])
                while 'nextPageToken' in response:
                    page_token = response['nextPageToken']
                    response = gmail_service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
                    messages.extend(response['messages'])

                print(messages)

                for message in messages:
                    print(message)
                    GetMessage(gmail_service,message["id"],subscriber.emailId)
            except:
                pass



# @app.route('/readmail')
def GetMessage(service, messageId, emailId):
    keywords = ["stop", "unsubscribe","Stop","Unsubscribe"]

    try:
        message = service.users().messages().get(userId="me", id=messageId, format="full").execute()
        payload = message['payload']
        mssg_parts = payload['parts']  # fetching the message parts
        part_one = mssg_parts[0]  # fetching first element of the part
        part_body = part_one['body']  # fetching body of the message
        part_data = part_body['data']
        clean_one = part_data.replace("-", "+")  # decoding from Base64 to UTF-8
        clean_one = clean_one.replace("_", "/")  # decoding from Base64 to UTF-8
        clean_two = base64.b64decode(bytes(clean_one, 'UTF-8'))  # fetching data from the body

        msg1 = str(clean_two).replace("\\r\\n", " ")

        msg = re.split(';|\t |\ |\\ |\,|\<|\>|\.|\@|\:|\'', msg1)

        for word in msg:
            if word in keywords:
                print(word)
                subscriber = Subscribers.query.filter_by(emailId=emailId).first()
                db.session.delete(subscriber)
                db.session.commit()
    except :
        pass


class GetCredentialsException(Exception):

    def __init__(self, authorization_url):
        """Construct a GetCredentialsException."""
        self.authorization_url = authorization_url


class CodeExchangeException(GetCredentialsException):
    """Error raised when a code exchange has failed."""


class NoRefreshTokenException(GetCredentialsException):
    """Error raised when no refresh token has been found."""


class NoUserIdException(Exception):
    """Error raised when no user ID could be retrieved."""


def get_stored_credentials(user_id):
    user = Users.query.filter_by(userId=user_id).first()
    return user


def store_credentials(user_id, credentials,emailId):
        user = Users(
            userId=user_id,
            emailId=emailId,
            credentials= str(credentials.to_json())
        )
        db.session.add(user)
        db.session.commit()




def exchange_code(authorization_code):
    flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
    flow.redirect_uri = REDIRECT_URI
    try:
        credentials = flow.step2_exchange(authorization_code)
        return credentials
    except FlowExchangeError as error:
        logging.error('An error occurred: %s', error)
        raise CodeExchangeException(None)


def get_user_info(credentials):
    user_info_service = discovery.build(
        serviceName='oauth2', version='v2',
        http=credentials.authorize(httplib2.Http()))
    user_info = None
    try:
        user_info = user_info_service.userinfo().get().execute()
    except errors.HttpError as e:
        logging.error('An error occurred: %s', e)
    if user_info and user_info.get('id'):
        return user_info
    else:
        raise NoUserIdException()


if __name__ == '__main__':
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.debug = True
    app.run()
