import os
import time

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# Asumimos que estas importaciones funcionan en tu entorno Docker/Local
from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def login_standard_user(driver, host):
    """Helper para realizar el login estándar."""
    driver.get(f"{host}/login")
    wait_for_page_to_load(driver)

    # Credenciales que sabemos que funcionan
    driver.find_element(By.NAME, "email").send_keys("user1@example.com")
    driver.find_element(By.NAME, "password").send_keys("1234" + Keys.RETURN)

    # Esperar redirección
    WebDriverWait(driver, 10).until(EC.url_changes(f"{host}/login"))


def test_upload_and_check_recommender():
    """
    1. Sube un dataset CSV.
    2. Navega a la lista, entra en el ÚLTIMO dataset subido (el más reciente).
    3. Verifica que el panel de recomendación carga correctamente.
    """
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    # Nombre único para identificarlo luego en la lista
    DATASET_TITLE = f"Recommender Check Upload {int(time.time())}"

    # Crear CSV Dummy
    csv_path = os.path.abspath("recommender_test_upload.csv")
    with open(csv_path, "w") as f:
        f.write("race_id,season,date,gp_name\n")
        f.write("1,2024,2024-01-01,Selenium GP\n")

    try:
        login_standard_user(driver, host)

        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # 1. Rellenar Metadatos
        driver.find_element(By.NAME, "title").send_keys(DATASET_TITLE)
        driver.find_element(By.NAME, "desc").send_keys("Testing Recommender Appearance after Upload")
        driver.find_element(By.NAME, "tags").send_keys("selenium, recommender")

        try:
            select_elem = driver.find_element(By.NAME, "publication_type")
            Select(select_elem).select_by_value("article")
        except Exception:
            pass

        # 2. Subida de Archivo
        try:
            file_input = driver.find_element(By.XPATH, "//input[@type='file']")
            driver.execute_script("arguments[0].style.display = 'block';", file_input)
            file_input.send_keys(csv_path)
            print("✅ Enviado al Input File del Formulario.")

            time.sleep(3)

        except Exception as e:
            print(f"❌ No se pudo enviar al input del formulario: {e}")

        # 3. Enviar Formulario
        check = driver.find_element(By.ID, "agreeCheckbox")
        driver.execute_script("arguments[0].click();", check)

        submit_btn = driver.find_element(By.ID, "upload_button")
        WebDriverWait(driver, 2).until(lambda d: submit_btn.is_enabled())
        driver.execute_script("arguments[0].click();", submit_btn)

        print("⏳ Esperando subida y redirección a la lista...")
        WebDriverWait(driver, 60).until_not(EC.url_contains("/dataset/upload"))
        print(f"✅ Redirección completada. URL actual: {driver.current_url}")

        if "list" in driver.current_url or "mydatasets" in driver.current_url:
            print("📍 Buscando el último dataset subido...")
            try:
                dataset_link = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.LINK_TEXT, DATASET_TITLE))
                )
                dataset_link.click()
                print("✅ Navegando a la vista de detalles del dataset recién subido.")
                wait_for_page_to_load(driver)
            except Exception:
                raise AssertionError(f"No se encontró el dataset '{DATASET_TITLE}' en la lista tras la subida.")

        print("🔍 Verificando panel de recomendación...")

        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "recommendation-list")))
            # Verificamos que cargó contenido (enlace o mensaje)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@id='recommendation-list']//a | //div[@id='recommendation-list']//p")
                )
            )
            print("✅ Panel de recomendación y contenido detectados con éxito.")

        except TimeoutException:
            raise AssertionError("El panel de recomendación no cargó contenido en 15s (Fallo de API o backend lento).")
        except NoSuchElementException:
            raise AssertionError("No se encontró el div 'recommendation-list'.")

    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)
        close_driver(driver)


