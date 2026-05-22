import os
import time
import hmac
import hashlib
import datetime
from typing import List, Optional, Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

APP_TITLE = "Global Sourcing Seller Actions API"
APP_VERSION = "1.0.0"

ACTION_API_KEY = os.getenv("ACTION_API_KEY", "change-this-to-a-long-random-secret")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

COUPANG_ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
COUPANG_SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")
COUPANG_VENDOR_ID = os.getenv("COUPANG_VENDOR_ID")

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "Actions API for product sourcing, profit estimation, marketplace recommendation, "
        "dropship checks, trend analysis, listing content generation, and draft publishing."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_action_key(x_api_key: Optional[str]) -> None:
    """GPT Actions가 내 서버를 호출할 때 쓰는 단순 API Key 검증."""
    if not ACTION_API_KEY:
        return
    if x_api_key != ACTION_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class HealthResponse(BaseModel):
    status: str = Field(..., description="API status")
    version: str = Field(..., description="API version")


class RiskFlag(BaseModel):
    code: str = Field(..., description="Risk code")
    level: Literal["low", "medium", "high"] = Field(..., description="Risk level")
    message: str = Field(..., description="Human-readable risk message")


class SourceRecommendation(BaseModel):
    source: str = Field(..., description="Recommended sourcing channel")
    score: int = Field(..., ge=0, le=100, description="Recommendation score")
    reason: str = Field(..., description="Reason for recommendation")


class MarketRecommendation(BaseModel):
    market: str = Field(..., description="Recommended selling marketplace")
    score: int = Field(..., ge=0, le=100, description="Recommendation score")
    reason: str = Field(..., description="Reason for recommendation")


class PhotoAnalyzeRequest(BaseModel):
    image_url: str = Field(..., description="Public or temporary URL of the product image")
    target_markets: List[str] = Field(
        default_factory=list,
        description="Target marketplaces such as naver, coupang, shopee, ebay, poizon, qoo10_japan",
    )
    memo: Optional[str] = Field(None, description="Optional user memo about the product")


class PhotoAnalyzeResponse(BaseModel):
    product_guess: str = Field(..., description="Estimated product name")
    category: str = Field(..., description="Estimated product category")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    consumable: bool = Field(..., description="Whether this looks like a consumable or repeat-purchase product")
    seasonality: str = Field(..., description="Seasonality estimate")
    risk_flags: List[RiskFlag] = Field(default_factory=list, description="Detected product risks")
    recommended_sources: List[SourceRecommendation] = Field(default_factory=list, description="Recommended sourcing channels")
    recommended_markets: List[MarketRecommendation] = Field(default_factory=list, description="Recommended selling marketplaces")
    final_decision: str = Field(..., description="Final decision such as sellable, conditional, hold, high-risk, exclude")


class ProfitEstimateRequest(BaseModel):
    product_name: str = Field(..., description="Product name")
    source_price: float = Field(..., ge=0, description="Source purchase price")
    currency: str = Field("KRW", description="Currency of source_price")
    exchange_rate: float = Field(1.0, gt=0, description="Exchange rate to KRW or target calculation currency")
    local_shipping: float = Field(0, ge=0, description="Local shipping fee at source country")
    buying_agent_fee: float = Field(0, ge=0, description="Buying agent or procurement fee")
    international_shipping: float = Field(0, ge=0, description="International shipping fee")
    customs_rate: float = Field(0, ge=0, description="Customs duty rate, example 0.08 for 8 percent")
    import_vat_rate: float = Field(0.10, ge=0, description="Import VAT rate")
    customs_clearance_fee: float = Field(0, ge=0, description="Customs clearance fee")
    inbound_shipping: float = Field(0, ge=0, description="Domestic inbound shipping fee to warehouse")
    domestic_shipping: float = Field(0, ge=0, description="Domestic shipping fee to customer")
    packaging_cost: float = Field(0, ge=0, description="Packaging cost")
    platform_fee_rate: float = Field(0, ge=0, description="Marketplace fee rate")
    payment_fee_rate: float = Field(0, ge=0, description="Payment fee rate")
    ad_cost_estimate: float = Field(0, ge=0, description="Estimated ad cost per order")
    return_reserve: float = Field(0, ge=0, description="Return and CS reserve per order")
    target_margin_rate: float = Field(0.25, ge=0, lt=0.95, description="Target profit margin rate")
    target_market: str = Field(..., description="Target marketplace")


