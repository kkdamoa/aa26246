import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains  # 추가된 import
from selenium.webdriver.common.keys import Keys  # 추가된 import
import time
import json
import requests
from bs4 import BeautifulSoup

def setup_driver():
    try:
        print("\n=== Chrome 드라이버 설정 시작 ===")
        options = Options()
        
        # chrome_profile 경로 설정
        script_dir = os.path.dirname(os.path.abspath(__file__))
        profile_path = os.path.join(script_dir, 'chrome_profile')
        
        # chrome_profile 폴더가 없으면 오류 발생
        if not os.path.exists(profile_path):
            raise Exception("chrome_profile 폴더가 필요합니다. 로그인된 프로필을 먼저 준비해주세요.")
        
        print(f"[1/4] Chrome 프로필 경로: {profile_path}")
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument('--profile-directory=Default')
        
        # 기본 옵션 설정
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--window-size=1920,1080')
        
        print("[2/4] Chrome 드라이버 초기화 중...")
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        
        print("[3/4] 밴드 페이지 로딩 테스트...")
        driver.get('https://band.us/home')  # /home으로 변경
        time.sleep(5)
        
        print(f"[4/4] 현재 URL: {driver.current_url}")
        # 로그인 상태 확인
        if not driver.current_url.startswith('https://band.us/home'):
            raise Exception("로그인되지 않은 상태입니다. chrome_profile에 로그인 정보가 저장되어 있는지 확인해주세요.")
        
        print("✓ 프로필 로드 및 로그인 확인 성공!")
        return driver

    except Exception as e:
        print(f"\n[오류] Chrome 드라이버 설정 실패: {str(e)}")
        raise

def get_url_content(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # meta 태그에서 description 추출
        description = soup.find('meta', {'name': 'description'})
        if (description):
            return description.get('content', '')
        
        # 본문 텍스트 추출
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text() for p in paragraphs])
        return content.strip()
        
    except Exception as e:
        print(f"URL 내용 가져오기 실패: {str(e)}")
        return url

def post_to_band(driver, config, band_info, step=1):
    try:
        print(f"\n=== [{step}단계] 밴드 '{band_info['name']}' 포스팅 시작 ===")
        
        print(f"[{step}.1] 밴드 페이지로 이동: {band_info['url']}")
        driver.get(band_info['url'])
        time.sleep(5)
        print(f"[{step}.1] ✓ 현재 URL: {driver.current_url}")
        
        print(f"[단계 {step}] 밴드 '{band_info['name']}' 포스팅 시작")
        # 밴드로 이동
        driver.get(band_info['url'])
        print(f"[단계 {step}.1] 밴드 페이지 로딩 중...")
        time.sleep(5)
        
        print(f"[단계 {step}.2] 글쓰기 버튼 찾는 중...")
        write_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button._btnPostWrite'))
        )
        print(f"[단계 {step}.3] 글쓰기 버튼 클릭")
        driver.execute_script("arguments[0].click();", write_btn)
        time.sleep(2)
        
        print(f"[단계 {step}.4] 에디터 로딩 대기 중...")
        editor = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"]'))
        )
        
        print(f"[단계 {step}.5] URL 콘텐츠 가져오는 중...")
        post_url = config['post_url']
        content = get_url_content(post_url)
        
        print(f"[단계 {step}.6] 제목 입력 중...")
        title = config['title']
        if (title):
            editor.send_keys(title)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(1)
        
        print(f"[단계 {step}.7] URL 입력 중...")
        editor.click()
        editor.clear()
        editor.send_keys(post_url)
        time.sleep(1)
        
        print(f"[단계 {step}.8] 미리보기 로딩 대기 중...")
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(7)
        
        print(f"[단계 {step}.9] URL 텍스트 정리 중...")
        editor.click()
        driver.execute_script("""
            var editor = arguments[0];
            var url = arguments[1];
            editor.innerHTML = editor.innerHTML.replace(url, '');
            editor.innerHTML = editor.innerHTML.replace(/^\\n|\\n$/g, '');
            editor.innerHTML = editor.innerHTML.trim();
            editor.dispatchEvent(new Event('input', { bubbles: true }));
        """, editor, post_url)
        
        print(f"[단계 {step}.10] 게시 버튼 클릭...")
        submit_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.uButton.-sizeM._btnSubmitPost.-confirm'))
        )
        time.sleep(3)
        submit_btn.click()
        print(f"[단계 {step}.11] 게시 완료 대기 중...")
        time.sleep(3)
        
        print(f"[단계 {step}] 포스팅 완료!")
        return True
        
    except Exception as e:
        print(f"[단계 {step}] 포스팅 실패: {str(e)}")
        return False

