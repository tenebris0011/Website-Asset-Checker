# Website Asset Checker (WordPress)
This tool scans across all websites provided looking for anything that is on the website itself or its CDN.

## Project Setup (no docker)
### Setup venv
```bash
# Linux
python3 -m venv /path/to/new/virtual/environment
# Windows
python -m venv c:\path\to\myenv
```
### Activate venv
- Active venv
```bash
# Linux
source /path/to/venv/bin/activate
# Windows
path\to\venv\Scripts\activate.bat
```
### Install requirements.txt
- Install requirements.txt
```bash
pip install -r requirements.txt
```
### Add required folders
- Create the resources directory in the root directory of the project.
- Add your sites.txt file to the directory, see below example.
- Create logs folder in the root directory of the project.
```
https://www.ihealthspot.com
https://www.medicaladvantage.com
```
- With all of the above completed, you should now be able to execute the script to begin processing.

## Project Setup (docker)
### Add required folders
- Create the resources directory in the root directory of the project.
- Add your sites.txt file to the directory, see below example.
- Create logs folder in the root directory of the project.
### Run the container
- In your root directory of your project run the below commands.
```bash
docker compose build
docker compose up
```
- Once the container is running you can check your logs directory, and tail the logs of the container.
```bash
tail -f ./logs/asset_checker.log
```
