# 유한양행 DART Financial Intelligence Dashboard

[![Dashboard](dashboard/assets/dashboard-badge.svg)](https://hsc-class01.github.io/SH_YuhanCo/)

## 🔗 대시보드 바로가기

[![🔗 대시보드 바로가기](dashboard/assets/dashboard-badge.svg)](https://hsc-class01.github.io/SH_YuhanCo/)

> DART(OpenDART)의 사업보고서·반기보고서·분기보고서를 수집하고, 2010년 이후 주요 재무수치와 재무비율을 표준화하여 GitHub Pages 대시보드로 제공하는 자동화 프로젝트입니다.

## 구성

- **2010~2014**: DART 공시검색 API → 정기보고서 원문 ZIP → 표 기반 heuristic parser
- **2015~현재**: OpenDART `fnlttSinglAcntAll` XBRL 재무제표 API
- **보고서**: 사업보고서(11011), 반기보고서(11012), 1분기보고서(11013), 3분기보고서(11014)
- **기준**: 기본값 연결재무제표(CFS)
- **분석**: 매출, 매출총이익, 영업이익, 세전이익, 순이익, 지배주주순이익, EBITDA 보조지표, CFO/CFI/CFF, CAPEX, FCF, 자산·부채·자본, 현금, 매출채권, 재고, 차입금 및 수익성·유동성·재무안정성·현금흐름 비율
- **자동화**: 매월 1일 09:17 KST GitHub Actions 실행
- **배포**: GitHub Pages

## 1. DART API Key 입력

API Key는 소스코드에 직접 입력하지 않습니다.

### GitHub Actions

1. GitHub 저장소 → **Settings → Secrets and variables → Actions**
2. **New repository secret** 선택
3. Name: `DART_API_KEY`
4. Secret: OpenDART에서 발급받은 40자리 인증키
5. 저장

OpenDART 인증키는 API 요청의 `crtfc_key` 파라미터로 사용됩니다. API 키가 코드나 README에 노출되지 않도록 GitHub Secret으로만 저장하세요.

### 로컬 실행

Windows PowerShell:

```powershell
$env:DART_API_KEY="여기에_발급받은_키"
python -m pip install -r requirements.txt
python scripts/update.py
python scripts/build_site.py
```

macOS/Linux:

```bash
export DART_API_KEY="여기에_발급받은_키"
python -m pip install -r requirements.txt
python scripts/update.py
python scripts/build_site.py
```

## 2. GitHub Actions 설치

ZIP에는 업로드 장애를 줄이기 위해 **숨김 파일을 넣지 않았습니다.** 따라서 ZIP의 `UPDATE_AND_DEPLOY_WORKFLOW.yml`을 다음 경로에 업로드/이동하세요.

```text
.github/workflows/update-and-deploy.yml
```

현재 ZIP에는 같은 파일을 `github_workflows/update-and-deploy.yml`에도 넣어 두었습니다. GitHub 웹 UI에서 `.github/workflows/` 폴더를 만들고 파일을 이동해도 됩니다.

워크플로우는 `workflow_dispatch` 수동 실행과 매월 1일 스케줄 실행을 모두 지원합니다.

## 3. GitHub Pages 설정

저장소에서:

**Settings → Pages → Build and deployment → Source: GitHub Actions**

첫 실행이 성공하면 프로젝트 Pages 주소는 기본적으로 다음 형식입니다.

`https://hsc-class01.github.io/SH_YuhanCo/`

## 4. About 섹션에 대시보드 링크

저장소 메인 화면 → 오른쪽 **About → 톱니바퀴(Edit repository details)** → Website에 다음 주소 입력:

`https://hsc-class01.github.io/SH_YuhanCo/`

가능하면 **Use your README** 링크와 중복되지 않도록 Website 항목에 대시보드 URL을 넣으세요.

## 5. 데이터 갱신 방식

매월 1일 Action이 실행되면:

1. DART `corpCode.xml`에서 유한양행의 DART 고유번호를 확인
2. 해당 연도의 정기보고서 데이터 조회
3. 신규/변경된 재무수치 정규화
4. 재무비율 계산
5. `data/*.csv` 갱신
6. `dashboard/data/*` 갱신
7. 변경사항 commit
8. GitHub Pages 재배포

분기 보고서의 손익계산서 항목은 DART가 제공하는 누적 기간 값과 전기 누적값을 이용해 필요한 경우 독립 분기값으로 변환합니다. 재무상태표 항목은 시점잔액이므로 임의 차감하지 않습니다.

## 6. 주요 계산식

- 매출총이익률 = 매출총이익 / 매출액
- 영업이익률 = 영업이익 / 매출액
- 순이익률 = 당기순이익 / 매출액
- 유동비율 = 유동자산 / 유동부채
- 부채비율 = 총부채 / 자본총계
- 자기자본비율 = 자본총계 / 총자산
- 차입금의존도 = 이자부차입금 / 총자산
- 이자보상배율 = 영업이익 / 이자비용
- 순차입금 = 이자부차입금 - 현금및현금성자산
- FCF = 영업활동현금흐름 - CAPEX
- CFO/순이익 = 영업활동현금흐름 / 당기순이익
- ROA/ROE는 현재 구현에서 기간자료와 시점자료의 정합성을 고려한 보조지표로 제공하며, 정밀 분석 시 평균 자산·평균 자본 기준으로 재계산할 수 있습니다.

## 7. Peer firms

Peer universe는 국내 상장 제약사 중 유한양행과 사업구조 및 매출 규모를 비교하기 쉬운 기업으로 구성했습니다.

- 한미약품 (128940)
- GC녹십자 (006280)
- 대웅제약 (069620)
- 종근당 (185750)
- HK이노엔 (195940)
- 동아에스티 (170900)

Peer universe는 고정된 투자평가 순위가 아니라 대시보드 비교 범위입니다. 분석 시에는 동일한 회계기준과 기간을 사용하세요.

## 출처

- OpenDART 개발가이드: https://opendart.fss.or.kr/guide/main.do
- DART 공시검색: https://dart.fss.or.kr/
- 금융감독원 전자공시시스템

## 주의

OpenDART가 제공하는 재무정보는 공시의무자가 제출한 자료를 기반으로 하며, 서비스 안내에서도 원문 공시와 비교·확인할 것을 안내합니다. 2010~2014년 원문 파서는 계정명/표 구조의 역사적 차이 때문에 일부 값이 `null`로 남을 수 있습니다. 이 경우 추측으로 값을 채우지 않고 공시 원문 확인이 필요합니다.