class ProfitEstimateResponse(BaseModel):
    total_landed_cost: float = Field(..., description="Total landed cost before marketplace percentage fees")
    breakeven_price: float = Field(..., description="Break-even selling price")
    aggressive_price: float = Field(..., description="Aggressive selling price")
    recommended_price: float = Field(..., description="Recommended selling price")
    high_margin_price: float = Field(..., description="High-margin selling price")
    expected_profit: float = Field(..., description="Expected profit at recommended price")
    margin_rate: float = Field(..., description="Expected profit margin rate")
    notes: List[str] = Field(default_factory=list, description="Important notes")


class DropshipCheckRequest(BaseModel):
    product_url: str = Field(..., description="DomeMae or DomeGgook product URL")
    source: Literal["domeme", "domeggook"] = Field(..., description="Wholesale source")
    product_name: Optional[str] = Field(None, description="Optional product name")


class DropshipCheckResponse(BaseModel):
    eligible: bool = Field(..., description="Whether dropshipping appears eligible")
    score: int = Field(..., ge=0, le=100, description="Dropshipping score")
    min_order_qty: int = Field(..., ge=1, description="Minimum order quantity")
    direct_shipping_available: bool = Field(..., description="Whether direct shipping to customer appears available")
    image_usage_status: str = Field(..., description="Image usage status")
    supplier_risk: str = Field(..., description="Supplier risk level")
    reasons: List[str] = Field(default_factory=list, description="Reasons for the decision")


class TrendRecommendRequest(BaseModel):
    country: str = Field(..., description="Target country")
    platform: str = Field(..., description="Target platform")
    category: Optional[str] = Field(None, description="Optional category")
    month: Optional[str] = Field(None, description="Target month, example 2026-06")
    include_consumables: bool = Field(True, description="Whether to include consumable products")


class TrendProduct(BaseModel):
    product: str = Field(..., description="Recommended product")
    demand_score: int = Field(..., ge=0, le=100, description="Demand score")
    seasonality: str = Field(..., description="Seasonality")
    recommended_source: str = Field(..., description="Recommended sourcing channel")
    recommended_market: str = Field(..., description="Recommended marketplace")
    risk: str = Field(..., description="Risk level")
    reason: str = Field(..., description="Reason for recommendation")


class TrendRecommendResponse(BaseModel):
    country: str = Field(..., description="Target country")
    platform: str = Field(..., description="Target platform")
    recommendations: List[TrendProduct] = Field(default_factory=list, description="Product recommendations")


class ListingGenerateRequest(BaseModel):
    product_name: str = Field(..., description="Product name")
    category: Optional[str] = Field(None, description="Product category")
    target_market: str = Field(..., description="Target marketplace")
    language: str = Field("ko", description="Output language")
    product_features: List[str] = Field(default_factory=list, description="Product features")
    risk_flags: List[str] = Field(default_factory=list, description="Risk flags to avoid risky claims")


class FAQItem(BaseModel):
    question: str = Field(..., description="FAQ question")
    answer: str = Field(..., description="FAQ answer")


class ListingGenerateResponse(BaseModel):
    title: str = Field(..., description="Listing title")
    keywords: List[str] = Field(default_factory=list, description="Search keywords")
    description: str = Field(..., description="Product description")
    thumbnail_copy: List[str] = Field(default_factory=list, description="Thumbnail copy ideas")
    detail_page_sections: List[str] = Field(default_factory=list, description="Detail page section plan")
    cs_faq: List[FAQItem] = Field(default_factory=list, description="CS and FAQ items")


class NaverDraftRequest(BaseModel):
    product_name: str = Field(..., description="Product name")
    price: int = Field(..., ge=0, description="Selling price")
    description: str = Field(..., description="Listing description")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    category_id: Optional[str] = Field(None, description="Naver category ID")
    memo: Optional[str] = Field(None, description="Internal memo")


