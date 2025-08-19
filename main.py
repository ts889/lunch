import requests
import os
import json
from datetime import datetime

# .env 파일 로드를 위한 dotenv 추가
try:
    from dotenv import load_dotenv
    load_dotenv()  # .env 파일 로드
    print("✅ .env 파일 로드 완료")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않았습니다. pip install python-dotenv로 설치하세요.")
    print("⚠️ 환경변수를 직접 설정하거나 GitHub Actions에서 실행하세요.")

# --- 설정 파일 로드 ---
def load_config():
    """환경 변수에서 API 키와 Telegram Bot Token, Chat ID를 로드합니다."""
    neis_api_key = os.getenv("NEIS_API_KEY")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    print(f"환경 변수 확인:")
    print(f"NEIS_API_KEY: {'설정됨' if neis_api_key else '설정되지 않음'}")
    print(f"TELEGRAM_BOT_TOKEN: {'설정됨' if telegram_bot_token else '설정되지 않음'}")
    print(f"TELEGRAM_CHAT_ID: {'설정됨' if telegram_chat_id else '설정되지 않음'}")

    if not neis_api_key:
        print("에러: NEIS_API_KEY 환경 변수를 찾을 수 없습니다.")
    if not telegram_bot_token:
        print("에러: TELEGRAM_BOT_TOKEN 환경 변수를 찾을 수 없습니다.")
    if not telegram_chat_id:
        print("에러: TELEGRAM_CHAT_ID 환경 변수를 찾을 수 없습니다.")

    return neis_api_key, telegram_bot_token, telegram_chat_id

# NEIS API 기본 정보
API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
ATPT_OFCDC_SC_CODE = "B10"  # 서울특별시교육청
SD_SCHUL_CODE = "7010537"  # 송곡관광고등학교 (급식 정보 확인된 코드)

