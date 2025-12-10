import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def count_datasets(driver, host):
    driver.get(f"{host}/dataset/list")
    wait_for_page_to_load(driver)

    try:
        amount_datasets = len(driver.find_elements(By.XPATH, "//table//tbody//tr"))
    except Exception:
        amount_datasets = 0
    return amount_datasets


def test_upload_dataset_formula_csv():
    driver = initialize_driver()

    csv_path = os.path.abspath("dummy_formula.csv")
    with open(csv_path, "w") as f:
        # Cabecera estándar F1
        f.write(
            "race_id,season,date,gp_name,circuit,driver,team,engine,position,points,time,laps,grid,fastest_lap,status\n"
        )
        f.write(
            "1,2024,2024-01-01,Selenium GP,Test Circuit,Max Verstappen,Red Bull,Honda,1,25,1:30:00,50,1,1:20,Finished\n"
        )

    try:
        host = get_host_for_selenium_testing()

        # --- LOGIN ---
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234" + Keys.RETURN)

        # Esperar redirección
        WebDriverWait(driver, 5).until(EC.url_changes(f"{host}/login"))

        # --- IR A UPLOAD ---
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # 1. Rellenar Metadatos (Basado en tu HTML actual)
        driver.find_element(By.NAME, "title").send_keys("Selenium CSV Formula")
        driver.find_element(By.NAME, "desc").send_keys("Testing CSV upload with current forms")

        # 2. Publication Type
        try:
            select_elem = driver.find_element(By.NAME, "publication_type")
            Select(select_elem).select_by_value("article")
        except Exception:
            print("⚠️ No se encontró el campo 'publication_type'.")

        driver.find_element(By.NAME, "tags").send_keys("selenium, f1")

        print("📤 Iniciando subida de archivo...")

        try:
            dropzone_input = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
            dropzone_input.send_keys(csv_path)
            print("✅ Enviado a Dropzone.")
            time.sleep(2)
        except Exception:
            print("⚠️ No se encontró Dropzone.")

        try:
            file_input = driver.find_element(By.XPATH, "//input[@type='file']")
            driver.execute_script("arguments[0].style.display = 'block';", file_input)
            file_input.send_keys(csv_path)
            print("✅ Enviado al Input File del Formulario.")

            time.sleep(3)

        except Exception as e:
            print(f"❌ No se pudo enviar al input del formulario: {e}")

        # 4. ACEPTAR Y ENVIAR
        check = driver.find_element(By.ID, "agreeCheckbox")
        driver.execute_script("arguments[0].click();", check)

        submit_btn = driver.find_element(By.ID, "upload_button")

        # Esperar a que el botón se active
        WebDriverWait(driver, 2).until(lambda d: submit_btn.is_enabled())

        # Click
        driver.execute_script("arguments[0].click();", submit_btn)

        time.sleep(4)  # Esperar respuesta del servidor

        # 5. VERIFICACIÓN
        print(f"URL final: {driver.current_url}")

        if "dataset/upload" in driver.current_url:
            # Si seguimos aquí, imprimimos los errores para depurar
            errors = driver.find_elements(By.XPATH, "//*[contains(@style, 'color: red')]")
            error_texts = [e.text for e in errors if e.text]
            print(f"🚨 ERRORES EN PANTALLA: {error_texts}")
            raise AssertionError("La subida falló (El formulario no validó).")

        print("✅ Subida completada (Redirección exitosa).")

    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)
        close_driver(driver)
