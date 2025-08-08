import os
import pickle
import requests
from bs4 import BeautifulSoup as bs
import schedule
from time import sleep
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
import undetected_chromedriver as uc
from steampy import guard
from user_agent import generate_user_agent
import config


COOKIES_FILE = "cookies.dat"
BASE_URL = "https://www.steamtrades.com"

def realtime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def selenium_login():
    log("Запускаю браузер для логина...")
    ua = generate_user_agent(os=('win'))
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-agent={ua}")
    options.add_argument("--disable-infobars")
    options.add_argument('--disable-notifications')
    options.add_argument("--mute-audio")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = uc.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        driver.get(BASE_URL)
        sleep(1.5)
        # Нажать кнопку "Login"
        driver.find_element(By.XPATH, '/html/body/header/div/nav/a').click()
        sleep(2)
        # Ввести логин
        driver.find_element(By.XPATH,
                            '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[1]/input').send_keys(config.login)
        sleep(0.5)
        # Ввести пароль
        driver.find_element(By.XPATH,
                            '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[2]/input').send_keys(config.passw)
        sleep(0.5)
        # Нажать кнопку входа
        driver.find_element(By.XPATH,
                            '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/div/form/div[4]/button').click()
        sleep(1.5)
        # Ввести код двухфакторной аутентификации
        code = guard.generate_one_time_code(config.shared_secret)
        driver.find_element(By.XPATH,
                            '//*[@id="responsive_page_template_content"]/div[1]/div[1]/div/div/div/div[2]/form/div/div[2]/div[1]/div/input[1]').send_keys(code)
        sleep(2)
        # Подтвердить логин
        driver.find_element(By.XPATH, '//*[@id="imageLogin"]').click()
        sleep(2)

        # Сохраняем куки в файл
        cookies = driver.get_cookies()
        with open(COOKIES_FILE, 'wb') as f:
            pickle.dump(cookies, f)
        log(f"Куки сохранены в {COOKIES_FILE}")
    except Exception as e:
        log(f"Ошибка при логине: {e}")
    finally:
        driver.quit()


def get_trade_links(session, user_id):
    r = session.get(f"{BASE_URL}/trades/search?user={user_id}")
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
    r = session.get(trade_url)
    soup = bs(r.text, "html.parser")

    # xsrf_token лежит в скрытом input
    xsrf_token = soup.find("input", {"name": "xsrf_token"})["value"]

    # code — это часть URL после /trade/
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
        "User-Agent": "Mozilla/5.0"
    }
    resp = session.post(f"{BASE_URL}/ajax.php", data=data, headers=headers)
    print(f"{realtime()} [{code}] bump → {resp.status_code} {resp.text.strip()}")


def create_session_from_cookies():
    if not os.path.exists(COOKIES_FILE):
        log("Файл с куками не найден, нужно логиниться через Selenium.")
        return None

    session = requests.Session()

    # Важный момент: нужен User-Agent, аналогичный браузеру
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        cookies = pickle.load(open(COOKIES_FILE, 'rb'))
        for c in cookies:
            session.cookies.set(c['name'], c['value'], domain=c.get('domain'), path=c.get('path', '/'))
        log(f"Загружено {len(cookies)} куки в requests.Session()")
    except Exception as e:
        log(f"Ошибка при загрузке куки из файла: {e}")
        return None

    return session


def test_session(session):
    if session is None:
        log("Сессия не создана.")
        return False
    try:
        r = session.get(BASE_URL, timeout=15)
        if r.status_code == 200:
            log("Успешный доступ к сайту через requests с куками.")
            return True
        else:
            log(f"Доступ через requests с куками не успешен. Код: {r.status_code}")
            return False
    except Exception as e:
        log(f"Ошибка при запросе: {e}")
        return False


def main():
    session = create_session_from_cookies()
    if session is None or not test_session(session):
        log("Будем логиниться через Selenium и получать свежие куки...")
        selenium_login()
        session = create_session_from_cookies()
        if not test_session(session):
            log("Не удалось получить рабочую сессию.")
            return
    response = session.get(BASE_URL)
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
