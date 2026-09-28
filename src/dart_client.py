from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://opendart.fss.or.kr/api"
TIMEOUT = 60


class DartAPIError(RuntimeError):
    pass


class DartClient:
    def __init__(self, api_key: str, raw_dir: str | Path = "data/raw") -> None:
        if not api_key:
            raise ValueError("DART_API_KEY가 필요합니다.")
        self.api_key = api_key
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SH_YuhanCo-DART-Agent/1.0"})

    def get_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        p = {"crtfc_key": self.api_key, **params}
        r = self.session.get(f"{BASE_URL}/{endpoint}.json", params=p, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if str(data.get("status")) != "000":
            raise DartAPIError(f"DART {data.get('status')}: {data.get('message')}")
        return data

    def download_bytes(self, endpoint: str, params: dict[str, Any]) -> bytes:
        p = {"crtfc_key": self.api_key, **params}
        r = self.session.get(f"{BASE_URL}/{endpoint}.xml", params=p, timeout=TIMEOUT)
        r.raise_for_status()
        content = r.content
        # Binary endpoints return a ZIP payload even though the endpoint ends in .xml.
        if not content.startswith(b"PK"):
            try:
                msg = content.decode("utf-8", errors="ignore")[:500]
            except Exception:
                msg = "binary response"
            raise DartAPIError(f"DART binary API 오류: {msg}")
        return content

    def corp_code_map(self) -> dict[str, dict[str, str]]:
        p = {"crtfc_key": self.api_key}
        r = self.session.get(f"{BASE_URL}/corpCode.xml", params=p, timeout=TIMEOUT)
        r.raise_for_status()
        if not r.content.startswith(b"PK"):
            raise DartAPIError("corpCode.xml 응답이 ZIP 파일이 아닙니다.")
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            xml = zf.read(zf.namelist()[0]).decode("utf-8-sig", errors="replace")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(xml, "xml")
        result = {}
        for item in soup.find_all("list"):
            stock = (item.stock_code.text or "").strip()
            if stock:
                result[stock] = {
                    "corp_code": (item.corp_code.text or "").strip(),
                    "corp_name": (item.corp_name.text or "").strip(),
                    "stock_code": stock,
                }
        return result

    def find_corp_code(self, stock_code: str) -> str:
        mapping = self.corp_code_map()
        if stock_code not in mapping:
            raise DartAPIError(f"종목코드 {stock_code}의 DART corp_code를 찾지 못했습니다.")
        return mapping[stock_code]["corp_code"]

    def full_financials(self, corp_code: str, year: int, reprt_code: str, fs_div: str = "CFS") -> dict[str, Any]:
        return self.get_json(
            "fnlttSinglAcntAll",
            {"corp_code": corp_code, "bsns_year": str(year), "reprt_code": reprt_code, "fs_div": fs_div},
        )

    def report_list(self, corp_code: str, bgn_de: str, end_de: str, page_no: int = 1, page_count: int = 100) -> dict[str, Any]:
        return self.get_json(
            "list",
            {
                "corp_code": corp_code,
                "bgn_de": bgn_de,
                "end_de": end_de,
                "page_no": page_no,
                "page_count": page_count,
                "pblntf_ty": "A",  # 정기공시
            },
        )

    def original_document(self, rcept_no: str) -> bytes:
        return self.download_bytes("document", {"rcept_no": rcept_no})