def get_api_data(api_key, meal_date):
    """NEIS API를 호출하여 급식 정보를 가져옵니다."""
    params = {
        'KEY': api_key,
        'Type': 'json',
        'pIndex': 1,
        'pSize': 100,
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE,
        'SD_SCHUL_CODE': SD_SCHUL_CODE,
        'MLSV_YMD': meal_date
    }
    try:
        print(f"🔍 API 요청 시작...")
        print(f"📅 요청 날짜: {meal_date}")
        print(f"🏫 학교 코드: {SD_SCHUL_CODE}")
        print(f"📋 API 요청 파라미터: {params}")
        
        response = requests.get(API_URL, params=params, timeout=10)
        
        print(f"📡 HTTP 상태 코드: {response.status_code}")
        print(f"📡 HTTP 헤더: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"❌ HTTP 오류: {response.status_code}")
            print(f"❌ 응답 내용: {response.text}")
            return None
            
        response.raise_for_status() # Raise an exception for HTTP errors
        
        print(f"✅ API 응답 성공!")
        print(f"📄 응답 길이: {len(response.text)} 문자")
        
        # JSON 파싱 시도
        try:
            json_data = response.json()
            print(f"✅ JSON 파싱 성공")
            print(f"📊 응답 데이터 타입: {type(json_data)}")
            return json_data
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 실패: {e}")
            print(f"📄 원본 응답 내용:")
            print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API 요청 중 에러 발생: {e}")
        print(f"❌ 에러 타입: {type(e)}")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        print(f"❌ 에러 타입: {type(e)}")
        return None

def format_meal_data(data):
    """API 응답 데이터를 Telegram 메시지 형식으로 가공합니다."""
    try:
        print("=== API 응답 데이터 구조 분석 ===")
        print(f"응답 키들: {list(data.keys())}")
        
        # mealServiceDietInfo가 있는지 확인
        if 'mealServiceDietInfo' not in data:
            print("❌ mealServiceDietInfo 키가 없습니다.")
            if 'RESULT' in data:
                result_code = data['RESULT'].get('CODE', '알 수 없음')
                result_msg = data['RESULT'].get('MESSAGE', '알 수 없음')
                print(f"API 결과: {result_code} - {result_msg}")
                if result_code == 'INFO-200':
                    return "오늘은 급식 정보가 없습니다."
                else:
                    return f"API 오류: {result_code} - {result_msg}"
            return "급식 정보를 찾을 수 없습니다."
        
        meal_info = data['mealServiceDietInfo']
        print(f"mealServiceDietInfo 타입: {type(meal_info)}")
        print(f"mealServiceDietInfo 내용: {meal_info}")
        
        # meal_info가 리스트인 경우와 딕셔너리인 경우를 모두 처리
        if isinstance(meal_info, list):
            if len(meal_info) < 2:
                print("❌ mealServiceDietInfo 리스트가 너무 짧습니다.")
                return "급식 정보 구조가 올바르지 않습니다."
            
            # 두 번째 요소에 row가 있는지 확인
            if 'row' not in meal_info[1]:
                print("❌ row 키를 찾을 수 없습니다.")
                return "급식 정보를 찾을 수 없습니다."
            
            rows = meal_info[1]['row']
        elif isinstance(meal_info, dict):
            if 'row' not in meal_info:
                print("❌ row 키를 찾을 수 없습니다.")
                return "급식 정보를 찾을 수 없습니다."
            rows = meal_info['row']
        else:
            print(f"❌ 예상치 못한 mealServiceDietInfo 타입: {type(meal_info)}")
            return "급식 정보 구조가 올바르지 않습니다."
        
        print(f"급식 행 수: {len(rows) if isinstance(rows, list) else '단일 행'}")
        
        # rows가 리스트가 아닌 경우 리스트로 변환
        if not isinstance(rows, list):
            rows = [rows]
        
        # 중식 정보 찾기
        lunch_menu = None
        for row in rows:
            print(f"급식 타입: {row.get('MMEAL_SC_NM', '알 수 없음')}")
            if row.get('MMEAL_SC_NM') == '중식':
                lunch_menu = row
                break
        
        if not lunch_menu:
            print("❌ 중식 정보를 찾을 수 없습니다.")
            available_meals = [row.get('MMEAL_SC_NM', '알 수 없음') for row in rows]
            print(f"사용 가능한 급식: {available_meals}")
            return "오늘은 중식 정보가 없습니다."

        print("✅ 중식 정보를 찾았습니다!")
        
        # 메뉴, 칼로리, 영양 정보 추출 및 가공
        dish = lunch_menu.get('DDISH_NM', '메뉴 정보 없음').replace('<br/>', '\n')
        cal_info = lunch_menu.get('CAL_INFO', '정보 없음')
        ntr_info = lunch_menu.get('NTR_INFO', '정보 없음').replace('<br/>', '\n')

        # Telegram에서 안전하게 표시할 수 있는 메시지 형식
        message = (
            f"🏫 송곡관광고등학교 오늘의 중식 🏫\n\n"
            f"🍽️ 메뉴:\n{dish}\n\n"
            f"🍚 칼로리: {cal_info}\n\n"
            f"🥗 영양정보:\n{ntr_info}"
        )
        
        print("✅ 메시지 가공 완료")
        return message

    except (KeyError, TypeError, IndexError) as e:
        print(f"❌ 데이터 파싱 중 오류 발생: {e}")
        print(f"오류 타입: {type(e)}")
        
        # 데이터가 없는 경우 (INFO-200)
        if data.get('RESULT', {}).get('CODE') == 'INFO-200':
            return "오늘은 급식 정보가 없습니다."
        
        # 더 자세한 디버깅 정보 제공
        return f"급식 정보를 파싱하는 중 오류가 발생했습니다. (오류: {str(e)})"
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return f"급식 정보 처리 중 예상치 못한 오류가 발생했습니다: {str(e)}"

def send_to_telegram(bot_token, chat_id, message):
    """Telegram으로 메시지를 전송합니다."""
    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Telegram API에서 안전하게 처리할 수 있는 메시지로 변환
    # <br/> 태그를 줄바꿈으로 변환하고 HTML 특수문자 처리
    safe_message = message.replace('<br/>', '\n').replace('<br>', '\n')
    
    payload = {
        'chat_id': chat_id,
        'text': safe_message,
        'parse_mode': 'HTML'  # HTML 파싱 모드 사용
    }
    
    # HTML 태그로 메시지 재구성 (Telegram에서 지원하는 태그만 사용)
    html_message = safe_message.replace('\n', '\n')
    
    # Telegram에서 지원하는 HTML 태그로 변환
    html_message = html_message.replace('🏫', '<b>🏫</b>')
    html_message = html_message.replace('🍽️', '<b>🍽️</b>')
    html_message = html_message.replace('🍚', '<b>🍚</b>')
    html_message = html_message.replace('🥗', '<b>🥗</b>')
    
    payload['text'] = html_message
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        print(f"Telegram API URL: {telegram_api_url}")
        print(f"Chat ID: {chat_id}")
        print(f"전송할 메시지: {html_message}")
        
        response = requests.post(telegram_api_url, json=payload, headers=headers, timeout=15)
        
        print(f"Telegram API 응답 상태 코드: {response.status_code}")
        print(f"Telegram API 응답 내용: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Telegram 메시지 전송 성공")
                return True
            else:
                print(f"❌ Telegram API 오류: {result.get('description', '알 수 없는 오류')}")
                return False
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram 전송 중 네트워크 에러 발생: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def test_telegram_connection(bot_token, chat_id):
    """Telegram 연결을 테스트합니다."""
    print("🔍 Telegram 연결 테스트 시작...")
    
    test_message = "🧪 오늘의 급식 알림 메시지입니다."
    success = send_to_telegram(bot_token, chat_id, test_message)
    
    if success:
        print("✅ Telegram 연결 테스트 성공!")
    else:
        print("❌ Telegram 연결 테스트 실패!")
    
    return success

if __name__ == "__main__":
    print("🚀 급식 알림봇 시작...")
    print("=" * 50)
    
    neis_api_key, telegram_bot_token, telegram_chat_id = load_config()

    if not neis_api_key or not telegram_bot_token or not telegram_chat_id:
        print("❌ 필수 환경 변수가 설정되지 않았습니다. 스크립트를 종료합니다.")
        exit(1)
    
    print("✅ 환경 변수 설정 완료")
    print("=" * 50)
    
    # Telegram 연결 테스트
    print("🔍 Telegram 연결 테스트 시작...")
    if not test_telegram_connection(telegram_bot_token, telegram_chat_id):
        print("❌ Telegram 연결에 실패했습니다. 설정을 확인해주세요.")
        exit(1)
    
    print("✅ Telegram 연결 테스트 성공!")
    print("=" * 50)
    
    today_date = datetime.now().strftime('%Y%m%d')
    print(f"📅 오늘 날짜: {today_date}")
    print("=" * 50)
    
    print("🍽️ NEIS API에서 급식 정보 조회 시작...")
    api_response = get_api_data(neis_api_key, today_date)

    if api_response:
        print("=" * 50)
        print("📊 NEIS API 응답 분석 시작...")
        print("--- NEIS API Raw Response ---")
        print(json.dumps(api_response, indent=2, ensure_ascii=False))
        print("-----------------------------")
        
        print("📝 급식 정보 메시지 가공 시작...")
        telegram_message = format_meal_data(api_response)
        print(f"📝 가공된 메시지:\n{telegram_message}")
        
        print("📤 Telegram으로 급식 정보 전송 시작...")
        success = send_to_telegram(telegram_bot_token, telegram_chat_id, telegram_message)
        if success:
            print("🎉 급식 정보 전송 완료!")
        else:
            print("💥 급식 정보 전송 실패!")
    else:
        print("❌ NEIS API에서 데이터를 가져올 수 없습니다.")
        print("⚠️ API 실패 시에도 에러 메시지 전송을 시도합니다...")
        # API 실패 시에도 테스트 메시지 전송
        error_message = f"⚠️ {today_date} 급식 정보 조회에 실패했습니다.\n\n가능한 원인:\n• 해당 날짜에 급식 정보가 없음\n• API 서버 오류\n• 네트워크 연결 문제"
        send_to_telegram(telegram_bot_token, telegram_chat_id, error_message)
    
    print("=" * 50)
    print("🏁 급식 알림봇 종료")
