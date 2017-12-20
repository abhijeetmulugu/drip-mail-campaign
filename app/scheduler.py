import schedule
import time


from campaignManager import SendMessage

from campaignManager import getmail

schedule.every().day.at("19:26").do(SendMessage)
schedule.every().day.at("19:28").do(getmail)
while 1:
    schedule.run_pending()
    time.sleep(1)