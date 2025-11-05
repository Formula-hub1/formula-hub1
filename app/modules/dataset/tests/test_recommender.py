import re
import os
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=5):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def count_datasets(driver, host):
    driver.get(f"{host}/dataset/list")
    wait_for_page_to_load(driver)
    
    DOI_LINK_LOCATOR = (By.XPATH, "//a[contains(@href, '/doi/')]")
    
    try:
        WebDriverWait(driver, 10).until(
             EC.presence_of_element_located(DOI_LINK_LOCATOR)
        )
        amount_datasets = len(driver.find_elements(*DOI_LINK_LOCATOR))
    except Exception:
        amount_datasets = 0
        
    return amount_datasets

def get_last_dataset_id(driver, host):
    driver.get(f"{host}/dataset/list")
    wait_for_page_to_load(driver)
    
    DOI_LINK_LOCATOR = (By.XPATH, "(//a[contains(@href, '/doi/')])[1]") # Busca el primer enlace DOI

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(DOI_LINK_LOCATOR)
        )
        
        last_dataset_link = driver.find_element(*DOI_LINK_LOCATOR)
        href = last_dataset_link.get_attribute("href")

        match = re.search(r'dataset(\d+)/?$', href)
        
        if match:
            return int(match.group(1))
        
        match = re.search(r'dataset(\d+)', href)
        if match:
             return int(match.group(1))

        return None
        
    except Exception as e:
        print(f"ERROR: Fallo al extraer el ID del enlace. {e}")
        return None

def test_recommendation_trigger_and_api():
    """
    Sube un Dataset y comprueba que la API de recomendaciones
    responde correctamente, validando que el algoritmo se ejecutó en el backend.
    """
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()
        
        driver.get(f"{host}/login")
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234" + Keys.RETURN)
        time.sleep(3)

        driver.get(f"{host}/dataset/upload")
        driver.find_element(By.NAME, "title").send_keys(f"Test Reco Simple {time.time()}")
        driver.find_element(By.NAME, "desc").send_keys("Test desc")
        driver.find_element(By.NAME, "tags").send_keys("test, reco")
        
        file_path = os.path.abspath("app/modules/dataset/uvl_examples/file1.uvl")
        driver.find_element(By.CLASS_NAME, "dz-hidden-input").send_keys(file_path)
        time.sleep(2)

        driver.find_element(By.ID, "agreeCheckbox").click()
        driver.find_element(By.ID, "upload_button").click()
        time.sleep(5) 

        assert driver.current_url == f"{host}/dataset/list", "Fallo: No se redirigió a la lista."
        new_dataset_id = get_last_dataset_id(driver, host)
        assert new_dataset_id is not None, "Fallo: No se pudo obtener el ID del dataset."
        
        api_url = f"{host}/datasets/{new_dataset_id}/recommendations"
        response = requests.get(api_url)
        
        assert response.status_code == 200, f"Fallo: API {api_url} devolvió {response.status_code}"
        data = response.json()
        assert 'recommended_ids' in data, "Fallo: La respuesta API no tiene la clave 'recommended_ids'."

        print(f"Test Aprobado: Dataset {new_dataset_id} subido y el algoritmo de recomendación se ejecutó con éxito.")

    finally:
        close_driver(driver)


test_recommendation_trigger_and_api()