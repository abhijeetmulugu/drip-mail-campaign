import json
import flask
import httplib2
import email
import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import discovery, errors
from oauth2client import client
from flask import render_template
from flask import request
from flask_sqlalchemy import SQLAlchemy

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "testdatabase.db"))

app = flask.Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = database_file
db = SQLAlchemy(app)

class Campaign(db.Model):
    campaignId = db.Column(db.Integer,autoincrement=True,primary_key=True)
    campaignName=db.Column(db.String(80),unique=True,nullable=False)
    stages = db.Column(db.Integer,nullable=False)

    def __init__(self, campaignName, stages):
        self.campaignName = campaignName
        self.stages = stages




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
                campaignName=request.form.get("campaignName"),
                stages=request.form.get("stages")
            )
            db.session.add(campaign)
            db.session.commit()
            return render_template("emailTemplates.html",stages=campaign.stages)



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
            print (request.form)
        return render_template("home.html")




@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        'client_secret.json',
        scope='https://mail.google.com/',
        redirect_uri=flask.url_for('oauth2callback', _external=True)
    )
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        flask.session['credentials'] = credentials.to_json()
        return flask.redirect(flask.url_for('index'))

@app.route('/getmail')
def getmail():
    if 'credentials' not in flask.session:
        return flask.redirect(flask.url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
    if credentials.access_token_expired:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        http_auth = credentials.authorize(httplib2.Http())
        gmail_service = discovery.build('gmail', 'v1', http_auth)
        query = 'from:sachin@tryscribe.com'
        """List all Messages of the user's mailbox matching the query.

        Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        query: String used to filter messages returned.
        Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

        Returns:
        List of Messages that match the criteria of the query. Note that the
        returned list contains Message IDs, you must use get with the
        appropriate ID to get the details of a Message.
        """
        try:
            response = gmail_service.users().messages().list(userId='me', q=query).execute()
            messages = []
            if 'messages' in response:
                print ('test %s' % response)
                messages.extend(response['messages'])
            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = gmail_service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
                messages.extend(response['messages'])

            return flask.jsonify({'data': messages})
        except errors:
            print ('An error occurred: %s' % errors)

@app.route('/sendmail')
def SendMessage():
    if 'credentials' not in flask.session:
        return flask.redirect(flask.url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
    if credentials.access_token_expired:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        http_auth = credentials.authorize(httplib2.Http())

        message = CreateMessage('abhijeetmulugu27@gmail.com','f2013494@hyderabad.bits-pilani.ac.in','test','','this is a test mail')
        gmail_service = discovery.build('gmail', 'v1', http_auth)
        """Send an email message.
            Args:
                  service: Authorized Gmail API service instance.
                  user_id: User's email address. The special value "me"
                        can be used to indicate the authenticated user.
                  message: Message to be sent.
            Returns:
                  Sent Message.    """
        try:
            sentmessage = (gmail_service.users().messages().send(userId='me', body=message)
                   .execute())
            print('Message Id: %s' % sentmessage['id'])
            return flask.jsonify({'data': sentmessage})
        except errors.HttpError as error:
            print('An error occurred: %s' % error)

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



if __name__ == '__main__':
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.debug = True
    app.run()
