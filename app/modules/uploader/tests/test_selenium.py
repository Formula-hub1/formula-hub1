import time
import unittest

from selenium.webdriver.common.by import By

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver

REPO_ZIP_URL = "https://github.com/Universal-Variability-Language/uvl-parser/"


class TestUploader(unittest.TestCase):

    def setUp(self):
        self.driver = initialize_driver()

        self.driver.implicitly_wait(10)

        self.base_url = get_host_for_selenium_testing()

        self.driver.get(self.base_url)

    def tearDown(self):
        close_driver(self.driver)

    def test_uploader(self):
        self.driver.get(self.base_url + "/")

        self.driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
        self.driver.find_element(By.ID, "email").send_keys("user1@example.com")
        self.driver.find_element(By.ID, "password").send_keys("1234")
        self.driver.find_element(By.ID, "submit").click()

        time.sleep(1)

        self.driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(7) .align-middle:nth-child(2)").click()
        time.sleep(1)

        url_input = self.driver.find_element(By.NAME, "url")
        url_input.send_keys(REPO_ZIP_URL)

        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'].btn-primary").click()
        time.sleep(1)

        desc_area = self.driver.find_element(By.NAME, "dataset_description")
        desc_area.send_keys("1234a")

        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'].btn-primary").click()
        time.sleep(1)

        self.driver.find_element(By.LINK_TEXT, "My datasets").click()
        time.sleep(1)


if __name__ == "__main__":
    unittest.main()
