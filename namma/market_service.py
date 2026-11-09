from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .config import DATA_GOV_IN_API_KEY, DATA_GOV_IN_MANDI_RESOURCE_ID, MANDI_CSV_PATH


class MarketDataError(RuntimeError):
    """Raised when a source cannot provide a trustworthy mandi observation."""


DATA_GOV_IN_BASE_URL = "https://api.data.gov.in/resource"
API_TIMEOUT_SECONDS = 12


def default_mandi_csv_path() -> Path:
    return MANDI_CSV_PATH


def mandi_api_is_configured() -> bool:
    return bool(DATA_GOV_IN_API_KEY)


def save_mandi_csv(csv_bytes: bytes, path: str | Path | None = None) -> Path:
    """Validate and save an Agmarknet CSV without replacing a good file on bad input."""
    if not csv_bytes:
        raise MarketDataError("The uploaded CSV is empty.")
    if len(csv_bytes) > 25 * 1024 * 1024:
        raise MarketDataError("CSV is larger than 25 MB. Please download a smaller date or state range.")
    records, headers = _read_csv_records(csv_bytes)
    columns = _map_columns(headers)
    _check_required_columns(columns)
    destination = Path(path) if path else default_mandi_csv_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(destination.suffix + ".tmp")
    temp_path.write_bytes(csv_bytes)
    temp_path.replace(destination)
    return destination


def load_mandi_prices(
    commodity: str,
    district: str = "Bengaluru Urban",
    state: str = "Karnataka",
    limit: int = 100,
    csv_path: str | Path | None = None,
    csv_bytes: bytes | None = None,
    market: str | None = None,
    prefer_api: bool = True,
) -> list[dict[str, Any]]:
    """Fetch official daily observations from data.gov.in first, then use CSV fallback.

    Prices are always source observations. The API key is read from server config,
    never accepted from the browser. A failed/empty API request falls back to a
    previously saved or explicitly supplied official CSV.
    """
    if not commodity or not commodity.strip():
        raise MarketDataError("Choose a commodity first.")

    api_problem: str | None = None
    if prefer_api and DATA_GOV_IN_API_KEY:
        try:
            rows = fetch_mandi_api_prices(
                commodity=commodity, district=district, state=state,
                limit=limit, market=market,
            )
            if rows:
                return rows
            api_problem = "The government API returned no matching records."
        except MarketDataError as exc:
            api_problem = str(exc)

    try:
        rows = _load_csv_prices(
            commodity, district, state, limit, csv_path=csv_path,
            csv_bytes=csv_bytes, market=market,
        )
        for row in rows:
            row["fallback_note"] = api_problem or (
                "Government API key is not configured; using the saved CSV."
                if prefer_api else "Using the supplied CSV."
            )
        return rows
    except MarketDataError as csv_error:
        if api_problem:
            raise MarketDataError(
                f"Government mandi API: {api_problem} CSV fallback: {csv_error}"
            ) from csv_error
        raise


