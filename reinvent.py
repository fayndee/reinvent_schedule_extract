############################################################################################
#### AWS re:Invent 2017 - Session Information Downloader
# Provides a quick dirty way to export AWS re:Invent session content from the event website.
# Requirements:
#   1. Update your event website credentials in the USERNAME and PASSWORD vars.
#   2. Download the Chrome web driver (https://sites.google.com/a/chromium.org/chromedriver/downloads).
#   3. Change the CHROME_DRIVER var to point to the driver location.
#
# @author Matt Adorjan
# @email matt.adorjan@gmail.com
############################################################################################

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import os
import requests
from time import sleep
from bs4 import BeautifulSoup
import re
from datetime import datetime
from datetime import time

# Search parameters
VENUE_CODES = {
    "Venetian": 22188,
    "Encore": 728,
    "Aria": 22191,
    "MGM": 22190,
    "Mirage": 22583,
    "BELLAGIO": 22584,
    "VDARA": 24372
}
DAY_CODES = {
    "Monday": 170,
    "Tuesday": 31,
    "Wednesday": 110,
    "Thursday": 111,
    "Friday": 112
}
SESSION_TYPE_CODES = {
    "Builders Session": 1781,
    "Chalk Talk": 1700,
    "Demo Session": 1560,
    "General Activity": 1140,
    "Hackathon": 1040,
    "Lightning Talk": 1440,
    "Security Jam": 1640,
    "Session": 2,
    "Spotlight Lab": 1780,
    "Worshop": 1000
}

# Set username and password for reinvent event website
USERNAME = 'USERNAME'
PASSWORD = 'PASSWORD'

# Chrome web driver path
CHROME_DRIVER = './chromedriver'

# Set to False to ignore SSL certificate validation in Requests package
REQ_VERIFY = False

# Initialize headless chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
content_to_parse = ''
sessions = []

driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=CHROME_DRIVER)

def login(chrome_driver, username, password):
    '''
    Handle user login to the reinvent session catalog.
    Utilizes headless chrome, passing in username and password
    '''
    chrome_driver.get("https://www.portal.reinvent.awsevents.com/connect/login.ww")
    cookie_button = chrome_driver.find_element_by_id("cookieAgreementAcceptButton")
    cookie_button.click()
    username_field = chrome_driver.find_element_by_id("loginUsername")
    username_field.send_keys(username)
    password_field = chrome_driver.find_element_by_id("loginPassword")
    password_field.send_keys(password)
    login_button = chrome_driver.find_element_by_id("loginButton")
    login_button.click()

def get_session_time(session_id):
    '''
    Calls the API on the reinvent event website which returns session times.
    Outputs a JSON object with time and room information for a specific session.
    '''
    url = 'https://www.portal.reinvent.awsevents.com/connect/dwr/call/plaincall/ConnectAjax.getSchedulingJSON.dwr'
    data = {
        "callCount": 1,
        "windowName": "",
        "c0-scriptName": "ConnectAjax",
        "c0-methodName": "getSchedulingJSON",
        "c0-id": 0,
        "c0-param0": "number:" + session_id,
        "c0-param1": "false",
        "batchId": 5,
        "instanceId": 0,
        "page": "%2Fconnect%2Fsearch.ww",
        "scriptSessionId": "1234567"
    }
    headers = {'Content-Type': 'text/plain'}
    r = requests.post(url, headers=headers, data=data, verify=REQ_VERIFY)
    returned = r.content.decode('unicode-escape')
    returned = returned.replace("\\", '')

    # Returns in XHR format. Strip out the relevant information.
    start_time = search(r"startTime\":(\".*?\")", returned)
    end_time = search(r"endTime\":(\".*?\")", returned)
    room = search(r"room\":(\".*?\")", returned)

    time_information = {
        # start_time & end_time transformation to ease Excel formatting
        # Wednesday, Nov 28, 5:30 PM -> 28/11/2018 17:30:00
        # 5:30 PM -> 17:00:00
        "start_time": datetime.strptime(start_time.replace('"', ''), "%A, %b %d, %I:%M %p").strftime("%d/%m/%Y %H:%M:%S"),
        "end_time": datetime.strptime(end_time.replace('"', ''), "%I:%M %p").strftime("%H:%M:%S"),
        "room": room.replace('"', ''),
        "day": start_time.replace('"', '')[:start_time.replace('"', '').find(',')]
    }

    return time_information

