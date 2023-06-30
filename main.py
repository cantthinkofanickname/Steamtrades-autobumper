import os
try:
    os.system(f"pip install --quiet -r requirements.txt")
except Exception as e:
    pass
import schedule
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from user_agent import generate_user_agent, generate_navigator
from steampy import guard
import pickle
from time import sleep
import glob
import shutil
from bs4 import BeautifulSoup as bs
from datetime import datetime
import lxml
import config



def log_in(driver, defurl):
    try:
        driver.get(defurl)
        sleep(1.5)
        driver.find_element(By.XPATH, '/html/body/header/div/nav/a').click()
        sleep(1)
        driver.find_element(By.XPATH, '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[1]/input').send_keys(f'{config.login}')
        sleep(0.4)
        driver.find_element(By.XPATH, '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[2]/input').send_keys(f'{config.passw}')
        sleep(0.4)
        driver.find_element(By.XPATH, '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[4]/button').click()
        sleep(1)
        code = guard.generate_one_time_code(f'{config.shared_secret}')
        driver.find_element(By.XPATH, '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/form/div/div[2]/div[1]/div/input[1]').send_keys(f'{code}')
        sleep(3)
        driver.find_element(By.XPATH, '//*[@id="imageLogin"]').click()
        sleep(1)
        pickle.dump(driver.get_cookies(), open('cookies.dat', 'wb'))
        return
    except Exception as e:
        return log_in(driver, defurl)


def bump(driver, link):
    try:
        driver.get(link)
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[3]/div[2]/a').click()
        sleep(1.5)
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[3]/div[2]/div/div/div[2]').click()
        sleep(1)
        return
    except Exception as e:
        return bump(driver, link)


def main():
    ua = generate_user_agent(os=('win'))
    options = Options()
    prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
    options.add_experimental_option("prefs", prefs)
    options.add_argument(f"user-agent={ua}")
    options.add_argument("--disable-infobars")
    options.add_argument('--disable-notifications')
    options.add_argument("--mute-audio")
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    defurl = 'https://www.steamtrades.com'
    driver.get(defurl)
    try:
        cookies = pickle.load(open('cookies.dat', 'rb'))
        for cookie in cookies:
            if datetime.fromtimestamp(cookie['expiry']) < datetime.now():
                log_in(driver, defurl)
            else:
                driver.add_cookie(cookie)
    except Exception as e:
        log_in(driver, defurl)

    driver.refresh()
    sleep(1)
    elem = driver.find_element(By.XPATH, "/html/body/header/div/nav/div[3]/div[5]/a")
    userid = elem.get_attribute("href")[33:]
    driver.get(f"https://www.steamtrades.com/trades/search?user={userid}")
    sleep(1)
    urls = []
    soup = bs(driver.page_source, "lxml")
    cparse = soup.findAll('h2')
    for item in cparse:
        try:
            urlstr = defurl
            urlstr += item.contents[0].attrs['href']
            urls.append(urlstr)
        except Exception as e:
            pass
    sleep(1)

    for link in urls:
        bump(driver, link)
    driver.quit()
    try:
        for f in glob.glob(R"C:\Program Files (x86)\scopeD_dir*"):
            shutil.rmtree(f)
    except Exception as e:
        print(e)


def start():
    main()

    schedule.every(3610).seconds.do(main)
    while True:
        schedule.run_pending()
        sleep(1)


if __name__ == '__main__':
    start()