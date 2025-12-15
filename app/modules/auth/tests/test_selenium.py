import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from app import create_app, db
from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.dataset.tests.test_recommender_selenium import wait_for_page_to_load
from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def setup_reset_data(email: str, password: str, create_if_missing: bool = True):
    """
    Crea el application context, busca el usuario, lo crea si es necesario,
    y genera un token de reset.
    """
    # Importante: Si estás teniendo problemas con el entorno de testing,
    # usa "testing". Si el error 1146 persiste y no puedes modificar conftest,
    # el problema es la BBDD, no el código.
    app = create_app("testing")

    with app.app_context():
        user_repo = UserRepository()
        auth_service = AuthenticationService()

        # --- SOLUCIÓN DE EMERGENCIA PARA BBDD ROTA (Error 1146) ---
        try:
            db.drop_all()
            db.create_all()
            db.session.commit()
        except Exception as e:
            # En un entorno de testing normal, esto no debería ser necesario.
            print(f"DEBUG: Error al forzar creación de tablas (probablemente un bug en conftest): {e}")
        # ---------------------------------------------------------

        user = user_repo.get_by_email(email)

        if user is None and create_if_missing:
            user = auth_service.create_with_profile(name="Test", surname="User", email=email, password=password)

        if user:
            token = auth_service.generate_reset_token(user.id)
            return user, token
        else:
            raise Exception(f"Usuario {email} no encontrado ni pudo ser creado.")


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

        driver.find_element(By.XPATH, "//*[contains(text(), 'sent')]")

    finally:
        close_driver(driver)
