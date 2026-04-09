"""Founder Finance service — business expense tracking, AI categorization, tax summaries.

MIGRATION STATUS: Migrated to psycopg3 raw SQL queries.
- Uses core_app.queries.founder_finance for all data operations
- Uses core_app.db.acquire for connection management
- Uses core_app.db.transaction for transaction management
- OTEL tracing enabled on all service methods
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import boto3
from opentelemetry import trace
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from core_app.ai.bedrock_service import BedrockClient, BedrockClientError, get_bedrock_client
from core_app.ai.service import AiService
from core_app.core.config import Settings, get_settings
from core_app.db import acquire
from core_app.db.transaction import managed_transaction
from core_app.documents.s3_storage import (
    default_exports_bucket,
    default_founder_finance_bucket,
    default_founder_personal_tax_bucket,
    presign_get,
    put_bytes,
)
from core_app.queries import founder_finance as ff_queries

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_RE_TOTAL = re.compile(r"(?:total|amount due|balance due)\s*[:#-]?\s*\$?([0-9][0-9,]*\.?[0-9]{0,2})", re.IGNORECASE)
_RE_TAX = re.compile(r"(?:tax|sales tax|vat)\s*[:#-]?\s*\$?([0-9][0-9,]*\.?[0-9]{0,2})", re.IGNORECASE)
_RE_ANY_AMOUNT = re.compile(r"\$?([0-9][0-9,]*\.?[0-9]{2})")
_RE_ISO_DATE = re.compile(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b")
_RE_US_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b")

LOW_CONFIDENCE_THRESHOLD = 0.78


@dataclass(slots=True)
class CategorizationSuggestion:
    category: str
    account_code: str
    confidence: float
    rationale: str
    provider: str
    summary: str | None = None
    raw_response: dict[str, Any] | None = None


DEFAULT_ACCOUNT_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "code": "1000",
        "name": "Operating Cash",
        "classification": "asset",
        "normal_balance": "debit",
        "tax_category": "balance_sheet",
        "description": "Primary founder business operating cash account.",
    },
    {
        "code": "1100",
        "name": "Accounts Receivable",
        "classification": "asset",
        "normal_balance": "debit",
        "tax_category": "balance_sheet",
        "description": "Open founder receivables when modeled.",
    },
    {
        "code": "2000",
        "name": "Accounts Payable",
        "classification": "liability",
        "normal_balance": "credit",
        "tax_category": "balance_sheet",
        "description": "Outstanding founder operating payables.",
    },
    {
        "code": "2100",
        "name": "Tax Reserve",
        "classification": "liability",
        "normal_balance": "credit",
        "tax_category": "tax_reserve",
        "description": "Quarterly founder tax reserve liability.",
    },
    {
        "code": "4000",
        "name": "Stripe Subscription Revenue",
        "classification": "revenue",
        "normal_balance": "credit",
        "tax_category": "gross_income",
        "description": "Recurring platform subscription revenue.",
    },
    {
        "code": "4010",
        "name": "Services Revenue",
        "classification": "revenue",
        "normal_balance": "credit",
        "tax_category": "gross_income",
        "description": "Non-subscription founder services revenue.",
    },
    {
        "code": "5000",
        "name": "Software Expense",
        "classification": "expense",
        "normal_balance": "debit",
        "tax_category": "deductible_software",
        "description": "Software subscriptions and tooling.",
    },
    {
        "code": "5010",
        "name": "Infrastructure Expense",
        "classification": "expense",
        "normal_balance": "debit",
        "tax_category": "deductible_infrastructure",
        "description": "Cloud, hosting, and infrastructure.",
    },
    {
        "code": "5020",
        "name": "Communications Expense",
        "classification": "expense",
        "normal_balance": "debit",
        "tax_category": "deductible_communications",
        "description": "Voice, SMS, and communications vendors.",
    },
    {
        "code": "5030",
        "name": "Marketing Expense",
        "classification": "expense",
        "normal_balance": "debit",
        "tax_category": "deductible_marketing",
        "description": "Demand generation and campaigns.",
    },
    {
        "code": "5040",
        "name": "Legal Expense",
        "classification": "expense",
        "normal_balance": "debit",
        "tax_category": "deductible_professional_services",
        "description": "Legal and professional services.",
    },
    {
        "code": "5050",
        "name": "Mailing Expense",
        "classification": "expense",
        "normal_balance": "debit",
        "tax_category": "deductible_operations",
        "description": "Postage, printing, and document delivery.",
    },
    {
        "code": "5060",
        "name": "AI Expense",
        "classification": "expense",
        "normal_balance": "debit",
        "tax_category": "deductible_research_and_development",
        "description": "Model, inference, and AI enablement costs.",
    },
    {
        "code": "5099",
        "name": "Miscellaneous Expense",
        "classification": "expense",
        "normal_balance": "debit",
        "tax_category": "deductible_other",
        "description": "Unclassified but approved founder expenses.",
    },
)

CATEGORY_ACCOUNT_MAP: dict[str, str] = {
    "Software": "5000",
    "Infrastructure": "5010",
    "Communications": "5020",
    "Marketing": "5030",
    "Legal": "5040",
    "Mailing": "5050",
    "AI/ML": "5060",
    "Other": "5099",
}

VENDOR_RULES: tuple[tuple[str, str, str, float, str], ...] = (
    ("aws", "Infrastructure", "5010", 0.94, "AWS spend maps to infrastructure."),
    ("amazon web services", "Infrastructure", "5010", 0.94, "AWS spend maps to infrastructure."),
    ("cloudflare", "Infrastructure", "5010", 0.91, "Cloud/network vendor maps to infrastructure."),
    ("stripe", "Software", "5000", 0.88, "Stripe platform costs are software/payment tooling spend."),
    ("github", "Software", "5000", 0.92, "Developer tooling maps to software expense."),
    ("figma", "Software", "5000", 0.92, "Design tooling maps to software expense."),
    ("slack", "Software", "5000", 0.92, "Collaboration tooling maps to software expense."),
    ("telnyx", "Communications", "5020", 0.94, "Telnyx spend maps to communications expense."),
    ("lob", "Mailing", "5050", 0.93, "Lob spend maps to mailing and print operations."),
    ("openai", "AI/ML", "5060", 0.94, "Model provider spend maps to AI/ML expense."),
    ("anthropic", "AI/ML", "5060", 0.94, "Model provider spend maps to AI/ML expense."),
    ("google ads", "Marketing", "5030", 0.95, "Ad network maps to marketing expense."),
    ("linkedin", "Marketing", "5030", 0.95, "Ad network maps to marketing expense."),
    ("legal", "Legal", "5040", 0.84, "Professional legal spend maps to legal expense."),
)


class FounderFinanceAccessError(PermissionError):
    pass


class FounderFinanceConfigError(RuntimeError):
    pass


class FounderFinanceProcessingError(RuntimeError):
    pass


def ensure_personal_vault_access(current_user_id: uuid.UUID, owner_user_id: uuid.UUID) -> None:
    if current_user_id != owner_user_id:
        raise FounderFinanceAccessError("personal_tax_vault_forbidden")


def parse_currency_to_cents(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.replace(",", "").replace("$", "").strip()
    if not normalized:
        return 0
    dollars, dot, cents = normalized.partition(".")
    whole = int(dollars or "0")
    frac = int((cents + "00")[:2]) if dot else 0
    return whole * 100 + frac


def parse_receipt_fields(filename: str, content_type: str, ocr_text: str) -> dict[str, Any]:
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    vendor_name = ""
    for line in lines[:5]:
        lowered = line.lower()
        if any(token in lowered for token in ("receipt", "invoice", "thank you", "subtotal", "total")):
            continue
        vendor_name = line[:255]
        break
    total_match = _RE_TOTAL.search(ocr_text)
    tax_match = _RE_TAX.search(ocr_text)
    any_amounts = [parse_currency_to_cents(match.group(1)) for match in _RE_ANY_AMOUNT.finditer(ocr_text)]
    total_cents = parse_currency_to_cents(total_match.group(1)) if total_match else (max(any_amounts) if any_amounts else 0)
    tax_cents = parse_currency_to_cents(tax_match.group(1)) if tax_match else 0
    subtotal_cents = max(total_cents - tax_cents, 0)

    parsed_date: date | None = None
    iso_match = _RE_ISO_DATE.search(ocr_text)
    us_match = _RE_US_DATE.search(ocr_text)
    try:
        if iso_match:
            parsed_date = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        elif us_match:
            parsed_date = date(int(us_match.group(3)), int(us_match.group(1)), int(us_match.group(2)))
    except ValueError:
        parsed_date = None

    return {
        "filename": filename,
        "content_type": content_type,
        "vendor_name": vendor_name or None,
        "document_date": parsed_date.isoformat() if parsed_date else None,
        "subtotal_cents": subtotal_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
        "line_count": len(lines),
        "preview": "\n".join(lines[:8]),
    }


def suggest_category_from_rules(fields: dict[str, Any], ocr_text: str) -> CategorizationSuggestion:
    haystack = " ".join(
        [
            str(fields.get("vendor_name") or ""),
            str(fields.get("filename") or ""),
            ocr_text,
        ]
    ).lower()
    for vendor_keyword, category, account_code, confidence, rationale in VENDOR_RULES:
        if vendor_keyword in haystack:
            return CategorizationSuggestion(
                category=category,
                account_code=account_code,
                confidence=confidence,
                rationale=rationale,
                provider="rules",
                summary=f"{category} expense suggested from vendor and OCR pattern match.",
                raw_response={"matched_rule": vendor_keyword},
            )
    if any(token in haystack for token in ("hosting", "compute", "server", "ec2", "s3")):
        return CategorizationSuggestion(
            category="Infrastructure",
            account_code="5010",
            confidence=0.82,
            rationale="Infrastructure keywords were detected in the OCR text.",
            provider="rules",
            summary="Infrastructure spend suggested from receipt keywords.",
            raw_response={"matched_rule": "keyword:infrastructure"},
        )
    if any(token in haystack for token in ("voice", "sms", "phone", "calling")):
        return CategorizationSuggestion(
            category="Communications",
            account_code="5020",
            confidence=0.8,
            rationale="Communications keywords were detected in the OCR text.",
            provider="rules",
            summary="Communications spend suggested from receipt keywords.",
            raw_response={"matched_rule": "keyword:communications"},
        )
    return CategorizationSuggestion(
        category="Other",
        account_code="5099",
        confidence=0.55,
        rationale="No deterministic vendor rule matched; human review is required.",
        provider="rules",
        summary="Fallback categorization requires human review.",
        raw_response={"matched_rule": "fallback"},
    )


def requires_human_review(confidence: float) -> bool:
    return confidence < LOW_CONFIDENCE_THRESHOLD


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug or "artifact"


def _now() -> datetime:
    return datetime.now(UTC)


def _quarter(value: date | None) -> int | None:
    if value is None:
        return None
    return ((value.month - 1) // 3) + 1


def _decode_text(content: bytes) -> str | None:
    for encoding in ("utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def _run_command(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def extract_text_from_document(filename: str, content_type: str, content: bytes) -> tuple[str, str, bytes | None]:
    suffix = Path(filename).suffix.lower() or ".bin"
    if content_type.startswith("text/"):
        return "decoded", _decode_text(content) or "", None

    with tempfile.TemporaryDirectory(prefix="Adaptix-finance-") as tmpdir:
        source_path = Path(tmpdir) / f"source{suffix}"
        source_path.write_bytes(content)

        if suffix == ".pdf" and shutil.which("pdftotext"):
            text_path = Path(tmpdir) / "source.txt"
            _run_command(["pdftotext", str(source_path), str(text_path)])
            if text_path.exists():
                return "pdftotext", text_path.read_text(encoding="utf-8", errors="ignore"), None

        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".pdf"} and shutil.which("tesseract"):
            text_output = _run_command(["tesseract", str(source_path), "stdout"])
            if text_output is not None:
                return "tesseract", text_output, None

        if suffix == ".pdf" and shutil.which("ocrmypdf") and shutil.which("pdftotext"):
            normalized_path = Path(tmpdir) / "normalized.pdf"
            try:
                subprocess.run(
                    ["ocrmypdf", "--skip-text", str(source_path), str(normalized_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                text_path = Path(tmpdir) / "normalized.txt"
                subprocess.run(["pdftotext", str(normalized_path), str(text_path)], check=True, capture_output=True, text=True)
                normalized_bytes = normalized_path.read_bytes()
                return "ocrmypdf", text_path.read_text(encoding="utf-8", errors="ignore"), normalized_bytes
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass

    return "unavailable", "", None


def enrich_with_bedrock(fields: dict[str, Any], ocr_text: str, settings: Settings | None = None) -> CategorizationSuggestion | None:
    settings = settings or get_settings()
    model_id = getattr(settings, "bedrock_founder_finance_model_id", "") or ""
    if not model_id:
        return None

    prompt = (
        "You are assisting a founder finance ledger system. "
        "Return strict JSON with keys: category, account_code, confidence, rationale, summary.\n"
        f"Fields: {json.dumps(fields, ensure_ascii=False)}\n"
        f"OCR Text: {ocr_text[:5000]}"
    )
    region_name = getattr(settings, "bedrock_region", "") or settings.aws_region or "us-east-1"
    try:
        ai = AiService(bedrock_client=get_bedrock_client(region=region_name, model_id=model_id))
        response_text, _meta = ai.chat(
            system="Return strict JSON only with keys: category, account_code, confidence, rationale, summary.",
            user=prompt,
            max_tokens=400,
            temperature=0,
        )
    except BedrockClientError as exc:
        raise FounderFinanceProcessingError(str(exc)) from exc
    except RuntimeError as exc:
        raise FounderFinanceProcessingError("AI features are disabled") from exc

    raw_text = str(response_text or "")

    if not raw_text:
        raise FounderFinanceProcessingError("Bedrock response did not contain text content.")

    parsed_any = BedrockClient.parse_json_content(raw_text, expected="object")
    parsed = parsed_any if isinstance(parsed_any, dict) else {}
    return CategorizationSuggestion(
        category=str(parsed.get("category") or "Other"),
        account_code=str(parsed.get("account_code") or CATEGORY_ACCOUNT_MAP["Other"]),
        confidence=float(parsed.get("confidence") or 0.0),
        rationale=str(parsed.get("rationale") or "Bedrock enrichment completed without rationale."),
        provider="bedrock",
        summary=str(parsed.get("summary") or ""),
        raw_response=parsed,
    )


class FounderFinanceService:
    """Founder Finance business logic service.

    NOTE: This service has been migrated to use psycopg3 raw SQL queries
    instead of SQLAlchemy ORM. All methods are now async.

    MIGRATION COMPATIBILITY:
    - The constructor accepts an optional `db` parameter for backward compatibility
    - The `db` parameter is ignored; the service manages its own connections
    - All methods are now async and must be awaited
    """

    def __init__(self, db=None, settings: Settings | None = None) -> None:
        """Initialize founder finance service.

        Args:
            db: Legacy SQLAlchemy session parameter (ignored, kept for compatibility)
            settings: Settings object for configuration
        """
        # db parameter is ignored - we use psycopg3 connection pool instead
        self.settings = settings or get_settings()

    @tracer.start_as_current_span("founder_finance.ensure_chart_of_accounts")
    async def ensure_chart_of_accounts(self, tenant_id: uuid.UUID) -> None:
        """Ensure default chart of accounts exists for tenant."""
        async with acquire() as conn:
            async with managed_transaction(conn, query_owner="founder_finance.ensure_chart_of_accounts"):
                count = await ff_queries.ensure_chart_of_accounts(
                    conn,
                    tenant_id=tenant_id,
                    account_definitions=list(DEFAULT_ACCOUNT_DEFINITIONS),
                )
                logger.info(
                    "Ensured chart of accounts for tenant %s: created %d accounts",
                    tenant_id,
                    count,
                )

    async def _write_business_audit(
        self,
        conn,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None,
        details: dict[str, Any],
    ) -> None:
        """Write business audit event."""
        await ff_queries.create_business_audit_event(
            conn,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )

    async def _write_personal_audit(
        self,
        conn,
        tenant_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None,
        details: dict[str, Any],
    ) -> None:
        """Write personal tax audit event."""
        await ff_queries.create_personal_tax_audit_event(
            conn,
            tenant_id=tenant_id,
            owner_user_id=owner_user_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )

    async def _get_account(self, conn, tenant_id: uuid.UUID, code: str) -> dict[str, Any]:
        """Get account by code, raising error if not found."""
        account = await ff_queries.get_account_by_code(
            conn,
            tenant_id=tenant_id,
            code=code,
        )
        if account is None:
            raise FounderFinanceProcessingError(f"Account code {code} is not configured for tenant {tenant_id}.")
        return account

    async def _stripe_subscription_snapshot(self, conn, tenant_id: uuid.UUID) -> dict[str, Any]:
        """Get Stripe subscription snapshot for revenue calculation."""
        rows = await ff_queries.get_stripe_subscription_snapshot(
            conn,
            tenant_id=tenant_id,
        )
        active_count = 0
        mrr_cents = 0
        status_rows: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row.get("data") or {})
            status_rows.append(data)
            if data.get("status") == "active":
                active_count += 1
                mrr_cents += int(data.get("monthly_amount_cents") or 0)
        return {
            "active_subscriptions": active_count,
            "mrr_cents": mrr_cents,
            "subscriptions": status_rows[:20],
        }

    def _stripe_live_metrics(self) -> dict[str, Any]:
        """Get live Stripe metrics from Stripe API."""
        if not self.settings.stripe_secret_key:
            return {
                "configured": False,
                "revenue_cents": 0,
                "refund_count": 0,
                "refund_cents": 0,
                "dispute_count": 0,
                "dispute_cents": 0,
                "api_error": "stripe_not_configured",
                "invoice_points": [],
            }
        try:
            import stripe

            stripe.api_key = self.settings.stripe_secret_key
            invoices = stripe.Invoice.list(limit=100, status="paid")
            invoice_points: list[dict[str, Any]] = []
            revenue_cents = 0
            for invoice in getattr(invoices, "data", []) or []:
                created_ts = getattr(invoice, "created", None) or invoice.get("created")
                created_at = datetime.fromtimestamp(created_ts, tz=UTC) if created_ts else _now()
                amount_paid = int(getattr(invoice, "amount_paid", None) or invoice.get("amount_paid") or 0)
                revenue_cents += amount_paid
                invoice_points.append({
                    "created_at": created_at.isoformat(),
                    "amount_cents": amount_paid,
                })

            refunds = stripe.Refund.list(limit=100)
            refund_items = getattr(refunds, "data", []) or []
            refund_cents = sum(int(getattr(item, "amount", None) or item.get("amount") or 0) for item in refund_items)

            disputes = stripe.Dispute.list(limit=100)
            dispute_items = getattr(disputes, "data", []) or []
            dispute_cents = sum(int(getattr(item, "amount", None) or item.get("amount") or 0) for item in dispute_items)

            return {
                "configured": True,
                "revenue_cents": revenue_cents,
                "refund_count": len(refund_items),
                "refund_cents": refund_cents,
                "dispute_count": len(dispute_items),
                "dispute_cents": dispute_cents,
                "api_error": None,
                "invoice_points": invoice_points,
            }
        except Exception as exc:  # pragma: no cover - network/runtime variability
            return {
                "configured": True,
                "revenue_cents": 0,
                "refund_count": 0,
                "refund_cents": 0,
                "dispute_count": 0,
                "dispute_cents": 0,
                "api_error": str(exc),
                "invoice_points": [],
            }

    def _build_quarterly_posture(
        self,
        approved_transactions: list[dict[str, Any]],
        invoice_points: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build quarterly financial posture from transactions and invoices."""
        buckets: dict[str, dict[str, int]] = {}
        for point in invoice_points:
            created_at = datetime.fromisoformat(point["created_at"])
            key = f"{created_at.year}-Q{_quarter(created_at.date())}"
            buckets.setdefault(key, {"income_cents": 0, "expense_cents": 0})["income_cents"] += int(point["amount_cents"])
        for tx in approved_transactions:
            occurred_on = tx.get("occurred_on") or tx["created_at"].date() if isinstance(tx["created_at"], datetime) else date.fromisoformat(tx["created_at"])
            key = f"{occurred_on.year}-Q{_quarter(occurred_on)}"
            buckets.setdefault(key, {"income_cents": 0, "expense_cents": 0})["expense_cents"] += int(tx["amount_cents"])
        return [
            {
                "quarter": key,
                "income_cents": value["income_cents"],
                "expense_cents": value["expense_cents"],
                "reserve_estimate_cents": max(int((value["income_cents"] - value["expense_cents"]) * 0.27), 0),
            }
            for key, value in sorted(buckets.items(), reverse=True)[:4]
        ]

    def _build_anomalies(self, transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect anomalies in transactions."""
        anomalies: list[dict[str, Any]] = []
        high_value_pending = [tx for tx in transactions if tx["review_status"] != "approved" and tx["amount_cents"] >= 100000]
        if high_value_pending:
            anomalies.append(
                {
                    "label": "High-value pending review",
                    "detail": f"{len(high_value_pending)} transaction(s) over $1,000 are still pending review.",
                    "tone": "critical",
                }
            )
        seen: set[tuple[str, int, str]] = set()
        duplicate_count = 0
        for tx in transactions:
            occurred = (tx.get("occurred_on") or tx["created_at"].date() if isinstance(tx["created_at"], datetime) else date.fromisoformat(tx["created_at"])).isoformat()
            key = ((tx.get("vendor_name") or "unknown").lower(), int(tx["amount_cents"]), occurred)
            if key in seen:
                duplicate_count += 1
            else:
                seen.add(key)
        if duplicate_count:
            anomalies.append(
                {
                    "label": "Duplicate receipt candidates",
                    "detail": f"{duplicate_count} duplicate-looking transaction(s) detected by vendor/date/amount.",
                    "tone": "warning",
                }
            )
        return anomalies

    @tracer.start_as_current_span("founder_finance.business_dashboard")
    async def business_dashboard(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """Get business finance dashboard with all metrics."""
        async with acquire() as conn:
            async with managed_transaction(conn, query_owner="founder_finance.business_dashboard"):
                await self.ensure_chart_of_accounts(tenant_id)

                transactions = await ff_queries.list_business_finance_transactions(
                    conn,
                    tenant_id=tenant_id,
                )
                documents = await ff_queries.list_business_finance_documents(
                    conn,
                    tenant_id=tenant_id,
                )

                approved_transactions = [tx for tx in transactions if tx["review_status"] == "approved"]
                pending_transactions = [tx for tx in transactions if tx["review_status"] != "approved"]
                approved_expense_cents = sum(tx["amount_cents"] for tx in approved_transactions if tx["direction"] == "expense")
                pending_expense_cents = sum(tx["amount_cents"] for tx in pending_transactions if tx["direction"] == "expense")

                subscription_snapshot = await self._stripe_subscription_snapshot(conn, tenant_id)
                stripe_metrics = self._stripe_live_metrics()
                revenue_cents = int(stripe_metrics.get("revenue_cents") or 0)
                if revenue_cents == 0:
                    revenue_cents = int(subscription_snapshot["mrr_cents"])
                cash_posture_cents = revenue_cents - approved_expense_cents
                document_completeness_pct = int((len([tx for tx in transactions if tx.get("document_id")]) / len(transactions)) * 100) if transactions else 100

                category_totals: dict[str, int] = {}
                for tx in approved_transactions:
                    category = tx.get("category") or "Uncategorized"
                    category_totals[category] = category_totals.get(category, 0) + int(tx["amount_cents"])
                category_trends = [
                    {"category": category, "amount_cents": amount}
                    for category, amount in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
                ]

                latest_audit_events = await ff_queries.list_business_audit_events(
                    conn,
                    tenant_id=tenant_id,
                    limit=10,
                )
                quarterly_posture = self._build_quarterly_posture(approved_transactions, list(stripe_metrics.get("invoice_points") or []))
                tax_reserve_estimate_cents = max(int((revenue_cents - approved_expense_cents) * 0.27), 0)

                return {
                    "revenue_cents": revenue_cents,
                    "expenses_cents": approved_expense_cents,
                    "net_movement_cents": revenue_cents - approved_expense_cents,
                    "cash_posture_cents": cash_posture_cents,
                    "stripe": {
                        **subscription_snapshot,
                        **stripe_metrics,
                    },
                    "receivables_cents": 0,
                    "payables_cents": pending_expense_cents,
                    "uncategorized_count": len([tx for tx in pending_transactions if not tx.get("category")]),
                    "pending_review_count": len(pending_transactions),
                    "pending_review_cents": pending_expense_cents,
                    "document_completeness_pct": document_completeness_pct,
                    "document_count": len(documents),
                    "category_trends": category_trends,
                    "tax_reserve_estimate_cents": tax_reserve_estimate_cents,
                    "quarterly_posture": quarterly_posture,
                    "anomalies": self._build_anomalies(transactions),
                    "audit_stream": [
                        {
                            "action": event["action"],
                            "entity_type": event["entity_type"],
                            "details": event["details"],
                            "created_at": event["created_at"].isoformat() if isinstance(event["created_at"], datetime) else event["created_at"],
                        }
                        for event in latest_audit_events
                    ],
                }

    @tracer.start_as_current_span("founder_finance.list_business_transactions")
    async def list_business_transactions(self, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
        """List all business transactions with AI suggestions."""
        async with acquire() as conn:
            transactions = await ff_queries.list_business_finance_transactions(
                conn,
                tenant_id=tenant_id,
            )
            suggestion_rows = await ff_queries.list_business_finance_ai_suggestions(
                conn,
                tenant_id=tenant_id,
            )

            by_transaction_id: dict[str, dict[str, Any]] = {}
            for suggestion in suggestion_rows:
                if suggestion.get("transaction_id") and str(suggestion["transaction_id"]) not in by_transaction_id:
                    by_transaction_id[str(suggestion["transaction_id"])] = suggestion

            return [
                {
                    "id": str(tx["id"]),
                    "occurred_on": tx["occurred_on"].isoformat() if tx.get("occurred_on") else None,
                    "vendor_name": tx.get("vendor_name"),
                    "category": tx.get("category"),
                    "amount_cents": tx["amount_cents"],
                    "review_status": tx["review_status"],
                    "confidence_score": tx.get("confidence_score"),
                    "tax_deductible": tx.get("tax_deductible"),
                    "document_id": str(tx["document_id"]) if tx.get("document_id") else None,
                    "memo": tx.get("memo"),
                    "suggested_account_code": (
                        by_transaction_id[str(tx["id"])].get("suggested_account_code")
                        if str(tx["id"]) in by_transaction_id
                        else None
                    ),
                    "suggestion_rationale": (
                        by_transaction_id[str(tx["id"])].get("rationale")
                        if str(tx["id"]) in by_transaction_id
                        else None
                    ),
                }
                for tx in transactions
            ]

    def _build_business_s3_key(self, tenant_id: uuid.UUID, filename: str) -> str:
        ts = _now().strftime("%Y%m%dT%H%M%S")
        return f"founder-finance/business/{tenant_id}/documents/{ts}-{uuid.uuid4().hex}-{_safe_slug(filename)}"

    def _build_personal_s3_key(self, tenant_id: uuid.UUID, owner_user_id: uuid.UUID, tax_year: int, filename: str) -> str:
        ts = _now().strftime("%Y%m%dT%H%M%S")
        return f"founder-finance/personal/{tenant_id}/{owner_user_id}/{tax_year}/{ts}-{uuid.uuid4().hex}-{_safe_slug(filename)}"

    @tracer.start_as_current_span("founder_finance.upload_business_document")
    async def upload_business_document(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        """Upload a business finance document with OCR and AI categorization."""
        bucket = default_founder_finance_bucket()
        if not bucket:
            raise FounderFinanceConfigError("s3_bucket_founder_finance_docs_not_configured")

        async with acquire() as conn:
            async with managed_transaction(conn, query_owner="founder_finance.upload_business_document"):
                await self.ensure_chart_of_accounts(tenant_id)

                s3_key = self._build_business_s3_key(tenant_id, filename)
                put_bytes(bucket=bucket, key=s3_key, content=content, content_type=content_type)

                ocr_engine, ocr_text, normalized_bytes = extract_text_from_document(filename, content_type, content)
                parsed_fields = parse_receipt_fields(filename, content_type, ocr_text)
                deterministic = suggest_category_from_rules(parsed_fields, ocr_text)
                enrichment = None
                try:
                    enrichment = enrich_with_bedrock(parsed_fields, ocr_text, self.settings)
                except Exception:
                    enrichment = None
                final_suggestion = enrichment if enrichment and enrichment.confidence >= deterministic.confidence else deterministic
                review_status = "needs_human_review" if requires_human_review(final_suggestion.confidence) else "suggested"

                document = await ff_queries.create_business_finance_document(
                    conn,
                    tenant_id=tenant_id,
                    uploaded_by_user_id=actor_user_id,
                    storage_bucket=bucket,
                    storage_key=s3_key,
                    normalized_bucket=bucket if normalized_bytes else None,
                    normalized_key=f"{s3_key}.normalized.pdf" if normalized_bytes else None,
                    original_filename=filename,
                    content_type=content_type,
                    byte_size=len(content),
                    source_type="receipt",
                    currency="USD",
                    document_date=parsed_fields.get("document_date"),
                    vendor_name=parsed_fields.get("vendor_name"),
                    subtotal_cents=int(parsed_fields.get("subtotal_cents") or 0),
                    tax_cents=int(parsed_fields.get("tax_cents") or 0),
                    total_cents=int(parsed_fields.get("total_cents") or 0),
                    ocr_status="complete" if ocr_text else ("unavailable" if ocr_engine == "unavailable" else "empty"),
                    ocr_engine=ocr_engine,
                    ocr_text=ocr_text or None,
                    extracted_fields=parsed_fields,
                    ai_summary=final_suggestion.summary,
                    ai_confidence=final_suggestion.confidence,
                    review_status=review_status,
                )

                if normalized_bytes:
                    put_bytes(
                        bucket=bucket,
                        key=str(document["normalized_key"]),
                        content=normalized_bytes,
                        content_type="application/pdf",
                    )

                transaction = await ff_queries.create_business_finance_transaction(
                    conn,
                    tenant_id=tenant_id,
                    document_id=document["id"],
                    occurred_on=document.get("document_date"),
                    vendor_name=document.get("vendor_name"),
                    direction="expense",
                    source_type="receipt",
                    category=final_suggestion.category,
                    memo=final_suggestion.summary or parsed_fields.get("preview") or f"Imported from {filename}",
                    amount_cents=document.get("total_cents") or document.get("subtotal_cents") or 0,
                    currency=document.get("currency") or "USD",
                    review_status=review_status,
                    confidence_score=final_suggestion.confidence,
                    tax_deductible=True,
                )

                suggestion = await ff_queries.create_business_finance_ai_suggestion(
                    conn,
                    tenant_id=tenant_id,
                    document_id=document["id"],
                    transaction_id=transaction["id"],
                    provider=final_suggestion.provider,
                    suggestion_type="categorization",
                    suggested_category=final_suggestion.category,
                    suggested_account_code=final_suggestion.account_code,
                    confidence_score=final_suggestion.confidence,
                    rationale=final_suggestion.rationale,
                    status="pending_review",
                    raw_response=final_suggestion.raw_response or {},
                )

                await self._write_business_audit(
                    conn,
                    tenant_id,
                    actor_user_id,
                    "receipt_uploaded",
                    "business_finance_document",
                    document["id"],
                    {
                        "transaction_id": str(transaction["id"]),
                        "ocr_engine": ocr_engine,
                        "review_status": review_status,
                        "provider": final_suggestion.provider,
                    },
                )

                return {
                    "document_id": str(document["id"]),
                    "transaction_id": str(transaction["id"]),
                    "review_status": review_status,
                    "ocr_status": document.get("ocr_status"),
                    "suggestion": {
                        "category": final_suggestion.category,
                        "account_code": final_suggestion.account_code,
                        "confidence": final_suggestion.confidence,
                        "rationale": final_suggestion.rationale,
                        "provider": final_suggestion.provider,
                    },
                }

    @tracer.start_as_current_span("founder_finance.approve_business_transaction")
    async def approve_business_transaction(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        chosen_category: str,
        chosen_account_code: str,
        note: str | None,
    ) -> dict[str, Any]:
        """Approve a business transaction and create journal entries."""
        async with acquire() as conn:
            async with managed_transaction(conn, query_owner="founder_finance.approve_business_transaction"):
                await self.ensure_chart_of_accounts(tenant_id)

                transaction = await ff_queries.get_business_finance_transaction_by_id(
                    conn,
                    tenant_id=tenant_id,
                    transaction_id=transaction_id,
                )
                if transaction is None:
                    raise FounderFinanceProcessingError("business_transaction_not_found")

                account = await self._get_account(conn, tenant_id, chosen_account_code)
                cash_account_code = "2000" if transaction["source_type"] == "invoice" else "1000"
                balancing_account = await self._get_account(conn, tenant_id, cash_account_code)

                occurred_on = transaction.get("occurred_on") or _now().date()
                journal_entry = await ff_queries.create_business_finance_journal_entry(
                    conn,
                    tenant_id=tenant_id,
                    entry_number=f"JE-{_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                    occurred_at=datetime.combine(occurred_on, datetime.min.time(), tzinfo=UTC).isoformat(),
                    memo=note or transaction.get("memo"),
                    source_transaction_id=transaction["id"],
                    status="posted",
                    posted_by_user_id=actor_user_id,
                )

                await ff_queries.create_business_finance_journal_lines(
                    conn,
                    tenant_id=tenant_id,
                    journal_entry_id=journal_entry["id"],
                    lines=[
                        {
                            "account_id": account["id"],
                            "line_type": "debit",
                            "amount_cents": transaction["amount_cents"],
                            "memo": note,
                            "document_id": transaction.get("document_id"),
                        },
                        {
                            "account_id": balancing_account["id"],
                            "line_type": "credit",
                            "amount_cents": transaction["amount_cents"],
                            "memo": note,
                            "document_id": transaction.get("document_id"),
                        },
                    ],
                )

                updated_tx = await ff_queries.update_business_finance_transaction(
                    conn,
                    tenant_id=tenant_id,
                    transaction_id=transaction_id,
                    updates={
                        "category": chosen_category,
                        "review_status": "approved",
                        "approved_by_user_id": actor_user_id,
                        "approved_at": _now().isoformat(),
                        "linked_journal_entry_id": journal_entry["id"],
                    },
                )

                await ff_queries.create_categorization_decision(
                    conn,
                    tenant_id=tenant_id,
                    transaction_id=transaction_id,
                    document_id=transaction.get("document_id"),
                    decided_by_user_id=actor_user_id,
                    chosen_category=chosen_category,
                    chosen_account_code=chosen_account_code,
                    confidence_score=transaction.get("confidence_score"),
                    decision_source="human",
                    note=note,
                )

                await ff_queries.update_ai_suggestion_status(
                    conn,
                    tenant_id=tenant_id,
                    transaction_id=transaction_id,
                    status="accepted",
                )

                await self._write_business_audit(
                    conn,
                    tenant_id,
                    actor_user_id,
                    "transaction_approved",
                    "business_finance_transaction",
                    transaction_id,
                    {"account_code": chosen_account_code, "category": chosen_category, "journal_entry_id": str(journal_entry["id"])},
                )

                return {
                    "transaction_id": str(transaction_id),
                    "journal_entry_id": str(journal_entry["id"]),
                    "review_status": "approved",
                }

    @tracer.start_as_current_span("founder_finance.business_tax_summary")
    async def business_tax_summary(self, tenant_id: uuid.UUID, tax_year: int) -> dict[str, Any]:
        """Generate business tax summary for a given year."""
        async with acquire() as conn:
            async with managed_transaction(conn, query_owner="founder_finance.business_tax_summary"):
                transactions = await ff_queries.list_business_finance_transactions(
                    conn,
                    tenant_id=tenant_id,
                )
                documents = await ff_queries.list_business_finance_documents(
                    conn,
                    tenant_id=tenant_id,
                )

                year_transactions = [
                    tx
                    for tx in transactions
                    if (tx.get("occurred_on") or tx["created_at"].date() if isinstance(tx["created_at"], datetime) else date.fromisoformat(tx["created_at"])).year == tax_year
                ]
                approved = [tx for tx in year_transactions if tx["review_status"] == "approved"]
                unresolved = [tx for tx in year_transactions if tx["review_status"] != "approved"]
                missing_docs = [tx for tx in year_transactions if tx["review_status"] == "approved" and not tx.get("document_id")]

                deductible_totals: dict[str, int] = {}
                for tx in approved:
                    if not tx.get("tax_deductible"):
                        continue
                    deductible_totals[tx.get("category") or "Uncategorized"] = deductible_totals.get(tx.get("category") or "Uncategorized", 0) + int(tx["amount_cents"])

                stripe_snapshot = await self._stripe_subscription_snapshot(conn, tenant_id)
                live_revenue_cents = self._stripe_live_metrics().get("revenue_cents") or 0
                gross_income_cents = int(live_revenue_cents or stripe_snapshot["mrr_cents"] * 12)
                deductible_expenses_cents = sum(int(tx["amount_cents"]) for tx in approved if tx.get("tax_deductible"))
                net_income_cents = gross_income_cents - deductible_expenses_cents
                reserve_estimate_cents = max(int(net_income_cents * 0.27), 0)

                summary = {
                    "tax_year": tax_year,
                    "gross_income_cents": gross_income_cents,
                    "deductible_expenses_cents": deductible_expenses_cents,
                    "net_income_cents": net_income_cents,
                    "reserve_estimate_cents": reserve_estimate_cents,
                    "unresolved_transaction_count": len(unresolved),
                    "unresolved_transaction_cents": sum(int(tx["amount_cents"]) for tx in unresolved),
                    "missing_document_count": len(missing_docs),
                    "document_coverage_pct": int(((len(approved) - len(missing_docs)) / len(approved)) * 100) if approved else 100,
                    "deductions_by_category": [
                        {"category": category, "amount_cents": amount}
                        for category, amount in sorted(deductible_totals.items(), key=lambda item: item[1], reverse=True)
                    ],
                    "income_by_source": [
                        {"source": "Stripe recurring", "amount_cents": int(stripe_snapshot["mrr_cents"] * 12)},
                        {"source": "Paid invoices (live)", "amount_cents": int(live_revenue_cents)},
                    ],
                    "workpaper_ready": len(unresolved) == 0 and len(missing_docs) == 0,
                    "readiness_label": "Ready for accountant handoff" if len(unresolved) == 0 and len(missing_docs) == 0 else "Review required",
                    "supporting_document_count": len([
                        doc for doc in documents
                        if (doc.get("document_date") or doc["created_at"].date() if isinstance(doc["created_at"], datetime) else date.fromisoformat(doc["created_at"])).year == tax_year
                    ]),
                }

                existing_snapshot = await ff_queries.get_tax_snapshot(
                    conn,
                    tenant_id=tenant_id,
                    tax_year=tax_year,
                    snapshot_kind="tax_summary",
                )

                if existing_snapshot is not None:
                    await ff_queries.update_tax_snapshot(
                        conn,
                        snapshot_id=existing_snapshot["id"],
                        tenant_id=tenant_id,
                        gross_income_cents=summary["gross_income_cents"],
                        deductible_expenses_cents=summary["deductible_expenses_cents"],
                        net_income_cents=summary["net_income_cents"],
                        reserve_estimate_cents=summary["reserve_estimate_cents"],
                        unresolved_transaction_count=summary["unresolved_transaction_count"],
                        missing_document_count=summary["missing_document_count"],
                        data=summary,
                    )
                else:
                    await ff_queries.create_tax_snapshot(
                        conn,
                        tenant_id=tenant_id,
                        tax_year=tax_year,
                        tax_quarter=None,
                        snapshot_kind="tax_summary",
                        gross_income_cents=summary["gross_income_cents"],
                        deductible_expenses_cents=summary["deductible_expenses_cents"],
                        net_income_cents=summary["net_income_cents"],
                        reserve_estimate_cents=summary["reserve_estimate_cents"],
                        unresolved_transaction_count=summary["unresolved_transaction_count"],
                        missing_document_count=summary["missing_document_count"],
                        data=summary,
                    )

                return summary

    def _build_ledger_csv(self, approved_transactions: list[dict[str, Any]], tax_year: int) -> bytes:
        """Build CSV ledger export."""
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=["transaction_id", "occurred_on", "vendor_name", "category", "amount_cents", "review_status", "document_id"],
        )
        writer.writeheader()
        for tx in approved_transactions:
            occurred_on = tx.get("occurred_on") or tx["created_at"].date() if isinstance(tx["created_at"], datetime) else date.fromisoformat(tx["created_at"])
            if occurred_on.year != tax_year:
                continue
            writer.writerow(
                {
                    "transaction_id": str(tx["id"]),
                    "occurred_on": occurred_on.isoformat(),
                    "vendor_name": tx.get("vendor_name") or "",
                    "category": tx.get("category") or "",
                    "amount_cents": tx["amount_cents"],
                    "review_status": tx["review_status"],
                    "document_id": str(tx["document_id"]) if tx.get("document_id") else "",
                }
            )
        return buffer.getvalue().encode("utf-8")

    def _build_json_review_package(self, tax_summary: dict[str, Any], transactions: list[dict[str, Any]]) -> bytes:
        """Build JSON review package."""
        return json.dumps({"tax_summary": tax_summary, "transactions": transactions}, indent=2, ensure_ascii=False).encode("utf-8")

    def _build_summary_pdf(self, tax_summary: dict[str, Any]) -> bytes:
        """Build PDF summary."""
        output = io.BytesIO()
        pdf = canvas.Canvas(output, pagesize=LETTER)
        pdf.setTitle(f"Adaptix Founder Tax Summary {tax_summary['tax_year']}")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(54, 760, f"Founder Business Tax Summary — {tax_summary['tax_year']}")
        pdf.setFont("Helvetica", 10)
        rows = [
            ("Gross income", tax_summary["gross_income_cents"]),
            ("Deductible expenses", tax_summary["deductible_expenses_cents"]),
            ("Net income", tax_summary["net_income_cents"]),
            ("Quarterly reserve estimate", tax_summary["reserve_estimate_cents"]),
            ("Unresolved transactions", tax_summary["unresolved_transaction_count"]),
            ("Missing supporting documents", tax_summary["missing_document_count"]),
        ]
        y = 724
        for label, value in rows:
            pretty = f"${value / 100:,.2f}" if isinstance(value, int) and label not in {"Unresolved transactions", "Missing supporting documents"} else str(value)
            pdf.drawString(54, y, label)
            pdf.drawRightString(550, y, pretty)
            y -= 18
        y -= 6
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(54, y, "Deductions by category")
        pdf.setFont("Helvetica", 10)
        y -= 20
        for item in tax_summary.get("deductions_by_category", [])[:12]:
            pdf.drawString(68, y, str(item["category"]))
            pdf.drawRightString(550, y, f"${item['amount_cents'] / 100:,.2f}")
            y -= 16
            if y < 80:
                pdf.showPage()
                y = 760
        pdf.save()
        return output.getvalue()

    async def _collect_source_documents(self, conn, tenant_id: uuid.UUID, tax_year: int) -> list[dict[str, Any]]:
        """Collect source documents for a tax year."""
        docs = await ff_queries.list_business_finance_documents(
            conn,
            tenant_id=tenant_id,
        )
        return [
            doc for doc in docs
            if (doc.get("document_date") or doc["created_at"].date() if isinstance(doc["created_at"], datetime) else date.fromisoformat(doc["created_at"])).year == tax_year
        ]

    def _build_source_bundle(self, documents: list[dict[str, Any]]) -> bytes:
        """Build ZIP bundle of source documents."""
        output = io.BytesIO()
        s3 = boto3.client("s3")
        with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            manifest: list[dict[str, Any]] = []
            for doc in documents:
                archive_name = f"source-documents/{_safe_slug(doc['original_filename'])}"
                try:
                    response = s3.get_object(Bucket=doc["storage_bucket"], Key=doc["storage_key"])
                    archive.writestr(archive_name, response["Body"].read())
                    manifest.append({"document_id": str(doc["id"]), "filename": doc["original_filename"], "status": "included"})
                except Exception as exc:  # pragma: no cover - AWS variability
                    manifest.append({"document_id": str(doc["id"]), "filename": doc["original_filename"], "status": f"missing:{exc}"})
            archive.writestr("manifest.json", json.dumps(manifest, indent=2).encode("utf-8"))
        return output.getvalue()

    @tracer.start_as_current_span("founder_finance.run_business_export")
    async def run_business_export(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        export_kind: str,
        tax_year: int,
    ) -> dict[str, Any]:
        """Run a business export and generate artifacts."""
        async with acquire() as conn:
            async with managed_transaction(conn, query_owner="founder_finance.run_business_export"):
                transactions = await ff_queries.list_business_finance_transactions(
                    conn,
                    tenant_id=tenant_id,
                )
                approved_transactions = [
                    tx
                    for tx in transactions
                    if tx["review_status"] == "approved"
                    and (tx.get("occurred_on") or tx["created_at"].date() if isinstance(tx["created_at"], datetime) else date.fromisoformat(tx["created_at"])).year == tax_year
                ]

                tax_summary = await self.business_tax_summary(tenant_id, tax_year)
                payload_bytes: bytes
                content_type: str
                extension: str

                if export_kind in {"ledger_csv", "expense_csv"}:
                    payload_bytes = self._build_ledger_csv(approved_transactions, tax_year)
                    content_type = "text/csv"
                    extension = "csv"
                elif export_kind == "json_review":
                    all_transactions = await self.list_business_transactions(tenant_id)
                    payload_bytes = self._build_json_review_package(tax_summary, all_transactions)
                    content_type = "application/json"
                    extension = "json"
                elif export_kind == "summary_pdf":
                    payload_bytes = self._build_summary_pdf(tax_summary)
                    content_type = "application/pdf"
                    extension = "pdf"
                elif export_kind in {"source_bundle", "accountant_bundle", "tax_workpaper"}:
                    documents = await self._collect_source_documents(conn, tenant_id, tax_year)
                    ledger_bytes = self._build_ledger_csv(approved_transactions, tax_year)
                    summary_pdf = self._build_summary_pdf(tax_summary)
                    all_transactions = await self.list_business_transactions(tenant_id)
                    review_json = self._build_json_review_package(tax_summary, all_transactions)
                    source_bundle = self._build_source_bundle(documents)
                    output = io.BytesIO()
                    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                        archive.writestr("ledger.csv", ledger_bytes)
                        archive.writestr("summary.pdf", summary_pdf)
                        archive.writestr("review.json", review_json)
                        archive.writestr("source-documents.zip", source_bundle)
                    payload_bytes = output.getvalue()
                    content_type = "application/zip"
                    extension = "zip"
                else:
                    raise FounderFinanceProcessingError(f"Unsupported export kind: {export_kind}")

                exports_bucket = default_exports_bucket()
                if not exports_bucket:
                    raise FounderFinanceConfigError("s3_bucket_exports_not_configured")
                artifact_key = f"founder-finance/exports/{tenant_id}/{tax_year}/{export_kind}-{uuid.uuid4().hex}.{extension}"
                put_bytes(bucket=exports_bucket, key=artifact_key, content=payload_bytes, content_type=content_type)

                export_run = await ff_queries.create_export_run(
                    conn,
                    tenant_id=tenant_id,
                    requested_by_user_id=actor_user_id,
                    export_kind=export_kind,
                    export_scope="business",
                    tax_year=tax_year,
                    status="completed",
                    artifact_bucket=exports_bucket,
                    artifact_key=artifact_key,
                    artifact_count=1,
                    note=f"Generated {export_kind} package for tax year {tax_year}.",
                )

                await self._write_business_audit(
                    conn,
                    tenant_id,
                    actor_user_id,
                    "export_generated",
                    "business_finance_export_run",
                    export_run["id"],
                    {"export_kind": export_kind, "tax_year": tax_year, "artifact_key": artifact_key},
                )

                return {
                    "export_run_id": str(export_run["id"]),
                    "status": export_run["status"],
                    "artifact_bucket": export_run["artifact_bucket"],
                    "artifact_key": export_run["artifact_key"],
                    "download_url": presign_get(bucket=exports_bucket, key=artifact_key, expires_seconds=300),
                }

    @tracer.start_as_current_span("founder_finance.get_export_run")
    async def get_export_run(self, tenant_id: uuid.UUID, export_run_id: uuid.UUID) -> dict[str, Any]:
        """Get export run details."""
        async with acquire() as conn:
            export_run = await ff_queries.get_export_run_by_id(
                conn,
                tenant_id=tenant_id,
                export_run_id=export_run_id,
            )
            if export_run is None:
                raise FounderFinanceProcessingError("export_run_not_found")
            download_url = None
            if export_run.get("artifact_bucket") and export_run.get("artifact_key"):
                download_url = presign_get(bucket=export_run["artifact_bucket"], key=export_run["artifact_key"], expires_seconds=300)
            return {
                "id": str(export_run["id"]),
                "status": export_run["status"],
                "export_kind": export_run["export_kind"],
                "tax_year": export_run.get("tax_year"),
                "download_url": download_url,
                "created_at": export_run["created_at"].isoformat() if isinstance(export_run["created_at"], datetime) else export_run["created_at"],
            }

    async def list_personal_documents(
        self,
        *,
        tenant_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        query: str | None = None,
        tax_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """List personal tax documents."""
        async with acquire() as conn:
            documents = await ff_queries.list_personal_tax_documents(
                conn,
                tenant_id=tenant_id,
                owner_user_id=owner_user_id,
                tax_year=tax_year,
            )

            query_norm = (query or "").strip().lower()
            if not query_norm:
                return [
                    {
                        "id": str(document["id"]),
                        "tax_year": document["tax_year"],
                        "document_type": document["document_type"],
                        "review_status": document["review_status"],
                        "ocr_status": document["ocr_status"],
                        "original_filename": document["original_filename"],
                        "summary_text": document.get("summary_text"),
                        "ai_confidence": document.get("ai_confidence"),
                        "created_at": document["created_at"].isoformat() if isinstance(document["created_at"], datetime) else document["created_at"],
                    }
                    for document in documents
                ]

            filtered: list[dict[str, Any]] = []
            for document in documents:
                haystack = " ".join(
                    [
                        document["original_filename"],
                        document["document_type"],
                        document.get("summary_text") or "",
                    ]
                ).lower()
                if query_norm in haystack:
                    filtered.append({
                        "id": str(document["id"]),
                        "tax_year": document["tax_year"],
                        "document_type": document["document_type"],
                        "review_status": document["review_status"],
                        "ocr_status": document["ocr_status"],
                        "original_filename": document["original_filename"],
                        "summary_text": document.get("summary_text"),
                        "ai_confidence": document.get("ai_confidence"),
                        "created_at": document["created_at"].isoformat() if isinstance(document["created_at"], datetime) else document["created_at"],
                    })
            return filtered

    async def upload_personal_tax_document(
        self,
        *,
        tenant_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        tax_year: int,
        document_type: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        """Upload a personal tax document."""
        ensure_personal_vault_access(actor_user_id, owner_user_id)
        bucket = default_founder_personal_tax_bucket()
        if not bucket:
            raise FounderFinanceConfigError("s3_bucket_founder_personal_tax_not_configured")

        async with acquire() as conn:
            async with managed_transaction(conn, query_owner="founder_finance.upload_personal_tax_document"):
                kms_key_id = getattr(self.settings, "s3_kms_key_founder_personal_tax", "") or None
                s3_key = self._build_personal_s3_key(tenant_id, owner_user_id, tax_year, filename)
                put_bytes(
                    bucket=bucket,
                    key=s3_key,
                    content=content,
                    content_type=content_type,
                    server_side_encryption="aws:kms" if kms_key_id else None,
                    kms_key_id=kms_key_id,
                    metadata={"domain": "personal_tax", "owner_user_id": str(owner_user_id)},
                )

                ocr_engine, ocr_text, normalized_bytes = extract_text_from_document(filename, content_type, content)
                summary = None
                confidence = None
                try:
                    enrichment = enrich_with_bedrock(
                        {
                            "document_type": document_type,
                            "tax_year": tax_year,
                            "filename": filename,
                        },
                        ocr_text,
                        self.settings,
                    )
                    if enrichment:
                        summary = enrichment.summary or enrichment.rationale
                        confidence = enrichment.confidence
                except Exception:
                    summary = None
                if not summary and ocr_text:
                    summary = " ".join(ocr_text.split())[:600]

                document = await ff_queries.create_personal_tax_document(
                    conn,
                    tenant_id=tenant_id,
                    owner_user_id=owner_user_id,
                    tax_year=tax_year,
                    document_type=document_type,
                    review_status="ready" if summary else "pending_review",
                    ocr_status="complete" if ocr_text else ("unavailable" if ocr_engine == "unavailable" else "empty"),
                    storage_bucket=bucket,
                    storage_key=s3_key,
                    normalized_bucket=bucket if normalized_bytes else None,
                    normalized_key=f"{s3_key}.normalized.pdf" if normalized_bytes else None,
                    original_filename=filename,
                    content_type=content_type,
                    byte_size=len(content),
                    ocr_text=ocr_text or None,
                    summary_text=summary,
                    ai_confidence=confidence,
                    metadata_json={"ocr_engine": ocr_engine},
                )

                if normalized_bytes:
                    put_bytes(
                        bucket=bucket,
                        key=str(document["normalized_key"]),
                        content=normalized_bytes,
                        content_type="application/pdf",
                        server_side_encryption="aws:kms" if kms_key_id else None,
                        kms_key_id=kms_key_id,
                        metadata={"domain": "personal_tax", "owner_user_id": str(owner_user_id)},
                    )

                await self._write_personal_audit(
                    conn,
                    tenant_id,
                    owner_user_id,
                    actor_user_id,
                    "personal_tax_document_uploaded",
                    "personal_tax_document",
                    document["id"],
                    {"tax_year": tax_year, "document_type": document_type, "ocr_engine": ocr_engine},
                )

                return {
                    "document_id": str(document["id"]),
                    "review_status": document["review_status"],
                    "ocr_status": document["ocr_status"],
                    "summary_text": document.get("summary_text"),
                }

    async def personal_tax_download_url(
        self,
        *,
        tenant_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get download URL for personal tax document."""
        ensure_personal_vault_access(actor_user_id, owner_user_id)
        async with acquire() as conn:
            document = await ff_queries.get_personal_tax_document_by_id(
                conn,
                tenant_id=tenant_id,
                owner_user_id=owner_user_id,
                document_id=document_id,
            )
            if document is None:
                raise FounderFinanceProcessingError("personal_tax_document_not_found")
            return {
                "document_id": str(document["id"]),
                "download_url": presign_get(bucket=document["storage_bucket"], key=document["storage_key"], expires_seconds=300),
                "filename": document["original_filename"],
            }
