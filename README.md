#Drip-mail-campaign

Setup a drip campaign which sends mail to your customers over time.

 
##Prerequisites
Python 3

Flask

Google Api Client Library

SqlAlchemy

Scheduler

httplib2

##Setup
-Install the required libraries

-Generate the secret json file from google api console. Rename it to client_secret.json and keep it in the app/ directory.

-Run the following commands:

python3

from campaignManager import db

db.create_all()

exit()

- A db with name sqlLite will  be created in the directory with the following tables:
campaign
subscribers
users
templates



-Run python3 campaignManager.py and python3 scheduler.py in separate consoles

##Setting up the Campaign
-Go to localhost:5000/. The app will redirect to google login page. Log in and provide the prompted permissions. You will redirected back to the campaign home page

-Enter the fields in the form. The stages field is the number of stages in the campaign. The days field is the number of days for subsequent emails.

-In the next page you will be prompted to enter the  user names and emails. While entering the email templates use {name} as a placeholder for name value.

##Working
-The first time a user logs in, the credentials object of that user which contains the refresh token will be stored in the users table and will be used to 
call gmail api to send mails

-The first email will be sent a day later at 12.00 pm whenever the user sets up the campaign. The subsequent emails will be sent as per the users
input at the time of setting up the campaign. All the emails all scheduled to be sent at 12.00pm

-Replies will be detected from each customer with some keywords and in case of match(when the customer replies to stop the campaign),
his information will be deleted from the subscribers table and he will not receive the subsequent emails. Replies are scheduled to occur at 11.30pm

##Schemas
There are 4 tables being used for this project

###users
userId, email and his credentials as provided by the oauth api are stored in this table.

###campaign
campaign information is stored here like the campaign name, no. of users and no. of subscribers

###templates
The email templates according to the corresponding campaign and their respective scheduled times are stored here

###subscribers
The subscribers names and their mails are stored in this table










   