from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common import exceptions 
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

def find_assets(website, item_count, item_type):
    found_targets = []

    if os.getenv('TARGET_ATTRIBUTES'):
        target_attributes = os.getenv('TARGET_ATTRIBUTES').split(',')
    else:
        target_attributes = ["src", "data-lazy-src", "content", "href", "src", "srcset"]
    if os.getenv('CDN_URL'):
        cdn_url = os.getenv('CDN_URL')
    else:
        cdn_url = False

    chrome_options = Options()
    if os.getenv('DRIVER_OPTIONS'):
        for option in os.getenv('DRIVER_OPTIONS').split(','):
            chrome_options.add_argument(option)
    else:
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--allow-insecure-localhost")
        chrome_options.add_argument("--whitelisted-ips=\"\"")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-dev-shm-usage")
    port = int(os.getenv('DRIVER_PORT')) if os.getenv('DRIVER_PORT') else 4444
    web_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                                             options=chrome_options, port=port, service_args=[f'--log-path=/dev/null',])
    web_driver.implicitly_wait(10)
    headers = {
        "authority": website.strip(),
        "referer": website.strip(),
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "sec-fetch-dest": "document",
        "accept-language": "en-US,en;q=0.9,tr;q=0.8",
    }

    for i in range(item_count):
        if item_type == 'posts':
            post_data = requests.get(
                website.strip() + "/wp-json/wp/v2/posts?page=" + str(i + 1), headers=headers
            ).json()
        else:
            post_data = requests.get(
                website.strip() + "/wp-json/wp/v2/pages?page=" + str(i + 1), headers=headers
            ).json()
        for data in post_data:
            try:
                web_driver.get(data["link"])
                element_list = web_driver.find_elements(By.XPATH, '//*')

                for e in element_list:
                    for atr in target_attributes:
                        if e.get_attribute(atr):
                            if e.get_attribute(atr) in found_targets:
                                logging.debug(f"Skipping duplicate target for: {data['link']}.")
                            elif "xmlrpc" in e.get_attribute(atr):
                                logging.debug(f"Skipping xmlrpc link for: {data['link']}.")
                            elif atr == 'srcset':
                                srcset = e.get_attribute(atr).split(' ')
                                for src in srcset:
                                    if "https" in src:
                                        found_targets.append([data['link'], src])
                                logging.debug(f"Found attribute: {atr}")
                            elif website.strip() in e.get_attribute(atr):
                                found_targets.append([data['link'], e.get_attribute(atr)])
                                logging.debug(f"Found attribute: {atr}")
                            elif cdn_url and cdn_url.strip() in e.get_attribute(atr):
                                found_targets.append([data['link'], e.get_attribute(atr)])
                                logging.debug(f"Found attribute: {atr}")
                        else:
                            logging.debug(f"Source invalid for: {data['link']}.")
            except exceptions.StaleElementReferenceException as e:
                logging.error(f"{data['link']}: stale element reference: element is not attached to the page document")
                bad_targets.append([website.strip(), data['link'], "Stale Element Reference Exception"])
    web_driver.close()
    return found_targets

"""
Starts each thread for multi-threading support.
Takes: List of Elements, and the Site being Scanned
Loops through the found URLs and checks for a status code in the known good range (200-299).
Should loop through the entire site the way it is designed right now.
"""
def StartThread(site_list):
    for target_site in site_list:
        headers = {
            "authority": target_site.strip(),
            "referer": target_site.strip(),
            "user-agent": "WilsonCode WPAssetCheckerBot 1.0",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "sec-fetch-dest": "document",
            "accept-language": "en-US,en;q=0.9,tr;q=0.8",
        }
        logging.info(f"Starting on site {target_site}")
        found_targets = []
        checked_targets = []
        posts_pages = int(requests.get(target_site.strip() + "/wp-json/wp/v2/posts", headers=headers).headers["X-WP-TotalPages"])
        pages_pages = int(requests.get(target_site.strip() + "/wp-json/wp/v2/pages", headers=headers).headers["X-WP-TotalPages"])
        total_posts = int(requests.get(target_site.strip() + "/wp-json/wp/v2/posts", headers=headers).headers["X-WP-Total"])
        total_pages = int(requests.get(target_site.strip() + "/wp-json/wp/v2/pages", headers=headers).headers["X-WP-Total"])

        logging.info(f"{total_posts} posts to scan for {target_site}")
        logging.info(f"{total_pages} pages to scan for {target_site}")
        found_targets.extend(find_assets(target_site, posts_pages, 'posts'))
        found_targets.extend(find_assets(target_site, pages_pages, 'pages'))

        for target in found_targets:
            try:
                if target[1] in checked_targets:
                    logging.debug(f"Target already checked: {target[1]}.")
                else:
                    for ignore in ["googleapis", "gstatic", "googletagmanager", "linkedin", "fbcdn", "jquery", "w3"]:
                        if ignore in target[1]:
                            checked_targets.append(target[1])
                            logging.debug(f"Skipping ignored words found. Skipping: {target[1]}.")
                    for ext in [".css",".js",".png",".jpeg"]:
                        if ext in target[1]:
                            checked_targets.append(target[1])
                            if int(requests.get(target[1]).status_code) == 200:
                                logging.debug("Valid source: {target}.")
                            else:
                                status_code = requests.get(target).status_code
                                logging.info(f"Possible bad link found (Status Code: {status_code}): {target[1]}.")
                                bad_targets.append([target_site.strip(), target[0], status_code])
            except (
                requests.exceptions.SSLError,
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.MissingSchema,
                requests.exceptions.Timeout,
                requests.exceptions.InvalidSchema,
                ) as errh:
                    bad_targets.append([target_site.strip(), target[0], "Unkown Error"])
        logging.info("Thread done processing")

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
        for x in range(0, len(sites), 2):
            thread = threading.Thread(target=StartThread, args=(sites[x:x + 2],))
            threads.append(thread)
            thread.start()
        for t in threads:
            t.join()

    with open(f"./resources/{results_file}", 'w') as f:
        header_row = ["Host", "Page", "Status Code"]
        write = csv.writer(f)
        write.writerow(header_row)
        for item in bad_targets:
            write.writerow(item)
    end_time = datetime.now()
    total_time = end_time - start_time
    logging.info(f'Duration: {total_time}')