def fetch_mandi_api_prices(
    commodity: str,
    district: str,
    state: str = "Karnataka",
    limit: int = 100,
    market: str | None = None,
    api_key: str | None = None,
    session: Any = requests,
) -> list[dict[str, Any]]:
    """Retrieve and validate records from the official data.gov.in resource API."""
    key = (api_key if api_key is not None else DATA_GOV_IN_API_KEY).strip()
    if not key:
        raise MarketDataError("DATA_GOV_IN_API_KEY is not configured.")
    resource_id = DATA_GOV_IN_MANDI_RESOURCE_ID
    params: dict[str, Any] = {
        "api-key": key,
        "format": "json",
        "limit": max(1, min(int(limit), 1000)),
        "filters[state]": state,
        "filters[commodity]": commodity,
    }
    if market:
        params["filters[market]"] = market
    url = f"{DATA_GOV_IN_BASE_URL}/{resource_id}"
    try:
        response = session.get(url, params=params, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise MarketDataError("The government API took too long to respond.") from exc
    except requests.RequestException as exc:
        raise MarketDataError("Could not connect to the government mandi API.") from exc
    except ValueError as exc:
        raise MarketDataError("The government mandi API returned invalid JSON.") from exc

    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        message = payload.get("message") if isinstance(payload, dict) else None
        # Do not echo the request URL: it contains the private API key.
        raise MarketDataError(str(message or "The government API response did not contain price records."))
    if not records:
        return []
    headers = list(records[0].keys())
    rows = _clean_mandi_records(
        records, headers, commodity, district, state,
        limit=limit, market=market, source_name="data.gov.in Agmarknet API",
        source_label="Agmarknet / data.gov.in API",
    )
    for row in rows:
        row["retrieved_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return rows


def _load_csv_prices(
    commodity: str,
    district: str,
    state: str,
    limit: int,
    csv_path: str | Path | None = None,
    csv_bytes: bytes | None = None,
    market: str | None = None,
) -> list[dict[str, Any]]:
    if csv_bytes is None:
        source_path = Path(csv_path) if csv_path else default_mandi_csv_path()
        if not source_path.exists():
            raise MarketDataError(
                "No mandi CSV is loaded yet. Add DATA_GOV_IN_API_KEY for automatic daily lookup, "
                "or upload an official Agmarknet CSV in Settings."
            )
        try:
            csv_bytes = source_path.read_bytes()
        except OSError as exc:
            raise MarketDataError(f"Could not read mandi CSV: {exc}") from exc
        source_name = source_path.name
    else:
        source_name = Path(csv_path).name if csv_path else "uploaded Agmarknet CSV"
    records, headers = _read_csv_records(csv_bytes)
    rows = _clean_mandi_records(
        records, headers, commodity, district, state, limit=limit,
        market=market, source_name=source_name,
        source_label="Agmarknet / data.gov.in CSV",
    )
    retrieved = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    for row in rows:
        row["retrieved_at"] = retrieved
    return rows


def _clean_mandi_records(
    records: list[dict[str, Any]],
    headers: list[str],
    commodity: str,
    district: str,
    state: str,
    limit: int = 100,
    market: str | None = None,
    source_name: str = "",
    source_label: str = "Agmarknet / data.gov.in",
) -> list[dict[str, Any]]:
    columns = _map_columns(headers)
    _check_required_columns(columns)
    wanted_state = _norm(state)
    wanted_district = _norm(district).replace(" district", "")
    district_aliases = {
        "bengaluru urban": {"bengaluru urban", "bangalore urban", "bengaluru", "bangalore"},
        "bengaluru rural": {"bengaluru rural", "bangalore rural"},
        "ramanagara": {"ramanagara", "ramanagara district"},
    }
    acceptable_districts = district_aliases.get(wanted_district, {wanted_district})
    wanted_commodity = _norm(commodity)
    wanted_market = _norm(market) if market else None
    cleaned: list[dict[str, Any]] = []
    today = date.today()
    for raw in records:
        record = {str(k): str(v if v is not None else "").strip() for k, v in raw.items()}
        state_value = _value(record, columns, "state")
        district_value = _value(record, columns, "district")
        market_value = _value(record, columns, "market")
        commodity_value = _value(record, columns, "commodity")
        if _norm(state_value) != wanted_state:
            continue
        normal_district = _norm(district_value).replace(" district", "")
        if not normal_district or not any(
            alias == normal_district or alias in normal_district or normal_district in alias
            for alias in acceptable_districts
        ):
            continue
        if _norm(commodity_value) != wanted_commodity:
            continue
        if wanted_market and _norm(market_value) != wanted_market:
            continue
        parsed_date = _parse_date(_value(record, columns, "arrival_date"))
        if parsed_date is None:
            continue
        min_price = _number(_value(record, columns, "min_price"))
        max_price = _number(_value(record, columns, "max_price"))
        modal_price = _number(_value(record, columns, "modal_price"))
        prices = [value for value in (min_price, max_price, modal_price) if value is not None]
        if not prices or any(value < 0 for value in prices):
            continue
        if min_price is not None and max_price is not None and min_price > max_price:
            continue
        days_old = max((today - parsed_date).days, 0)
        freshness = "Recent observation" if days_old <= 1 else "May be delayed" if days_old <= 3 else "Older data"
        cleaned.append({
            "state": state_value, "district": district_value, "market": market_value,
            "commodity": commodity_value,
            "variety": _value(record, columns, "variety") if "variety" in columns else "",
            "grade": _value(record, columns, "grade") if "grade" in columns else "",
            "arrival_date": parsed_date.strftime("%d/%m/%Y"),
            "record_date": parsed_date.isoformat(), "days_old": days_old,
            "freshness": freshness, "min_price": min_price,
            "max_price": max_price, "modal_price": modal_price,
            "unit": "₹ / quintal", "source": source_label, "source_file": source_name,
        })
    cleaned.sort(key=lambda row: (row["record_date"], row["market"]), reverse=True)
    if not cleaned:
        raise MarketDataError(
            f"No matching {commodity} records were found for {district}, {state}. "
            "Try another market or district, or use a newer official CSV."
        )
    return cleaned[: max(1, min(int(limit), 1000))]


def _read_csv_records(csv_bytes: bytes) -> tuple[list[dict[str, str]], list[str]]:
    text: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = csv_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise MarketDataError("Could not read the CSV text encoding. Please re-save it as UTF-8 CSV.")
    try:
        reader = csv.DictReader(io.StringIO(text))
        headers = [str(header or "").strip() for header in (reader.fieldnames or [])]
        if not headers:
            raise MarketDataError("The CSV has no header row.")
        records = [
            {str(key or "").strip(): str(value or "").strip() for key, value in row.items() if key is not None}
            for row in reader
        ]
    except csv.Error as exc:
        raise MarketDataError(f"The CSV format is invalid: {exc}") from exc
    if not records:
        raise MarketDataError("The CSV contains column headings but no price records.")
    return records, headers


def _check_required_columns(columns: dict[str, str]) -> None:
    required = ("state", "district", "market", "commodity", "arrival_date", "min_price", "max_price", "modal_price")
    missing = [name for name in required if name not in columns]
    if missing:
        raise MarketDataError("This CSV does not look like the Agmarknet daily-price file. Missing columns: " + ", ".join(missing))


def _normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _map_columns(headers: list[str]) -> dict[str, str]:
    aliases = {
        "state": ("state", "statename"), "district": ("district", "districtname"),
        "market": ("market", "marketname", "apmc", "apmcname"),
        "commodity": ("commodity", "commodityname", "crop"),
        "variety": ("variety", "commodityvariety"), "grade": ("grade", "qualitygrade"),
        "arrival_date": ("arrivaldate", "date", "reporteddate", "pricedate"),
        "min_price": ("minprice", "minimumprice"),
        "max_price": ("maxprice", "maximumprice"),
        "modal_price": ("modalprice", "modelprice"),
    }
    normalised = {_normalise_header(header): header for header in headers}
    result: dict[str, str] = {}
    for field, candidates in aliases.items():
        for candidate in candidates:
            if candidate in normalised:
                result[field] = normalised[candidate]
                break
        if field not in result:
            for norm, original in normalised.items():
                if any(norm.startswith(candidate) for candidate in candidates):
                    result[field] = original
                    break
    return result


def _value(row: dict[str, str], columns: dict[str, str], field: str) -> str:
    return str(row.get(columns[field], "") or "").strip()


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").casefold().strip())


def _parse_date(value: str) -> date | None:
    value = str(value or "").strip()
    for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%Y/%m/%d", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _number(value: Any) -> float | None:
    try:
        cleaned = re.sub(r"[^0-9.\-]", "", str(value).replace(",", "").strip())
        return float(cleaned) if cleaned else None
    except (TypeError, ValueError):
        return None
