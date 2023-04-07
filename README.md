# Gunicorn-Manager

1. Gunicorn-Manager is a simple web interface for managing gunicorn processes.
2. This is a simple PSUTIL and SIGNAL based Streamlit app which can be used to manage gunicorn processes and it's workers.
3. While I was going through the gunicorn documentation, I found that there is no way to manage gunicorn processes and it's workers.
4. Deploying gunicorn with systemd is not a good idea for me everytime I need to use terminal to restart for any changes. So I decided to write a simple web interface for managing gunicorn processes.
5. Also CI/CD in gunicorn based processes is hard enough since I couldn't find much documentation or ways to do it. So I decided to write a simple web interface for managing gunicorn processes which you can also use to deploy your application in production with 0 downtime.


## Usage

    $ python3 gunicorn-manager.py

## Requirements
    
        $ pip3 install streamlit requests pygit2

## Features

1. List all gunicorn processes and it's workers.
2. Restart gunicorn processes and it's workers.
3. Stop gunicorn processes and it's workers.
4. Start gunicorn processes and it's workers.
5. Shows memory usage of gunicorn processes and it's workers.
6. Increase/Decrease number of workers for gunicorn processes.
7. 0 Downtime and CI/CD friendly for test as well as production environment.
8. Also connect your github/gitlab repository to the application and use it to checkout any branch and deploy it in production with 0 downtime.


## How and Why do I say it's 0 Downtime and CI/CD friendly?

Gunicorn can restart it's workers (process), when number of workers > 1 and running worker is killed with signal TERM
By using signal TERM, the worker will be gracefully shutdown and it will not accept any new requests but only shutdown when it's current request is completed, making sure that there is no downtime for the application.


1. So basically just pull your updated code from git branch
2. Turn on gunicorn manager code on browser
3. Just click on restart button for any gunicorn worker
4. It will take some time according to your code/application bootup time
5. The new worker will be up and running with new code
6. Keep doing this for all gunicorn workers until all workers are up and running with new code

## Screenshots

![Gunicorn-Manager](
https://raw.githubusercontent.com/leetanshaj/Gunicorn-Manager/main/gunicorn-manager.png)
