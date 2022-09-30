from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import selenium.common.exceptions
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
Starts each thread for multi-threading support.
Takes: List of Elements, and the Site being Scanned
Loops through the found URLs and checks for a status code in the known good range (200-299).
Should loop through the entire site the way it is designed right now.
"""
def StartThread(site_list):
    if os.getenv('TARGET_ATTRIBUTES'):
        target_attributes = os.getenv('TARGET_ATTRIBUTES').split(',')
    else:
        target_attributes = ["src", "data-lazy-src", "content", "href", "src", "srcset"]
    cdn_url = os.getenv('CDN_URL') if os.getenv('CDN_URL') else "ihealthspot"
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

    
    for target_site in site_list:
        found_targets = []
        checked_targets = []
        thread_web_driver.get(target_site)
        element_list = thread_web_driver.find_elements(By.XPATH, '//*')

        for e in element_list:
            for atr in target_attributes:
                if e.get_attribute(atr):
                    if e.get_attribute(atr) in found_targets:
                        logging.debug(f"Target already found: {target}.")
                    elif "xmlrpc" in e.get_attribute(atr):
                        logging.debug(f"Skipping xmlrpc link: {target}.")
                    elif atr == 'srcset':
                        srcset = e.get_attribute(atr).split(' ')
                        for src in srcset:
                            if "https" in src:
                                found_targets.append(src)
                                logging.info(src)
                    elif target_site.strip() in e.get_attribute(atr):
                        found_targets.append(e.get_attribute(atr))
                        logging.info(e.get_attribute(atr))
                    elif cdn_url.strip() in e.get_attribute(atr):
                        found_targets.append(e.get_attribute(atr))
                        logging.info(e.get_attribute(atr))
                    else:
                        logging.debug("Source invalid: {target}.")
        
        for target in found_targets:
            try:
                for ext in [".css",".js",".png",".jpeg"]:
                    if ext in target:
                        checked_targets.append(target)
                        if requests.get(target).status_code == 200:
                            logging.debug("Valid source: {target}.")
                        else:
                            status_code = requests.get(target).status_code
                            logging.info(f"Possible bad link found (Status Code: {status_code}): {target}.")
                            bad_targets.append([target_site, status_code, target])
                for ignore in ["googleapis", "gstatic", "googletagmanager", "linkedin", "fbcdn", "jquery", "w3"]:
                    if ignore in target:
                        checked_targets.append(target)
                        logging.debug(f"Skipping ignored words found. Skipping: {target}.")
                if target in checked_targets:
                    logging.debug(f"Target already checked: {target}.")
                elif requests.get(target).status_code == 200:
                    checked_targets.append(target)
                    thread_web_driver.get(target)
                    thread_elements = thread_web_driver.find_elements(By.XPATH, '//*')
                    for e in thread_elements:
                        for atr in target_attributes:
                            if e.get_attribute(atr):
                                if e.get_attribute(atr) in found_targets:
                                    logging.debug(f"Target already found: {target}.")
                                elif "xmlrpc" in e.get_attribute(atr):
                                    logging.debug(f"Skipping xmlrpc link: {target}.")
                                elif atr == 'srcset':
                                    srcset = e.get_attribute(atr).split(' ')
                                    for src in srcset:
                                        if "http" in src:
                                            found_targets.append(src)
                                            logging.info(src)
                                elif "http" in e.get_attribute(atr):
                                    found_targets.append(e.get_attribute(atr))
                                elif target_site.strip() in e.get_attribute(atr):
                                    found_targets.append(e.get_attribute(atr))
                                    logging.info(e.get_attribute(atr))
                                elif cdn_url.strip() in e.get_attribute(atr):
                                    found_targets.append(e.get_attribute(atr))
                                    logging.info(e.get_attribute(atr))
                                else:
                                    logging.debug("Source invalid: {target}.")
                else:
                    status_code = requests.get(target).status_code
                    logging.info(f"Possible bad link found (Status Code: {status_code}): {target}.")
                    bad_targets.append([target_site, status_code, target])
            except selenium.common.exceptions.InvalidSessionIdException as er:
                logging.error(f"Error processing {target} \n {er}")
            except selenium.common.exceptions.StaleElementReferenceException as er:
                logging.error(f"Error processing {target} \n {er}")
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

    with open(f"./resources/{site_file}", 'r') as f:
        sites = f.readlines()
        threads = []
        for x in range(0, len(sites), 50):
            thread = threading.Thread(target=StartThread, args=(sites[x:x + 50],))
            threads.append(thread)
            thread.start()
        for t in threads:
            t.join()

    with open(f"./resources/{results_file}", 'w') as f:
        header_row = ["Host", "Status Code", "URL"]
        write = csv.writer(f)
        write.writerow(header_row)
        for item in bad_targets:
            write.writerow(item)
    end_time = datetime.now()
    total_time = end_time - start_time
    logging.info(f'Duration: {total_time}')

