from selenium import webdriver
from bs4 import BeautifulSoup
import datetime
import http.client, urllib
import time
from colorama import Fore, Back, Style, init as colorama_init
import sys
import json
import os
from dotenv import load_dotenv

load_dotenv()
colorama_init()

PUSHOVER_API_TOKEN = os.environ['PUSHOVER_API_TOKEN']
PUSHOVER_USER_KEY = os.environ['PUSHOVER_USER_KEY']

start_url = ''
appointment_url = ''
doc_name = ['']
before_date = datetime.date(2024, 6, 11)

last_message_char_count = 0

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("Accept-Language=en-US,en;q=0.9,lt;q=0.8")
chrome_options.add_argument("--disable-network-throttling")
browser = webdriver.Chrome(options=chrome_options)

def clean_print(message):
    global last_message_char_count
    padded_message = message + ' ' * max(0, last_message_char_count - len(message))
    last_message_char_count = len(padded_message)
    sys.stdout.write('\r' + padded_message)
    sys.stdout.flush()

def countdown_timer(seconds):
    for i in range(seconds, 0, -1):
        clean_print(f"{Fore.BLACK}{Back.WHITE}Time until next reload:{Style.RESET_ALL} {i}s")
        time.sleep(1)
    clean_print('')


def notify(msg):
    pushover_conn = http.client.HTTPSConnection("api.pushover.net:443")
    try:
        pushover_conn.request("POST", "/1/messages.json",
            urllib.parse.urlencode({
              "token": PUSHOVER_API_TOKEN,
              "user": PUSHOVER_USER_KEY,
              "message": msg,
            }), {"Content-type": "application/x-www-form-urlencoded"})
        pushover_conn.getresponse()
    except Exception as e:
        print("Error:", e)
    time.sleep(1)

def process_data():
    html_content = browser.page_source
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find_all('tr', class_='values')
    database_data = {"data": []}

    try:
        with open('data.json', 'r') as json_file:
            database_data = json.load(json_file)
    except FileNotFoundError:
        database_data = {"data": []}
    except Exception as e:
        print(f"JSON file error: {e}")
    
    if rows:
        for row in rows:
            row_doc = row.find('td', class_='doc').find('a').text
            date_list = row.find('td', class_='date').text[:10].split('-')
            row_date = datetime.date(int(date_list[0]), int(date_list[1]), int(date_list[2]))
            
            if any(entry['doc'] == row_doc and entry['date'] == str(row_date) for entry in database_data["data"]):
                continue
            
            if doc_name:
                if row_doc in doc_name:
                    if row_date < before_date:
                        database_data["data"].append({'doc': row_doc, 'date': str(row_date)})
                        print(f'{row_date}, {row_doc}')
                        notify(f"{row_date}, {row_doc}")
            else:
                if row_date < before_date:
                    database_data["data"].append({'doc': row_doc, 'date': str(row_date)})
                    print(f'{row_date}, {row_doc}')
                    notify(f"{row_date}, {row_doc}")
    with open('data.json', 'w') as json_file:
        json.dump(database_data, json_file, indent=2)

try:
    while True:
        try:
            while True:
                browser.get(start_url)
                browser.execute_script("localStorage.setItem('randid', '')")
                input("\rPress Enter after manually logging in...")
                # Login opens the app in a new tab; switch to it
                browser.close()
                browser.switch_to.window(browser.window_handles[-1])
                try:
                    while True:
                        # A redirect away from the appointments page means the session was lost
                        if browser.current_url != appointment_url:
                            browser.get(appointment_url)
                            if browser.current_url != appointment_url:
                                notify('[SESSION LOST] login required...')
                                break
                            else:
                                process_data()
                        else:
                            process_data()
                        countdown_timer(300)
                        browser.refresh()
                except KeyboardInterrupt:
                    clean_print('Back to sign-in...')
                    pass
        except KeyboardInterrupt:
            browser.quit()
            clean_print(f'{Fore.WHITE}{Back.RED}Script stopped{Style.RESET_ALL}')
            sys.exit(1)
            pass
        except Exception as e:
            print(f"\n\rAn unexpected error occurred: {e}")
            break
except Exception as e:
    print(f"\n\rAn unexpected error occurred: {e}")
    browser.quit()
    pass