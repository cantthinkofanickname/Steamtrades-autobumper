import pickle
import requests
from bs4 import BeautifulSoup as bs
import schedule
from time import sleep
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from user_agent import generate_user_agent, generate_navigator
import undetected_chromedriver as uc
from steampy import guard
import config


COOKIES_FILE = "cookies.dat"
BASE_URL = "https://www.steamtrades.com"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# безопасные запросы с таймаутом и отловом ошибок
def safe_get(session, url, timeout=50):
    try:
        return session.get(url, timeout=timeout)
    except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
        log(f"Ошибка GET {url}: {e}. Пропускаем до следующего часа.")
        return None

def safe_post(session, url, data=None, headers=None, timeout=50):
    try:
        return session.post(url, data=data, headers=headers, timeout=timeout)
    except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
        log(f"Ошибка POST {url}: {e}. Пропускаем до следующего часа.")
        return None


def selenium_login():
    log("Запускаю браузер для логина...")
    ua = generate_user_agent(os=('win'))
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-infobars")
    options.add_argument('--disable-notifications')
    options.add_argument("--mute-audio")
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = uc.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        driver.get(BASE_URL)
        sleep(1.5)
        driver.find_element(By.XPATH, '/html/body/header/div/nav/a').click()
        sleep(2)
        driver.find_element(By.XPATH,
                            '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[1]/input').send_keys(config.login)
        sleep(0.5)
        driver.find_element(By.XPATH,
                            '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[2]/input').send_keys(config.passw)
        sleep(0.5)
        driver.find_element(By.XPATH,
                            '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[4]/button').click()
        sleep(1.5)
        code = guard.generate_one_time_code(config.shared_secret)
        driver.find_element(By.XPATH,
                            '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/form/div/div[2]/div[1]/div/input[1]').send_keys(code)
        sleep(2)
        driver.find_element(By.XPATH, '//*[@id="imageLogin"]').click()
        sleep(2)

        cookies = driver.get_cookies()
        with open(COOKIES_FILE, 'wb') as f:
            pickle.dump(cookies, f)
        log(f"Куки сохранены в {COOKIES_FILE}")
    except Exception as e:
        log(f"Ошибка при логине: {e}")
    finally:
        driver.quit()


def get_trade_links(session, userid):
    r = safe_get(session, f"{BASE_URL}/trades/search?user={userid}")
    if r is None:
        return []
    soup = bs(r.text, "html.parser")
    links = []
    for h2 in soup.find_all("h2"):
        try:
            trade_url = BASE_URL + h2.contents[0]["href"]
            links.append(trade_url)
        except:
            pass
    return links


def bump_trade(session, trade_url):
    r = safe_get(session, trade_url)
    if r is None:
        return

    soup = bs(r.text, "html.parser")
    xsrf_token = soup.find("input", {"name": "xsrf_token"})["value"]
    code = trade_url.split("/trade/")[1].split("/")[0]

    data = {
        "do": "trade_bump",
        "code": code,
        "xsrf_token": xsrf_token
    }
    headers = {
        "Origin": BASE_URL,
        "Referer": trade_url,
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    resp = safe_post(session, f"{BASE_URL}/ajax.php", data=data, headers=headers, timeout=30)
    if resp is None:
        return

    log(f"[{code}] bump → {resp.status_code} {resp.text.strip()}")


def create_session_from_cookies():
    if not os.path.exists(COOKIES_FILE):
        log("Файл с куками не найден, нужно логиниться через Selenium.")
        return None

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        cookies = pickle.load(open(COOKIES_FILE, 'rb'))
        for c in cookies:
            session.cookies.set(c['name'], c['value'], domain=c.get('domain'), path=c.get('path', '/'))
        log("Новый час, апаем темки :)")
    except Exception as e:
        log(f"Ошибка при загрузке куки из файла: {e}")
        return None

    return session


def test_session(session):
    if session is None:
        return "bad_cookies"
    try:
        r = safe_get(session, BASE_URL)
        if r is None:
            return "offline"
        if r.status_code == 200:
            return "ok"
        else:
            log(f"Доступ через requests с куками не успешен. Код: {r.status_code}")
            return "bad_cookies"
    except Exception as e:
        log(f"Ошибка при проверке сессии: {e}")
        return "offline"


def main():
    session = create_session_from_cookies()
    status = test_session(session)

    if status == "offline":
        log("Сайт недоступен, пропускаем до следующего часа.")
        return

    if status == "bad_cookies":
        log("Куки невалидны, пробуем логин через Selenium...")
        selenium_login()
        session = create_session_from_cookies()
        status = test_session(session)
        if status != "ok":
            log("Не удалось получить рабочую сессию, пропускаем до следующего часа.")
            return

    # если дошли сюда — сессия рабочая
    response = safe_get(session, BASE_URL)
    if response is None:
        return

    soup = bs(response.text, "html.parser")
    userid = soup.find_all('a', class_="nav_btn nav_btn_left")[1].attrs['href'][6:]
    trades = get_trade_links(session, userid)
    for trade_url in trades:
        bump_trade(session, trade_url)


def start():
    main()
    schedule.every(3610).seconds.do(main)
    while True:
        schedule.run_pending()
        sleep(1)


if __name__ == "__main__":
    start()