def normal_posting_process(driver, config):
    """일반적인 포스팅 프로세스"""
    try:
        print("\n[단계 1] 밴드 목록 페이지로 이동 중...")
        driver.get('https://band.us/feed')
        time.sleep(3)

        print("[단계 2] 밴드 목록 로딩 중...")
        # "내 밴드 더보기" 버튼을 찾아서 클릭
        try:
            more_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button.myBandMoreView._btnMore'))
            )
            print("'내 밴드 더보기' 버튼 발견")
            driver.execute_script("arguments[0].click();", more_btn)
            time.sleep(2)  # 밴드 목록이 로드될 때까지 대기
        except Exception as e:
            print("'내 밴드 더보기' 버튼을 찾을 수 없거나 이미 모든 밴드가 표시되어 있습니다.")
        
        band_list = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[data-viewname="DMyGroupBandBannerView.MyGroupBandListView"]'))
        )
        
        # 모든 밴드 항목 찾기
        band_items = band_list.find_elements(By.CSS_SELECTOR, 'li[data-viewname="DMyGroupBandListItemView"]')
        band_elements = []
        
        for item in band_items:
            try:
                band_link = item.find_element(By.CSS_SELECTOR, 'a.itemMyBand')
                band_name = item.find_element(By.CSS_SELECTOR, 'span.body strong.ellipsis').text.strip()
                band_url = band_link.get_attribute('href')
                
                if (band_url and band_name):
                    band_elements.append({
                        'name': band_name,
                        'url': band_url
                    })
                    print(f"밴드 발견: {band_name} ({band_url})")
            except Exception as e:
                continue
        
        # URL 기준으로 내림차순 정렬 (높은 숫자가 먼저 오도록)
        band_elements.sort(key=lambda x: int(x['url'].split('/')[-1]), reverse=True)
        
        total = len(band_elements)
        print(f"[단계 4] 총 {total}개의 밴드 발견")
        if (total > 0):
            print(f"첫 번째 밴드: {band_elements[0]['name']} ({band_elements[0]['url']})")
            print(f"마지막 밴드: {band_elements[-1]['name']} ({band_elements[-1]['url']})")
        else:
            print("밴드를 찾을 수 없습니다.")
            return 1

        # 각 밴드에 글 작성
        success_count = 0
        for idx, band_info in enumerate(band_elements, 1):
            print(f"\n=== 밴드 {idx}/{len(band_elements)} 처리 중 ===")
            if post_to_band(driver, config, band_info, step=idx+4):
                success_count += 1
            time.sleep(10)  # 각 밴드 간 대기 시간
        
        print(f"\n[최종 단계] 작업 완료 (성공: {success_count}, 실패: {total - success_count})")
        return 0
        
    except Exception as e:
        print(f"\n[오류] 프로세스 실패: {str(e)}")
        return 1

def main():
    print("\n=== 밴드 자동 포스팅 시작 ===")
    try:
        # 설정 로드
        print("[1/3] 설정 파일 로드 중...")
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Chrome 드라이버 설정
        print("\n[2/3] Chrome 드라이버 설정 중...")
        driver = setup_driver()
        
        # 포스팅 프로세스 시작
        print("\n[3/3] 포스팅 프로세스 시작...")
        try:
            return normal_posting_process(driver, config)
        finally:
            print("\n브라우저 종료")
            driver.quit()
            
    except Exception as e:
        print(f"\n치명적 오류: {str(e)}")
        return 1

if __name__ == "__main__":
    print("===== 밴드 자동 포스팅 시작 =====")
    sys.exit(main())