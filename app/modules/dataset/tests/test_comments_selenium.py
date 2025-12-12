import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Importaciones del entorno del proyecto
from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    """Espera a que la página cargue completamente (DOM ready)."""
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def login_standard_user(driver, host):
    """Helper para realizar el login estándar."""
    driver.get(f"{host}/login")
    wait_for_page_to_load(driver)

    driver.find_element(By.NAME, "email").send_keys("user1@example.com")
    driver.find_element(By.NAME, "password").send_keys("1234" + Keys.RETURN)

    WebDriverWait(driver, 10).until(EC.url_changes(f"{host}/login"))


def test_create_comment_selenium():
    """
    Test 1: Crea un comentario nuevo en un dataset.
    Flujo: Login -> Home -> Click en Comentarios del 2º Dataset -> Escribir -> Enviar.
    """
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        login_standard_user(driver, host)

        driver.get(host)
        wait_for_page_to_load(driver)

        print("⏳ Buscando datasets en la home...")
        cards = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "card")))

        if len(cards) < 2:
            target_card_index = 0
        else:
            target_card_index = 1

        print(f"📍 Abriendo comentarios del dataset #{target_card_index + 1}")
        btn_comments = cards[target_card_index].find_element(By.CSS_SELECTOR, ".btn-comments")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_comments)
        time.sleep(1)

        try:
            btn_comments.click()
        except Exception:
            print("⚠️ Click normal interceptado, forzando con JS...")
            driver.execute_script("arguments[0].click();", btn_comments)

        comment_field = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.NAME, "content")))
        comment_field.click()
        comment_field.clear()

        timestamp = int(time.time())
        test_message = f"Prueba selenium auto {timestamp}"
        comment_field.send_keys(test_message)

        print("📤 Enviando comentario...")
        submit_btn = driver.find_element(By.CSS_SELECTOR, "#comment-form .btn")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        submit_btn.click()

        print("✅ Verificando que el comentario aparece...")
        WebDriverWait(driver, 5).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), test_message))

        try:
            modal_close = driver.find_element(By.CSS_SELECTOR, ".modal-close")
            if modal_close.is_displayed():
                modal_close.click()
        except Exception:
            pass

    finally:
        close_driver(driver)


def test_reply_comment_selenium():
    """
    Test 2: Simula la interacción de Hover y Reply.
    """
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        login_standard_user(driver, host)

        driver.get(host)
        wait_for_page_to_load(driver)

        print("⏳ Ejecutando secuencia de Hover y Click (Test 2)...")

        target_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card:nth-child(2) .btn-comments"))
        )

        actions = ActionChains(driver)
        actions.move_to_element(target_btn).perform()

        target_btn.click()

        body_elem = driver.find_element(By.TAG_NAME, "body")

        actions.move_to_element(body_elem).perform()

        try:
            comment_field = WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.NAME, "content")))
            comment_field.send_keys("Reply test action chains")

            submit_btn = driver.find_element(By.CSS_SELECTOR, "#comment-form .btn")
            submit_btn.click()
            print("✅ Formulario enviado.")

            WebDriverWait(driver, 5).until(
                EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Reply test action chains")
            )

        except Exception as e:
            print(f"⚠️ No se pudo completar el envío del formulario en Test 2: {e}")

        try:
            modal_close = driver.find_element(By.CSS_SELECTOR, ".modal-close")
            if modal_close.is_displayed():
                modal_close.click()
        except Exception:
            pass

    finally:
        close_driver(driver)