class DraftResponse(BaseModel):
    status: str = Field(..., description="Draft status")
    message: str = Field(..., description="Result message")
    product_name: str = Field(..., description="Product name")
    price: int = Field(..., description="Price")
    warnings: List[str] = Field(default_factory=list, description="Warnings")


@app.get("/", response_model=HealthResponse, operation_id="rootHealthCheck")
def root_health_check():
    return HealthResponse(status="ok", version=APP_VERSION)


@app.get("/health", response_model=HealthResponse, operation_id="healthCheck")
def health_check():
    return HealthResponse(status="ok", version=APP_VERSION)


@app.get("/privacy", operation_id="privacyPolicy")
def privacy_policy():
    return {
        "privacy_policy": (
            "This API processes product analysis requests for sourcing and selling recommendations. "
            "Do not send sensitive personal information. Product data may be logged for debugging "
            "depending on server settings."
        )
    }


@app.post("/photo/analyze", response_model=PhotoAnalyzeResponse, operation_id="analyzeProductPhoto")
def analyze_product_photo(request: PhotoAnalyzeRequest, x_api_key: Optional[str] = Header(None)):
    verify_action_key(x_api_key)

    risk_flags = [
        RiskFlag(
            code="PHOTO_ONLY",
            level="medium",
            message="사진만으로 정확한 모델명, 인증, 브랜드 여부는 확정할 수 없습니다.",
        )
    ]

    if request.memo and any(word in request.memo for word in ["배터리", "전기", "무선", "충전"]):
        risk_flags.append(
            RiskFlag(
                code="KC_CHECK",
                level="high",
                message="전기·배터리·무선 상품일 가능성이 있어 KC/배송 제한 확인이 필요합니다.",
            )
        )

    return PhotoAnalyzeResponse(
        product_guess="상품 사진 기반 추정 필요",
        category="생활용품/잡화 추정",
        confidence=0.55,
        consumable=False,
        seasonality="확인 필요",
        risk_flags=risk_flags,
        recommended_sources=[
            SourceRecommendation(source="1688", score=80, reason="유사 생활잡화 소싱 후보가 많습니다."),
            SourceRecommendation(source="도매매", score=72, reason="초기 위탁 테스트 후보로 적합할 수 있습니다."),
            SourceRecommendation(source="도매꾹", score=65, reason="묶음 사입 후보로 확인할 수 있습니다."),
        ],
        recommended_markets=[
            MarketRecommendation(market="네이버 스마트스토어", score=82, reason="검색형 생활용품 테스트에 적합합니다."),
            MarketRecommendation(market="Shopee", score=70, reason="가볍고 소형 상품이면 해외 테스트가 가능합니다."),
            MarketRecommendation(market="쿠팡", score=64, reason="가격경쟁과 인증 여부 확인이 필요합니다."),
        ],
        final_decision="조건부 가능",
    )


@app.post("/profit/estimate", response_model=ProfitEstimateResponse, operation_id="estimateProfit")
def estimate_profit(request: ProfitEstimateRequest, x_api_key: Optional[str] = Header(None)):
    verify_action_key(x_api_key)

    source_cost_krw = request.source_price * request.exchange_rate
    import_base = source_cost_krw + request.local_shipping + request.buying_agent_fee + request.international_shipping
    customs = import_base * request.customs_rate
    import_vat = (import_base + customs) * request.import_vat_rate

    fixed_cost = (
        import_base
        + customs
        + import_vat
        + request.customs_clearance_fee
        + request.inbound_shipping
        + request.domestic_shipping
        + request.packaging_cost
        + request.ad_cost_estimate
        + request.return_reserve
    )

    percentage_fee_rate = request.platform_fee_rate + request.payment_fee_rate
    if percentage_fee_rate >= 0.95:
        raise HTTPException(status_code=400, detail="Fee rate is too high")

    breakeven_price = fixed_cost / (1 - percentage_fee_rate)
    recommended_price = breakeven_price / max(0.01, (1 - request.target_margin_rate))
    aggressive_price = breakeven_price * 1.10

    high_margin_target = min(request.target_margin_rate + 0.10, 0.90)
    high_margin_price = breakeven_price / max(0.01, (1 - high_margin_target))

    expected_fees = recommended_price * percentage_fee_rate
    expected_profit = recommended_price - fixed_cost - expected_fees
    margin_rate = expected_profit / recommended_price if recommended_price > 0 else 0

    return ProfitEstimateResponse(
        total_landed_cost=round(fixed_cost, 2),
        breakeven_price=round(breakeven_price, 2),
        aggressive_price=round(aggressive_price, 2),
        recommended_price=round(recommended_price, 2),
        high_margin_price=round(high_margin_price, 2),
        expected_profit=round(expected_profit, 2),
        margin_rate=round(margin_rate, 4),
        notes=[
            "관세율, 수입부가세, 플랫폼 수수료는 최신 기준 확인이 필요합니다.",
            "광고비와 반품 예비비는 실제 운영 데이터로 보정하세요.",
        ],
    )


