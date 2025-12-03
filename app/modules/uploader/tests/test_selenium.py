import os
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

TEST_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files", "test1.zip")

REPO_ZIP_URL = "https://github.com/Universal-Variability-Language/uvl-parser/" "archive/refs/heads/main.zip"


class TestUploader(unittest.TestCase):

    def setUp(self):
        self.driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
        self.driver.implicitly_wait(10)
        self.base_url = "http://localhost:5000"
        self.driver.get(self.base_url)

    def tearDown(self):
        self.driver.quit()

    def test_uploader(self):
        self.driver.get(self.base_url + "/")

        self.driver.set_window_size(1936, 1048)

        self.driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
        self.driver.find_element(By.ID, "email").send_keys("user1@example.com")
        self.driver.find_element(By.ID, "password").send_keys("1234")
        self.driver.find_element(By.ID, "submit").click()

        time.sleep(1)

        self.driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(7) .align-middle:nth-child(2)").click()
        time.sleep(1)

        file_input = self.driver.find_element(By.NAME, "file")

        print(f"Attempting to upload file from: {TEST_FILE_PATH}")
        file_input.send_keys(TEST_FILE_PATH)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        time.sleep(1)

        self.driver.find_element(By.CSS_SELECTOR, ".btn-primary").click()
        time.sleep(1)

        desc_area = self.driver.find_element(By.NAME, "dataset_description")
        desc_area.send_keys("1234")

        self.driver.find_element(By.CSS_SELECTOR, ".btn-primary").click()
        time.sleep(1)

        self.driver.find_element(By.LINK_TEXT, "Upload files").click()
        time.sleep(1)

        url_input = self.driver.find_element(By.NAME, "url")
        url_input.send_keys(REPO_ZIP_URL)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        time.sleep(1)

        desc_area = self.driver.find_element(By.NAME, "dataset_description")
        desc_area.send_keys("1234a")

        self.driver.find_element(By.CSS_SELECTOR, ".btn-primary").click()
        time.sleep(1)

        self.driver.find_element(By.LINK_TEXT, "My datasets").click()
        time.sleep(1)

        self.driver.find_element(By.LINK_TEXT, REPO_ZIP_URL).click()
        time.sleep(1)

        self.driver.find_element(By.CSS_SELECTOR, ".list-group-item:nth-child(2) .col-12 > .btn").click()


if __name__ == "__main__":
    unittest.main()