def search(value_exp, content):
    result = re.search(value_exp, content, re.DOTALL | re.MULTILINE)
    if result is None:
        return ''
    else:
        return result.group(1)

def parse_sessions(html_content):
    # Start the process of grabbing out relevant session information and writing to a file
    #soup = BeautifulSoup(content_to_parse, "html5lib")
    soup = BeautifulSoup(html_content, "html.parser")

    # In some event titles, there are audio options available inside of an 'i' tag
    # Strip out all 'i' tags to make this easier on BS
    # Hopefully there is no other italicized text that I'm removing
    for i in soup.find_all('i'):
        i.extract()

    # Grab all of the sessionRows from the final set of HTML and work only with that
    return soup.find_all("div", class_="sessionRow")

# Login to the reinvent website
login(driver, USERNAME, PASSWORD)

# Getting content by day, instead of the entire set, because sometimes the
# Get More Results link stops working on the full list. Haven't had issues
# looking at the lists day by day.
for day, day_id in DAY_CODES.items():
    for venue, venue_id in VENUE_CODES.items():
        url = "https://www.portal.reinvent.awsevents.com/connect/search.ww#loadSearch-searchPhrase=&searchType=session&tc=0&sortBy=daytime&dayID={0}&p=&i(728)={1}".format(day_id, venue_id)
        print ("Getting content at {0} on {1}...".format(venue, day))
        driver.get("http://google.com")
        driver.get(url)
        sleep(2)
        more_results = True
        # Click through all of the session results pages for a specific day.
        # The goal is to get the full list for a day loaded.
        while(more_results):
            try:
                # Find the Get More Results link and click it to load next sessions
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                get_results_btn = driver.find_element_by_link_text("Get More Results")
                print ("Getting more results...")
                get_results_btn.click()
                sleep(2)
            except NoSuchElementException as e:
                more_results = False

        # Once all sessions for the day have been loaded by the headless browser,
        # append to a variable for use in BS.
        # content_to_parse = content_to_parse + driver.page_source
        parsed = parse_sessions(driver.page_source)
        print ("{0} sessions found.".format(len(parsed)))
        sessions = sessions + parsed

driver.close()

# # Start the process of grabbing out relevant session information and writing to a file
# #soup = BeautifulSoup(content_to_parse, "html5lib")
# soup = BeautifulSoup(content_to_parse, "html.parser")
#
# # In some event titles, there are audio options available inside of an 'i' tag
# # Strip out all 'i' tags to make this easier on BS
# # Hopefully there is no other italicized text that I'm removing
# for i in soup.find_all('i'):
#     i.extract()
#
# # Grab all of the sessionRows from the final set of HTML and work only with that
# sessions = soup.find_all("div", class_="sessionRow")

# Open a blank text file to write sessions to
with open("sessions.txt","w") as file:
# Create a header row for the file. Note the PIPE (|) DELIMITER.
    file.write("Session Number|Session Type|Session Title|Session Interest|Start Time|End Time|Room and Building|Day of Week\n")


    # For each session, pull out the relevant fields and write them to the sessions.txt file.
    for session in sessions:
        session_soup = BeautifulSoup(str(session), "html.parser")
        session_id = session_soup.find("div", class_="sessionRow")
        session_id = session_id['id']
        session_id = session_id[session_id.find("_")+1:]
        session_timing = get_session_time(session_id)
        session_number = session_soup.find("span", class_="abbreviation")
        session_number = session_number.string.replace(" - ", "")

        session_title = session_soup.find("span", class_="title")
        session_title = session_title.string.encode('utf-8').rstrip()
        session_title = session_title.decode('utf-8')

        session_type = session_soup.find("small", class_="type")
        session_type = session_type.string

        session_abstract = session_soup.find("span", class_="abstract")

        session_interest = session_soup.find("a", class_="interested")

        if (session_interest == None):
            session_interest = False
        else:
            session_interest = True

        write_contents = str(session_number) + "|" + session_type + "|" + session_title + "|" + str(session_interest) + "|" + str(session_timing['start_time']) + "|" + str(session_timing['end_time']) + "|" + str(session_timing['room'] + "|" + str(session_timing['day']))
        file.write(write_contents.strip() + "\n")
        # Print the session title for each session written to the file
        print (session_title.encode('utf-8').strip())