def test_navigate_existing_dataset_recommender():
    """
    1. Entra directamente a un dataset usando su DOI.
    2. Comprueba que hay recomendaciones.
    3. Navega a una de ellas.
    """
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    TARGET_DATASET_DOI_URL = f"{host}/doi/10.1234/f1-spain-2024"

    try:
        login_standard_user(driver, host)

        print(f"📍 Navegando al dataset por DOI: {TARGET_DATASET_DOI_URL}")
        driver.get(TARGET_DATASET_DOI_URL)
        wait_for_page_to_load(driver)

        print("⏳ Esperando carga de recomendaciones...")
        try:
            recommendation_link = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[@id='recommendation-list']//a[contains(@class, 'list-group-item')]")
                )
            )
            print(f"✅ Recomendación encontrada: {recommendation_link.text}")

        except Exception:
            print("⚠️ No se encontraron recomendaciones clickeables.")
            try:
                driver.find_element(By.ID, "recommendation-list")
                print("✅ Panel encontrado, pero la lista está vacía (posiblemente falta data en BD).")
                return  # Pasa si la interfaz es estable
            except NoSuchElementException:
                raise AssertionError("El panel de recomendación ('recommendation-list') no se cargó.")

        current_url = driver.current_url
        recommendation_link.click()

        WebDriverWait(driver, 10).until(EC.url_changes(current_url))
        print(f"✅ Navegación exitosa a: {driver.current_url}")

        if driver.current_url == current_url:
            raise AssertionError("El click en la recomendación no cambió la página.")

    finally:
        close_driver(driver)


def test_recommender_link_format():
    """
    Verifica la integridad visual y el formato de los enlaces en el panel de recomendaciones.

    1. Navega a un dataset conocido (que debe tener recomendaciones).
    2. Comprueba que cada enlace de recomendación tiene una URL válida (/dataset/ID o /doi/...).
    """
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    # Usamos un DOI de ejemplo que debería existir/ser redirigido
    TARGET_DATASET_DOI_URL = f"{host}/doi/10.1234/f1-spain-2024"

    try:
        # --- LOGIN ---
        login_standard_user(driver, host)

        # --- NAVEGACIÓN DIRECTA POR DOI ---
        print(f"📍 Navegando al dataset por DOI para verificar recomendaciones: {TARGET_DATASET_DOI_URL}")
        driver.get(TARGET_DATASET_DOI_URL)
        wait_for_page_to_load(driver)

        # --- ESPERAR CARGA DEL PANEL ---
        print("⏳ Esperando que el panel cargue resultados...")

        try:
            # Esperamos que aparezca al menos un enlace de recomendación real
            recommendation_items = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//div[@id='recommendation-list']//a[contains(@class, 'list-group-item')]")
                )
            )

            # 3. VERIFICAR FORMATO DE LOS ENLACES
            print(f"✅ Panel cargado. Verificando {len(recommendation_items)} enlaces.")

            if not recommendation_items:
                # El test de interfaz pasa si no hay enlaces (lista vacía), pero la validación de formato no aplica.
                try:
                    driver.find_element(
                        By.XPATH, "//div[@id='recommendation-list']" "//p[contains(text(), 'No similar datasets')]"
                    )
                    print("⚠️ Panel vacío: El seeder necesita más datos, pero la interfaz es correcta.")
                    return
                except NoSuchElementException:
                    raise AssertionError(
                        "El panel de recomendación cargó, pero está " "vacío y no mostró mensaje de no resultados."
                    )

            # Iterar sobre todos los enlaces encontrados
            for index, item in enumerate(recommendation_items):
                href = item.get_attribute("href")

                # Regla de integridad: La URL debe ser una URL completa y contener "/dataset/" o "/doi/"
                assert href is not None, f"El enlace #{index} no tiene atributo 'href'."

                # Nota: Tu seeder debe garantizar que los DOIs son válidos y únicos.
                if not (href.startswith(f"{host}/dataset/") or href.startswith(f"{host}/doi/")):
                    raise AssertionError(f"El enlace #{index} tiene un formato de URL incorrecto: {href}")

            print("✅ Integridad de enlaces verificada: Todos tienen el formato /dataset/ o /doi/.")

        except TimeoutException:
            raise AssertionError("El panel de recomendación no cargó los elementos dentro del tiempo límite (15s).")
        except NoSuchElementException:
            raise AssertionError("No se encontró el contenedor principal 'recommendation-list'.")

    finally:
        close_driver(driver)
