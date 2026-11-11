"""
Environment for Behave Testing
"""

import os
import shutil
from selenium import webdriver

WAIT_SECONDS = int(os.getenv("WAIT_SECONDS", "30"))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
DRIVER = os.getenv("DRIVER", "chrome").lower()


def before_all(context):
    """Executed once before all tests"""
    context.base_url = BASE_URL.rstrip("/")
    context.wait_seconds = WAIT_SECONDS
    # Select either Chrome or Firefox
    if "firefox" in DRIVER:
        context.driver = get_firefox()
    else:
        context.driver = get_chrome()
    context.driver.set_window_size(1280, 1024)
    context.config.setup_logging()


def after_all(context):
    """Executed after all tests"""
    context.driver.quit()


######################################################################
# Utility functions to create web drivers
######################################################################


def get_chrome():
    """Creates a headless Chrome driver"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Use the driver installed in the image instead of letting Selenium download one
    service = webdriver.ChromeService(executable_path=shutil.which("chromedriver"))
    return webdriver.Chrome(options=options, service=service)


def get_firefox():
    """Creates a headless Firefox driver"""
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    service = webdriver.FirefoxService(executable_path=shutil.which("geckodriver"))
    return webdriver.Firefox(options=options, service=service)
