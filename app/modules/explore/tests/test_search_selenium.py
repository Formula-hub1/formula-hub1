from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def login_standard_user(driver, host):
    driver.get(f"{host}/login")
    wait_for_page_to_load(driver)
    driver.find_element(By.NAME, "email").send_keys("user1@example.com")
    driver.find_element(By.NAME, "password").send_keys("1234" + Keys.RETURN)
    WebDriverWait(driver, 10).until(EC.url_changes(f"{host}/login"))


def open_advanced_filters(driver):
    btn = driver.find_element(By.ID, "advancedFilterBtn")
    WebDriverWait(driver, 2).until(EC.element_to_be_clickable(btn))
    btn.click()
    # Esperamos a que uno de los filtros sea visible (ej. author)
    WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.ID, "filter-author")))


def apply_filters(driver):
    apply_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Apply')]")
    apply_btn.click()
    # Esperamos un poco a que el DOM reaccione (si es AJAX rápido)
    driver.implicitly_wait(1)


def reset_search_page(driver, host):
    """Limpia la búsqueda recargando la página de explore."""
    driver.get(f"{host}/explore")
    wait_for_page_to_load(driver)


def assert_dataset_present(driver, title):
    """Verifica que el dataset con el título dado esté visible."""
    WebDriverWait(driver, 5).until(EC.text_to_be_present_in_element((By.ID, "results"), title))


def assert_dataset_not_present(driver, title):
    """Verifica que el dataset NO esté en los resultados."""
    results_container = driver.find_element(By.ID, "results")
    assert title not in results_container.text, f"Error: Se encontró '{title}' cuando NO debería aparecer."


def assert_no_results_found(driver):
    """Verifica si la búsqueda no arrojó resultados (opcional, según tu UI)."""
    results = driver.find_elements(By.CSS_SELECTOR, "#results .card")
    assert len(results) == 0, "Se esperaban 0 resultados, pero se encontraron datasets."


# --- TESTS SOLICITADOS ---


def test_search_function_1_tags():
    """Funcion 1: tag --> racing (valido) ; colegio (no valido)"""
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        login_standard_user(driver, host)

        # CASO 1: VÁLIDO (racing)
        reset_search_page(driver, host)
        open_advanced_filters(driver)

        # Asumiendo ID="filter-tags"
        driver.find_element(By.ID, "filter-tags-nav").send_keys("racing")
        apply_filters(driver)

        # Debe aparecer el dataset esperado (ej: Gran Premio...)
        assert_dataset_present(driver, "Gran Premio de España 2024")

        # CASO 2: NO VÁLIDO (colegio)
        reset_search_page(driver, host)
        open_advanced_filters(driver)

        driver.find_element(By.ID, "filter-tags-nav").send_keys("colegio")
        apply_filters(driver)

        # No debe encontrar nada
        assert_no_results_found(driver)

    finally:
        close_driver(driver)


def test_search_function_2_date():
    """Funcion 2: date --> 07/12/2025 (valido) ; 12/04/2023 (no valido)"""
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        login_standard_user(driver, host)

        # CASO 1: VÁLIDO (07/12/2025)
        reset_search_page(driver, host)
        open_advanced_filters(driver)

        date_input = driver.find_element(By.ID, "filter-date")
        # Inyectamos fecha en formato ISO YYYY-MM-DD para input type="date"
        driver.execute_script("arguments[0].value = '2025-12-07';", date_input)

        apply_filters(driver)
        assert_dataset_present(driver, "Gran Premio de España 2024")

        # CASO 2: NO VÁLIDO (12/04/2023)
        reset_search_page(driver, host)
        open_advanced_filters(driver)

        date_input = driver.find_element(By.ID, "filter-date")
        driver.execute_script("arguments[0].value = '2023-04-12';", date_input)

        apply_filters(driver)
        assert_no_results_found(driver)

    finally:
        close_driver(driver)


def test_search_function_3_author():
    """Funcion 3: description --> Resultados oficiales de la carrera de F1 en Barcelona. (valido) ;
    Buenas noches (no valido)"""
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        login_standard_user(driver, host)

        # CASO 1: VÁLIDO (Author 1)
        reset_search_page(driver, host)
        open_advanced_filters(driver)

        driver.find_element(By.ID, "filter-description").send_keys(
            "Resultados oficiales de la carrera de F1 en Barcelona."
        )
        apply_filters(driver)

        # Verificamos que aparezca algún resultado (o el título específico si lo sabemos)
        # Asumo que Gran Premio es de Author 1
        assert_dataset_present(driver, "Gran Premio de España 2024")

        # CASO 2: NO VÁLIDO (Author 23)
        reset_search_page(driver, host)
        open_advanced_filters(driver)

        driver.find_element(By.ID, "filter-description").send_keys("Buenas noches")
        apply_filters(driver)

        assert_no_results_found(driver)

    finally:
        close_driver(driver)


def test_search_function_4_files():
    """Funcion 4: files --> file10.uvl (valido) ; file23 (no valido)"""
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        login_standard_user(driver, host)

        # CASO 1: VÁLIDO (file1)
        reset_search_page(driver, host)
        open_advanced_filters(driver)

        # Asumiendo ID="filter-file"
        driver.find_element(By.ID, "filter-file").send_keys("file10.uvl")
        apply_filters(driver)

        assert_dataset_present(driver, "Sample dataset 4")

        # CASO 2: NO VÁLIDO (file23)
        reset_search_page(driver, host)
        open_advanced_filters(driver)

        driver.find_element(By.ID, "filter-file").send_keys("file23.uvl")
        apply_filters(driver)

        assert_no_results_found(driver)

    finally:
        close_driver(driver)


def test_search_function_5_global_search():
    """Funcion 5: Barra busqueda --> Gran Premio... (valido) ; Fibes 2025 (no valido)"""
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    try:
        login_standard_user(driver, host)

        # CASO 1: VÁLIDO
        reset_search_page(driver, host)

        # Asumiendo que la barra principal tiene ID="query"
        search_bar = driver.find_element(By.ID, "query")
        search_bar.clear()
        search_bar.send_keys("Gran Premio de España 2024")
        # Normalmente la barra busca al pulsar ENTER o tiene su propio botón
        search_bar.send_keys(Keys.RETURN)

        assert_dataset_present(driver, "Gran Premio de España 2024")

        # CASO 2: NO VÁLIDO
        reset_search_page(driver, host)

        search_bar = driver.find_element(By.ID, "query")
        search_bar.clear()
        search_bar.send_keys("Fibes 2025")
        search_bar.send_keys(Keys.RETURN)

        assert_no_results_found(driver)

    finally:
        close_driver(driver)