@app.post("/wholesale/check-dropship", response_model=DropshipCheckResponse, operation_id="checkDropshipEligibility")
def check_dropship_eligibility(request: DropshipCheckRequest, x_api_key: Optional[str] = Header(None)):
    verify_action_key(x_api_key)

    if request.source == "domeme":
        return DropshipCheckResponse(
            eligible=True,
            score=78,
            min_order_qty=1,
            direct_shipping_available=True,
            image_usage_status="확인 필요",
            supplier_risk="medium",
            reasons=[
                "도매매는 위탁배송 후보로 우선 검토할 수 있습니다.",
                "이미지 사용 가능 여부와 반품 조건은 상품별 확인이 필요합니다.",
            ],
        )

    return DropshipCheckResponse(
        eligible=False,
        score=55,
        min_order_qty=2,
        direct_shipping_available=False,
        image_usage_status="확인 필요",
        supplier_risk="medium",
        reasons=[
            "도매꾹은 사입형 상품이 많아 위탁배송 여부 확인이 필요합니다.",
            "최소구매수량과 고객 직배송 가능 여부를 확인하세요.",
        ],
    )


@app.post("/trend/recommend-products", response_model=TrendRecommendResponse, operation_id="recommendTrendingProducts")
def recommend_trending_products(request: TrendRecommendRequest, x_api_key: Optional[str] = Header(None)):
    verify_action_key(x_api_key)

    recommendations = [
        TrendProduct(
            product="여행용 압축 파우치",
            demand_score=86,
            seasonality="휴가철/여행 시즌 강함",
            recommended_source="1688 또는 도매매",
            recommended_market=request.platform,
            risk="low",
            reason="가볍고 배송비 부담이 낮으며 국가별 여행 수요에 맞습니다.",
        ),
        TrendProduct(
            product="욕실 틈새 청소 브러시",
            demand_score=82,
            seasonality="연중 꾸준한 생활 소모품",
            recommended_source="1688 또는 도매매",
            recommended_market=request.platform,
            risk="low",
            reason="소모성 생활용품이며 재구매 가능성이 있습니다.",
        ),
        TrendProduct(
            product="차량용 소형 정리함",
            demand_score=76,
            seasonality="연중 수요, 차량용품 시즌에 상승",
            recommended_source="1688 또는 도매꾹",
            recommended_market=request.platform,
            risk="medium",
            reason="부피와 배송비를 확인하면 판매 후보가 될 수 있습니다.",
        ),
    ]

    return TrendRecommendResponse(
        country=request.country,
        platform=request.platform,
        recommendations=recommendations,
    )


