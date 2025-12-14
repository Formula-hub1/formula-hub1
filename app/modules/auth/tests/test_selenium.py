import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from app import create_app
from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.dataset.tests.test_recommender_selenium import wait_for_page_to_load
from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_login_and_check_element():

    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        # Find the username and password field and enter the values
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)

        # Wait a little while to ensure that the action has been completed
        time.sleep(4)

        try:

            driver.find_element(By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Latest datasets')]")
            print("Test passed!")

        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:

        # Close the browser
        close_driver(driver)


# Recover password test


def login(driver, host, email="user1@example.com", password="1234"):
    """Helper function to login"""
    driver.get(f"{host}/login")
    wait_for_page_to_load(driver)

    email_field = driver.find_element(By.NAME, "email")
    password_field = driver.find_element(By.NAME, "password")

    email_field.send_keys(email)
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)

    time.sleep(2)


def test_password_recovery_success():

    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        driver.get(f"{host}/recover-password/")
        time.sleep(2)

        email_field = driver.find_element(By.NAME, "email")
        email_field.send_keys("user1@example.com")

        email_field.send_keys(Keys.RETURN)
        time.sleep(4)

        current_url = driver.current_url
        if not current_url.endswith("/recover-password/"):
            raise AssertionError(f"ERROR: URL unexpected: {current_url}.")

        driver.find_element(By.XPATH, "//*[contains(text(), 'sent')]")

    finally:
        close_driver(driver)


def test_password_reset_success():

    driver = initialize_driver()
    host = get_host_for_selenium_testing()
    new_password = "SecureNewPassword789"

    try:
        user = UserRepository().get_by_email("user1@example.com")
        token = AuthenticationService().generate_reset_token(user.id)

        driver.get(f"{host}/reset-password/?token={token}")
        time.sleep(3)

        current_url = driver.current_url
        if current_url.endswith("/login"):
            raise AssertionError("FALLO: El token no fue aceptado o expiró prematuramente.")

        password_field = driver.find_element(By.NAME, "password")
        confirm_password_field = driver.find_element(By.NAME, "new_password")

        password_field.send_keys(new_password)
        confirm_password_field.send_keys(new_password)

        confirm_password_field.send_keys(Keys.RETURN)
        time.sleep(4)

        assert driver.current_url.endswith("/login"), "ERROR: Did not redirect to /login after successful reset."

        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys(new_password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(4)

        assert not driver.current_url.endswith("/login"), "ERROR: Login failed with new password."

    finally:
        close_driver(driver)


def test_password_reset_fail_same_password():

    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        user = UserRepository().get_by_email("user1@example.com")
        token = AuthenticationService().generate_reset_token(user.id)

        driver.get(f"{host}/reset-password/?token={token}")
        time.sleep(3)

        password_field = driver.find_element(By.NAME, "password")
        confirm_password_field = driver.find_element(By.NAME, "new_password")

        password_field.send_keys(user.password)
        confirm_password_field.send_keys(user.password)

        confirm_password_field.send_keys(Keys.RETURN)
        time.sleep(3)

        assert not driver.current_url.endswith("/login"), "ERROR: Redirect to /login when using the same password."

        error_message = "New password can not be the same as the last one."
        driver.find_element(By.XPATH, f"//*[contains(text(), '{error_message}')]")

    except NoSuchElementException:
        raise AssertionError("ERROR: Error message was not found.")
    finally:
        close_driver(driver)
