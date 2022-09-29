from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import requests
import logging
from datetime import datetime
import threading
import csv
import os

"""
Setup our logging format.
Log file set to ./logs/asset_checker.log
"""
getDate = datetime.now().strftime("%m/%d/%y")
FORMAT = '(%(threadName)-10s) %(message)s'
logging.basicConfig(filename=f'./logs/asset_checker.log', level=logging.INFO, format=FORMAT)

"""
Global Variables
"""
bad_targets = []


"""
ElementCheck
Returns: list, string, or bool
Takes the element as an argument, and checks if it contains assets we are about.
Limits assets we check to CDN and the site itself.
"""
def ElementCheck(element):
    if os.getenv('TARGET_ATTRIBUTES'):
        target_attributes = os.getenv('TARGET_ATTRIBUTES').split(',')
    else:
        target_attributes = ["src", "data-lazy-src", "content", "href", "src", "srcset"]
    cdn_url = os.getenv('CDN_URL') if os.getenv('CDN_URL') else "media.cdn"
    for atr in target_attributes:
        if element.get_attribute(atr) and \
                (site in element.get_attribute(atr) or cdn_url in element.get_attribute(atr)):
            if "xmlrpc" in element.get_attribute(atr):
                return False
            elif atr == 'srcset':
                srcset = element.get_attribute(atr).split(' ')
                items = []
                for src in srcset:
                    if "https://" in src:
                        items.append(src)
                return items
            else:
                return element.get_attribute(atr)

"""
Starts each thread for multi-threading support.
Takes: List of Elements, and the Site being Scanned
Loops through the found URLs and checks for a status code in the known good range (200-299).
Should loop through the entire site the way it is designed right now.
"""
def StartThread(element_list, target_site):
    thread_chrome_options = Options()
    if os.getenv('DRIVER_OPTIONS'):
        for option in os.getenv('DRIVER_OPTIONS').split(','):
            thread_chrome_options.add_argument(option)
    else:
        thread_chrome_options.add_argument("--no-sandbox")
        thread_chrome_options.add_argument("--disable-gpu")
        thread_chrome_options.add_argument("--disable-extensions")
        thread_chrome_options.add_argument("--allow-insecure-localhost")
        thread_chrome_options.add_argument("--whitelisted-ips=\"\"")
        thread_chrome_options.add_argument("--headless")
        thread_chrome_options.add_argument("--log-level=3")
        thread_chrome_options.add_argument("--disable-dev-shm-usage")
    port = int(os.getenv('DRIVER_PORT')) if os.getenv('DRIVER_PORT') else 4444
    thread_web_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                                             options=thread_chrome_options, port=port)
    found_targets = []
    checked_targets = []
    for e in element_list:
        target = ElementCheck(e)
        if isinstance(target, str):
            if target not in found_targets:
                logging.info(target)
                found_targets.append(target)
        if isinstance(target, list):
            for t in target:
                if t not in found_targets:
                    logging.info(t)
                    found_targets.append(t)

    for target in found_targets:
        if requests.get(target).status_code in range(200, 300) and target not in checked_targets:
            checked_targets.append(target)
            thread_web_driver.get(target)
            thread_elements = thread_web_driver.find_elements(By.XPATH, '//*')
            for e in thread_elements:
                target = ElementCheck(e)
                if isinstance(target, str):
                    if target not in found_targets:
                        found_targets.append(target)
                        logging.info(target)
                if isinstance(target, list):
                    for t in target:
                        if t not in found_targets:
                            found_targets.append(t)
                            logging.info(t)
        else:
            status_code = requests.get(target).status_code
            logging.info(f"Bad link found (Status Code: {status_code}): {target}")
            bad_targets.append([target_site, status_code, target])
    logging.info("Thread done processing")
    thread_web_driver.close()

"""
Main Method
Takes a sites.txt file, and processes each site in the file.
Once completed, outputs the bad assets to a CSV.
"""
if __name__ == '__main__':
    start_time = datetime.now()
    site_file = os.getenv('SITES_FILE') if os.getenv('SITES_FILE') else "sites.txt"
    results_file = os.getenv('RESULTS_FILE') if os.getenv('RESULTS_FILE') else "results.csv"
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--allow-insecure-localhost")
    chrome_options.add_argument("--whitelisted-ips=\"\"")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-dev-shm-usage")
    web_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    with open(f"./resources/{site_file}", 'r') as f:
        lines = f.readlines()
        for site in lines:
            logging.info(f"Starting Site: {site}")
            web_driver.get(site)
            elements = web_driver.find_elements(By.XPATH, '//*')
            for x in range(0, len(elements), 100):
                thread = threading.Thread(target=StartThread, args=(elements[x:x + 100], site,))
                thread.start()

    with open(f"./resources/{results_file}", 'w') as f:
        header_row = ["Host", "Status Code", "URL"]
        write = csv.writer(f)
        write.writerow(header_row)
        write.writerow(bad_targets)
    end_time = datetime.now()
    total_time = end_time - start_time
    logging.info(f'Duration: {total_time}')

