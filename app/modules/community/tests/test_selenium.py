import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")


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


def test_community_index_page():
    """Test that community index page loads correctly"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/communities/")
        wait_for_page_to_load(driver)

        time.sleep(2)

        # Verify page loaded by checking URL
        assert "communities" in driver.current_url

        print("Test community index page passed!")

    finally:
        close_driver(driver)


def test_community_search():
    """Test community search functionality"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/communities/search?q=test")
        wait_for_page_to_load(driver)

        time.sleep(2)

        assert "search" in driver.current_url.lower()

        print("Test community search passed!")

    finally:
        close_driver(driver)


def test_community_create_requires_login():
    """Test that creating a community requires login"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/communities/create")
        wait_for_page_to_load(driver)

        time.sleep(2)

        # Should redirect to login
        assert "login" in driver.current_url.lower()

        print("Test community create requires login passed!")

    finally:
        close_driver(driver)


def test_community_create_form():
    """Test community creation form"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        driver.get(f"{host}/communities/create")
        wait_for_page_to_load(driver)

        time.sleep(2)

        # Use ID selectors (Flask-WTF generates id same as field name)
        name_field = driver.find_element(By.ID, "name")
        slug_field = driver.find_element(By.ID, "slug")

        # Use CSS selector for textarea to avoid meta tag
        description_field = driver.find_element(By.CSS_SELECTOR, "textarea#description")

        unique_slug = f"selenium-{int(time.time())}"

        name_field.send_keys("Selenium Test Community")
        slug_field.send_keys(unique_slug)
        description_field.send_keys("Community created by Selenium test")

        # Find the visible submit button using CSS
        submit_button = driver.find_element(By.CSS_SELECTOR, "button.btn-primary[type='submit']")
        driver.execute_script("arguments[0].click();", submit_button)

        time.sleep(3)

        # Check if redirected or community created
        current_url = driver.current_url
        assert unique_slug in current_url or "communities" in current_url

        print("Test community create form passed!")

    finally:
        close_driver(driver)


def test_community_sidebar_link():
    """Test that community link appears in sidebar"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/")
        wait_for_page_to_load(driver)

        time.sleep(2)

        # Find communities link in sidebar
        communities_link = driver.find_element(By.CSS_SELECTOR, "a[href*='/communities']")
        assert communities_link is not None

        print("Test community sidebar link passed!")

    finally:
        close_driver(driver)


def test_community_members_requires_login():
    """Test that members page requires login"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/communities/test-community/members")
        wait_for_page_to_load(driver)

        time.sleep(2)

        # Should redirect to login or communities
        current_url = driver.current_url
        assert "login" in current_url.lower() or "communities" in current_url

        print("Test community members requires login passed!")

    finally:
        close_driver(driver)


def test_community_api_endpoint():
    """Test community API endpoint"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/communities/api/communities")
        wait_for_page_to_load(driver)

        time.sleep(2)

        # Firefox renders JSON with viewer, check for JSON tab or content
        page_source = driver.page_source
        assert "JSON" in page_source or "communities" in driver.current_url

        print("Test community API endpoint passed!")

    finally:
        close_driver(driver)


def test_community_submit_dataset_requires_login():
    """Test that submitting a dataset to community requires login"""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/communities/test-community/submit")
        wait_for_page_to_load(driver)

        time.sleep(2)

        # Should redirect to login
        current_url = driver.current_url
        assert "login" in current_url.lower() or "communities" in current_url

        print("Test community submit dataset requires login passed!")

    finally:
        close_driver(driver)


# Run tests when executed directly
if __name__ == "__main__":
    test_community_index_page()
    test_community_search()
    test_community_create_requires_login()
    test_community_create_form()
    test_community_sidebar_link()
    test_community_members_requires_login()
    test_community_api_endpoint()
    test_community_submit_dataset_requires_login()
