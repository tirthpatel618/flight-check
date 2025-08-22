repo to automate finding cheap flights out of your home airport - want to go explore the world (but sadly i am on tight budget)

How to set up:

Download the script. 

run `pip install -r requirements.txt` to get the required libraries

Get the amaedus API and secret, and get an app password from gmail 

Input those into the .env example file, and rename it just .env

Change the destination, origin or price(hopefully higher than my brokie price) according to your needs

run python file locally and check it out


**Automation**
set it up with github actions or cron or any task scheduler of your choice
    for github actions  
    Set repo variables same as .env
    Download the .yml file in that exact path
    allow the workflow in settings
    Run it once to test, and it should work from there on

