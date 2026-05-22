# Sourcing Actions API

국내외 통합 소싱MD GPTs에 연결할 FastAPI Actions 서버입니다.

## 기능

- `/health` 서버 상태 확인
- `/privacy` 개인정보처리방침 테스트 URL
- `/profit/estimate` 마진/손익분기/권장판매가 계산
- `/photo/analyze` 상품 사진 기반 소싱/판매처 추천 보조 API
- `/wholesale/check-dropship` 도매매/도매꾹 위탁판매 가능성 판정
- `/trend/recommend-products` 국가/플랫폼별 시즌·소모품 추천
- `/listing/generate` 상품명/키워드/상세설명/CS 생성
- `/publish/naver/draft` 네이버 등록 초안 생성, 실제 업로드 전 단계

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 확인 주소

```text
http://localhost:8000/health
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

## GPT Actions 연결

1. Render 등에 배포
2. `https://YOUR-SERVICE.onrender.com/openapi.json` 확인
3. GPT Builder → Configure → Actions → Create new action
4. Import from URL에 `/openapi.json` 주소 입력
5. Authentication 설정:
   - Type: API Key
   - Auth Type: Custom
   - Header Name: X-API-Key
   - API Key: 서버의 `ACTION_API_KEY` 값

## Render 설정

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment Variable: `ACTION_API_KEY`