@app.post("/listing/generate", response_model=ListingGenerateResponse, operation_id="generateListingPackage")
def generate_listing_package(request: ListingGenerateRequest, x_api_key: Optional[str] = Header(None)):
    verify_action_key(x_api_key)

    safe_features = request.product_features or ["간편한 사용", "실용적인 구성", "일상 생활에 적합"]
    title = f"{request.product_name} 실용 생활용품 추천"

    # 위험 플래그가 있으면 과장·인증 표현을 피하는 방향으로 문구를 보수화
    risk_note = ""
    if request.risk_flags:
        risk_note = " 인증, 효능, 원산지, 구성품 관련 표현은 실제 확인된 정보만 사용해 주세요."

    return ListingGenerateResponse(
        title=title,
        keywords=[request.product_name, request.category or "생활용품", request.target_market, "소싱상품"],
        description=(
            f"{request.product_name}은 일상에서 활용하기 좋은 상품입니다. "
            f"주요 특징은 {', '.join(safe_features)}입니다. "
            "실제 색상, 사이즈, 구성품은 상세 정보를 확인해 주세요."
            f"{risk_note}"
        ),
        thumbnail_copy=[
            "일상에서 간편하게",
            "깔끔한 정리와 편리한 사용",
            "실용적인 생활 아이템",
        ],
        detail_page_sections=[
            "상단 후킹 이미지",
            "상품 핵심 장점",
            "사용 장면",
            "사이즈/스펙",
            "구성품 안내",
            "사용 방법",
            "주의사항",
            "배송/교환/반품 안내",
        ],
        cs_faq=[
            FAQItem(question="배송은 얼마나 걸리나요?", answer="주문 후 상품 준비 및 배송 상황에 따라 달라질 수 있습니다."),
            FAQItem(question="반품이 가능한가요?", answer="상품 수령 후 미사용 상태와 판매처 정책에 따라 반품 가능 여부가 결정됩니다."),
            FAQItem(question="색상이 사진과 같나요?", answer="모니터와 촬영 환경에 따라 실제 색상과 차이가 있을 수 있습니다."),
        ],
    )


@app.post("/publish/naver/draft", response_model=DraftResponse, operation_id="createNaverDraft")
def create_naver_draft(payload: NaverDraftRequest, x_api_key: Optional[str] = Header(None)):
    verify_action_key(x_api_key)

    warnings = [
        "현재 엔드포인트는 실제 네이버 등록이 아니라 등록 초안 생성용입니다.",
        "실제 등록 전 카테고리, 고시정보, 이미지 권리, KC/인증 여부를 검수하세요.",
    ]

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        warnings.append("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 아직 설정되지 않았습니다.")

    return DraftResponse(
        status="draft_ready",
        message="네이버 등록 초안이 생성되었습니다. 실제 등록 API 연결 전 검수용으로 사용하세요.",
        product_name=payload.product_name,
        price=payload.price,
        warnings=warnings,
    )


# ===== 외부 마켓 API 연결용 예시 함수: 실제 엔드포인트에 붙여 확장 =====

_naver_token_cache = {"access_token": None, "expires_at": 0}


def get_naver_access_token() -> str:
    """네이버 커머스API access_token 발급 예시. 실제 키 입력 후 사용."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are required")

    now = time.time()
    if _naver_token_cache["access_token"] and now < _naver_token_cache["expires_at"] - 60:
        return _naver_token_cache["access_token"]

    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": NAVER_CLIENT_ID,
        "client_secret": NAVER_CLIENT_SECRET,
    }
    response = requests.post(url, data=data, timeout=20)
    response.raise_for_status()
    token_data = response.json()

    access_token = token_data["access_token"]
    expires_in = int(token_data.get("expires_in", 10800))

    _naver_token_cache["access_token"] = access_token
    _naver_token_cache["expires_at"] = now + expires_in
    return access_token


def coupang_authorization(method: str, path: str, query: str = "") -> str:
    """쿠팡 Open API HMAC Authorization 헤더 생성 예시."""
    if not COUPANG_ACCESS_KEY or not COUPANG_SECRET_KEY:
        raise RuntimeError("COUPANG_ACCESS_KEY and COUPANG_SECRET_KEY are required")

    datetime_utc = datetime.datetime.utcnow().strftime("%y%m%dT%H%M%SZ")
    message = datetime_utc + method.upper() + path + query
    signature = hmac.new(
        COUPANG_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return (
        f"CEA algorithm=HmacSHA256, access-key={COUPANG_ACCESS_KEY}, "
        f"signed-date={datetime_utc}, signature={signature}"
    )
