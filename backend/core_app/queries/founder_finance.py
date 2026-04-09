"""Founder Finance domain SQL queries.

Covers business finance tracking, receipt processing, tax summaries, and
personal tax document management for founders.

Tables:
- business_finance_accounts
- business_finance_documents
- business_finance_transactions
- business_finance_ai_suggestions
- business_finance_categorization_decisions
- business_finance_journal_entries
- business_finance_journal_lines
- business_finance_tax_snapshots
- business_finance_export_runs
- business_finance_audit_events
- personal_tax_documents
- personal_tax_audit_events
"""

from __future__ import annotations

import uuid
from typing import Any

import psycopg

from core_app.db.executor import execute, executemany, fetchall, fetchone, fetchval

_OWNER = "queries.founder_finance"


# ---------------------------------------------------------------------------
# Business Finance Accounts
# ---------------------------------------------------------------------------

async def ensure_chart_of_accounts(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    account_definitions: list[dict[str, Any]],
) -> int:
    """Ensure default chart of accounts exists for tenant.

    Returns number of accounts created.
    """
    # Get existing account codes
    existing = await fetchall(
        conn,
        """
        SELECT code
        FROM business_finance_accounts
        WHERE tenant_id = %(tenant_id)s
          AND deleted_at IS NULL
        """,
        {"tenant_id": tenant_id},
        query_owner=f"{_OWNER}.ensure_chart_of_accounts.get_existing",
        tenant_id=str(tenant_id),
    )
    existing_codes = {row["code"] for row in existing}

    # Filter to only new accounts
    new_accounts = [
        defn for defn in account_definitions
        if defn["code"] not in existing_codes
    ]

    if not new_accounts:
        return 0

    # Bulk insert new accounts
    params_seq = [
        {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "code": defn["code"],
            "name": defn["name"],
            "classification": defn["classification"],
            "normal_balance": defn["normal_balance"],
            "tax_category": defn.get("tax_category"),
            "is_active": True,
            "is_system": True,
            "description": defn.get("description"),
            "version": 1,
        }
        for defn in new_accounts
    ]

    return await executemany(
        conn,
        """
        INSERT INTO business_finance_accounts (
            id, tenant_id, code, name, classification, normal_balance,
            tax_category, is_active, is_system, description, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(code)s, %(name)s, %(classification)s, %(normal_balance)s,
            %(tax_category)s, %(is_active)s, %(is_system)s, %(description)s, %(version)s
        )
        """,
        params_seq,
        query_owner=f"{_OWNER}.ensure_chart_of_accounts.insert",
        tenant_id=str(tenant_id),
    )


async def get_account_by_code(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    code: str,
) -> dict[str, Any] | None:
    """Get account by code."""
    return await fetchone(
        conn,
        """
        SELECT
            id, tenant_id, code, name, classification, normal_balance,
            tax_category, is_active, is_system, description,
            created_at, updated_at, version
        FROM business_finance_accounts
        WHERE tenant_id = %(tenant_id)s
          AND code = %(code)s
          AND deleted_at IS NULL
        """,
        {"tenant_id": tenant_id, "code": code},
        query_owner=f"{_OWNER}.get_account_by_code",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Business Finance Documents
# ---------------------------------------------------------------------------

async def create_business_finance_document(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID | None,
    storage_bucket: str,
    storage_key: str,
    normalized_bucket: str | None,
    normalized_key: str | None,
    original_filename: str,
    content_type: str,
    byte_size: int,
    source_type: str,
    currency: str,
    document_date: str | None,
    vendor_name: str | None,
    subtotal_cents: int,
    tax_cents: int,
    total_cents: int,
    ocr_status: str,
    ocr_engine: str | None,
    ocr_text: str | None,
    extracted_fields: dict[str, Any],
    ai_summary: str | None,
    ai_confidence: float | None,
    review_status: str,
) -> dict[str, Any]:
    """Create a business finance document."""
    document_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO business_finance_documents (
            id, tenant_id, uploaded_by_user_id, storage_bucket, storage_key,
            normalized_bucket, normalized_key, original_filename, content_type,
            byte_size, source_type, currency, document_date, vendor_name,
            subtotal_cents, tax_cents, total_cents, ocr_status, ocr_engine,
            ocr_text, extracted_fields, ai_summary, ai_confidence, review_status, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(uploaded_by_user_id)s, %(storage_bucket)s, %(storage_key)s,
            %(normalized_bucket)s, %(normalized_key)s, %(original_filename)s, %(content_type)s,
            %(byte_size)s, %(source_type)s, %(currency)s, %(document_date)s::date, %(vendor_name)s,
            %(subtotal_cents)s, %(tax_cents)s, %(total_cents)s, %(ocr_status)s, %(ocr_engine)s,
            %(ocr_text)s, %(extracted_fields)s::jsonb, %(ai_summary)s, %(ai_confidence)s, %(review_status)s, 1
        )
        RETURNING
            id, tenant_id, uploaded_by_user_id, storage_bucket, storage_key,
            normalized_bucket, normalized_key, original_filename, content_type,
            byte_size, source_type, currency, document_date, vendor_name,
            subtotal_cents, tax_cents, total_cents, ocr_status, ocr_engine,
            ai_summary, ai_confidence, review_status,
            created_at, updated_at, version
        """,
        {
            "id": document_id,
            "tenant_id": tenant_id,
            "uploaded_by_user_id": uploaded_by_user_id,
            "storage_bucket": storage_bucket,
            "storage_key": storage_key,
            "normalized_bucket": normalized_bucket,
            "normalized_key": normalized_key,
            "original_filename": original_filename,
            "content_type": content_type,
            "byte_size": byte_size,
            "source_type": source_type,
            "currency": currency,
            "document_date": document_date,
            "vendor_name": vendor_name,
            "subtotal_cents": subtotal_cents,
            "tax_cents": tax_cents,
            "total_cents": total_cents,
            "ocr_status": ocr_status,
            "ocr_engine": ocr_engine,
            "ocr_text": ocr_text,
            "extracted_fields": extracted_fields,
            "ai_summary": ai_summary,
            "ai_confidence": ai_confidence,
            "review_status": review_status,
        },
        query_owner=f"{_OWNER}.create_business_finance_document",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO business_finance_documents returned no row for id={document_id}")
    return row


async def list_business_finance_documents(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """List all business finance documents for a tenant."""
    return await fetchall(
        conn,
        """
        SELECT
            id, tenant_id, uploaded_by_user_id, storage_bucket, storage_key,
            normalized_bucket, normalized_key, original_filename, content_type,
            byte_size, source_type, currency, document_date, vendor_name,
            subtotal_cents, tax_cents, total_cents, ocr_status, ocr_engine,
            ai_summary, ai_confidence, review_status,
            created_at, updated_at, version
        FROM business_finance_documents
        WHERE tenant_id = %(tenant_id)s
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        {"tenant_id": tenant_id},
        query_owner=f"{_OWNER}.list_business_finance_documents",
        tenant_id=str(tenant_id),
    )


async def get_business_finance_document_by_id(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Get a business finance document by ID."""
    return await fetchone(
        conn,
        """
        SELECT
            id, tenant_id, uploaded_by_user_id, storage_bucket, storage_key,
            normalized_bucket, normalized_key, original_filename, content_type,
            byte_size, source_type, currency, document_date, vendor_name,
            subtotal_cents, tax_cents, total_cents, ocr_status, ocr_engine,
            ai_summary, ai_confidence, review_status,
            created_at, updated_at, version
        FROM business_finance_documents
        WHERE tenant_id = %(tenant_id)s
          AND id = %(document_id)s
          AND deleted_at IS NULL
        """,
        {"tenant_id": tenant_id, "document_id": document_id},
        query_owner=f"{_OWNER}.get_business_finance_document_by_id",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Business Finance Transactions
# ---------------------------------------------------------------------------

async def create_business_finance_transaction(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID | None,
    occurred_on: str | None,
    vendor_name: str | None,
    direction: str,
    source_type: str,
    category: str | None,
    memo: str | None,
    amount_cents: int,
    currency: str,
    review_status: str,
    confidence_score: float | None,
    tax_deductible: bool,
) -> dict[str, Any]:
    """Create a business finance transaction."""
    transaction_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO business_finance_transactions (
            id, tenant_id, document_id, occurred_on, vendor_name, direction,
            source_type, category, memo, amount_cents, currency, review_status,
            confidence_score, tax_deductible, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(document_id)s, %(occurred_on)s::date, %(vendor_name)s, %(direction)s,
            %(source_type)s, %(category)s, %(memo)s, %(amount_cents)s, %(currency)s, %(review_status)s,
            %(confidence_score)s, %(tax_deductible)s, 1
        )
        RETURNING
            id, tenant_id, document_id, occurred_on, vendor_name, direction,
            source_type, category, memo, amount_cents, currency, review_status,
            confidence_score, tax_deductible, approved_by_user_id, approved_at,
            created_at, updated_at, version
        """,
        {
            "id": transaction_id,
            "tenant_id": tenant_id,
            "document_id": document_id,
            "occurred_on": occurred_on,
            "vendor_name": vendor_name,
            "direction": direction,
            "source_type": source_type,
            "category": category,
            "memo": memo,
            "amount_cents": amount_cents,
            "currency": currency,
            "review_status": review_status,
            "confidence_score": confidence_score,
            "tax_deductible": tax_deductible,
        },
        query_owner=f"{_OWNER}.create_business_finance_transaction",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO business_finance_transactions returned no row for id={transaction_id}")
    return row


async def list_business_finance_transactions(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """List all business finance transactions for a tenant."""
    return await fetchall(
        conn,
        """
        SELECT
            id, tenant_id, document_id, occurred_on, vendor_name, direction,
            source_type, category, memo, amount_cents, currency, review_status,
            confidence_score, tax_deductible, approved_by_user_id, approved_at,
            linked_journal_entry_id,
            created_at, updated_at, version
        FROM business_finance_transactions
        WHERE tenant_id = %(tenant_id)s
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        {"tenant_id": tenant_id},
        query_owner=f"{_OWNER}.list_business_finance_transactions",
        tenant_id=str(tenant_id),
    )


async def get_business_finance_transaction_by_id(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Get a business finance transaction by ID."""
    return await fetchone(
        conn,
        """
        SELECT
            id, tenant_id, document_id, occurred_on, vendor_name, direction,
            source_type, category, memo, amount_cents, currency, review_status,
            confidence_score, tax_deductible, approved_by_user_id, approved_at,
            linked_journal_entry_id,
            created_at, updated_at, version
        FROM business_finance_transactions
        WHERE tenant_id = %(tenant_id)s
          AND id = %(transaction_id)s
          AND deleted_at IS NULL
        """,
        {"tenant_id": tenant_id, "transaction_id": transaction_id},
        query_owner=f"{_OWNER}.get_business_finance_transaction_by_id",
        tenant_id=str(tenant_id),
    )


async def update_business_finance_transaction(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    transaction_id: uuid.UUID,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Update a business finance transaction."""
    # Build dynamic SET clause
    set_parts = [f"{key} = %({key})s" for key in updates.keys()]
    set_clause = ", ".join(set_parts)

    params = {**updates, "transaction_id": transaction_id, "tenant_id": tenant_id}

    sql = f"""
        UPDATE business_finance_transactions
        SET {set_clause},
            updated_at = NOW()
        WHERE id = %(transaction_id)s
          AND tenant_id = %(tenant_id)s
          AND deleted_at IS NULL
        RETURNING
            id, tenant_id, document_id, occurred_on, vendor_name, direction,
            source_type, category, memo, amount_cents, currency, review_status,
            confidence_score, tax_deductible, approved_by_user_id, approved_at,
            linked_journal_entry_id,
            created_at, updated_at, version
    """

    return await fetchone(
        conn,
        sql,
        params,
        query_owner=f"{_OWNER}.update_business_finance_transaction",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Business Finance AI Suggestions
# ---------------------------------------------------------------------------

async def create_business_finance_ai_suggestion(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    transaction_id: uuid.UUID | None,
    provider: str,
    suggestion_type: str,
    suggested_category: str | None,
    suggested_account_code: str | None,
    confidence_score: float,
    rationale: str | None,
    status: str,
    raw_response: dict[str, Any],
) -> dict[str, Any]:
    """Create a business finance AI suggestion."""
    suggestion_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO business_finance_ai_suggestions (
            id, tenant_id, document_id, transaction_id, provider, suggestion_type,
            suggested_category, suggested_account_code, confidence_score, rationale,
            status, raw_response, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(document_id)s, %(transaction_id)s, %(provider)s, %(suggestion_type)s,
            %(suggested_category)s, %(suggested_account_code)s, %(confidence_score)s, %(rationale)s,
            %(status)s, %(raw_response)s::jsonb, 1
        )
        RETURNING
            id, tenant_id, document_id, transaction_id, provider, suggestion_type,
            suggested_category, suggested_account_code, confidence_score, rationale,
            status, created_at, updated_at, version
        """,
        {
            "id": suggestion_id,
            "tenant_id": tenant_id,
            "document_id": document_id,
            "transaction_id": transaction_id,
            "provider": provider,
            "suggestion_type": suggestion_type,
            "suggested_category": suggested_category,
            "suggested_account_code": suggested_account_code,
            "confidence_score": confidence_score,
            "rationale": rationale,
            "status": status,
            "raw_response": raw_response,
        },
        query_owner=f"{_OWNER}.create_business_finance_ai_suggestion",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO business_finance_ai_suggestions returned no row for id={suggestion_id}")
    return row


async def list_business_finance_ai_suggestions(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """List all AI suggestions for a tenant."""
    return await fetchall(
        conn,
        """
        SELECT
            id, tenant_id, document_id, transaction_id, provider, suggestion_type,
            suggested_category, suggested_account_code, confidence_score, rationale,
            status, created_at, updated_at, version
        FROM business_finance_ai_suggestions
        WHERE tenant_id = %(tenant_id)s
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        {"tenant_id": tenant_id},
        query_owner=f"{_OWNER}.list_business_finance_ai_suggestions",
        tenant_id=str(tenant_id),
    )


async def update_ai_suggestion_status(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    transaction_id: uuid.UUID,
    status: str,
) -> int:
    """Update AI suggestion status by transaction ID."""
    return await execute(
        conn,
        """
        UPDATE business_finance_ai_suggestions
        SET status = %(status)s,
            updated_at = NOW()
        WHERE tenant_id = %(tenant_id)s
          AND transaction_id = %(transaction_id)s
        """,
        {"tenant_id": tenant_id, "transaction_id": transaction_id, "status": status},
        query_owner=f"{_OWNER}.update_ai_suggestion_status",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Business Finance Journal Entries
# ---------------------------------------------------------------------------

async def create_business_finance_journal_entry(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    entry_number: str,
    occurred_at: str,
    memo: str | None,
    source_transaction_id: uuid.UUID | None,
    status: str,
    posted_by_user_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Create a business finance journal entry."""
    entry_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO business_finance_journal_entries (
            id, tenant_id, entry_number, occurred_at, memo,
            source_transaction_id, status, posted_by_user_id, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(entry_number)s, %(occurred_at)s::timestamp, %(memo)s,
            %(source_transaction_id)s, %(status)s, %(posted_by_user_id)s, 1
        )
        RETURNING
            id, tenant_id, entry_number, occurred_at, memo,
            source_transaction_id, status, posted_by_user_id,
            created_at, updated_at, version
        """,
        {
            "id": entry_id,
            "tenant_id": tenant_id,
            "entry_number": entry_number,
            "occurred_at": occurred_at,
            "memo": memo,
            "source_transaction_id": source_transaction_id,
            "status": status,
            "posted_by_user_id": posted_by_user_id,
        },
        query_owner=f"{_OWNER}.create_business_finance_journal_entry",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO business_finance_journal_entries returned no row for id={entry_id}")
    return row


async def create_business_finance_journal_lines(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    journal_entry_id: uuid.UUID,
    lines: list[dict[str, Any]],
) -> int:
    """Create multiple journal lines for an entry."""
    params_seq = [
        {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "journal_entry_id": journal_entry_id,
            "account_id": line["account_id"],
            "line_type": line["line_type"],
            "amount_cents": line["amount_cents"],
            "memo": line.get("memo"),
            "document_id": line.get("document_id"),
            "version": 1,
        }
        for line in lines
    ]

    return await executemany(
        conn,
        """
        INSERT INTO business_finance_journal_lines (
            id, tenant_id, journal_entry_id, account_id, line_type,
            amount_cents, memo, document_id, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(journal_entry_id)s, %(account_id)s, %(line_type)s,
            %(amount_cents)s, %(memo)s, %(document_id)s, %(version)s
        )
        """,
        params_seq,
        query_owner=f"{_OWNER}.create_business_finance_journal_lines",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Business Finance Categorization Decisions
# ---------------------------------------------------------------------------

async def create_categorization_decision(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    transaction_id: uuid.UUID,
    document_id: uuid.UUID | None,
    decided_by_user_id: uuid.UUID,
    chosen_category: str,
    chosen_account_code: str,
    confidence_score: float | None,
    decision_source: str,
    note: str | None,
) -> dict[str, Any]:
    """Create a categorization decision."""
    decision_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO business_finance_categorization_decisions (
            id, tenant_id, transaction_id, document_id, decided_by_user_id,
            chosen_category, chosen_account_code, confidence_score,
            decision_source, note, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(transaction_id)s, %(document_id)s, %(decided_by_user_id)s,
            %(chosen_category)s, %(chosen_account_code)s, %(confidence_score)s,
            %(decision_source)s, %(note)s, 1
        )
        RETURNING
            id, tenant_id, transaction_id, document_id, decided_by_user_id,
            chosen_category, chosen_account_code, confidence_score,
            decision_source, note,
            created_at, updated_at, version
        """,
        {
            "id": decision_id,
            "tenant_id": tenant_id,
            "transaction_id": transaction_id,
            "document_id": document_id,
            "decided_by_user_id": decided_by_user_id,
            "chosen_category": chosen_category,
            "chosen_account_code": chosen_account_code,
            "confidence_score": confidence_score,
            "decision_source": decision_source,
            "note": note,
        },
        query_owner=f"{_OWNER}.create_categorization_decision",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO business_finance_categorization_decisions returned no row for id={decision_id}")
    return row


# ---------------------------------------------------------------------------
# Business Finance Tax Snapshots
# ---------------------------------------------------------------------------

async def get_tax_snapshot(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    tax_year: int,
    snapshot_kind: str,
) -> dict[str, Any] | None:
    """Get the most recent tax snapshot."""
    return await fetchone(
        conn,
        """
        SELECT
            id, tenant_id, tax_year, tax_quarter, snapshot_kind,
            gross_income_cents, deductible_expenses_cents, net_income_cents,
            reserve_estimate_cents, unresolved_transaction_count,
            missing_document_count, data,
            created_at, updated_at, version
        FROM business_finance_tax_snapshots
        WHERE tenant_id = %(tenant_id)s
          AND tax_year = %(tax_year)s
          AND snapshot_kind = %(snapshot_kind)s
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "tax_year": tax_year, "snapshot_kind": snapshot_kind},
        query_owner=f"{_OWNER}.get_tax_snapshot",
        tenant_id=str(tenant_id),
    )


async def create_tax_snapshot(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    tax_year: int,
    tax_quarter: int | None,
    snapshot_kind: str,
    gross_income_cents: int,
    deductible_expenses_cents: int,
    net_income_cents: int,
    reserve_estimate_cents: int,
    unresolved_transaction_count: int,
    missing_document_count: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Create a tax snapshot."""
    snapshot_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO business_finance_tax_snapshots (
            id, tenant_id, tax_year, tax_quarter, snapshot_kind,
            gross_income_cents, deductible_expenses_cents, net_income_cents,
            reserve_estimate_cents, unresolved_transaction_count,
            missing_document_count, data, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(tax_year)s, %(tax_quarter)s, %(snapshot_kind)s,
            %(gross_income_cents)s, %(deductible_expenses_cents)s, %(net_income_cents)s,
            %(reserve_estimate_cents)s, %(unresolved_transaction_count)s,
            %(missing_document_count)s, %(data)s::jsonb, 1
        )
        RETURNING
            id, tenant_id, tax_year, tax_quarter, snapshot_kind,
            gross_income_cents, deductible_expenses_cents, net_income_cents,
            reserve_estimate_cents, unresolved_transaction_count,
            missing_document_count, data,
            created_at, updated_at, version
        """,
        {
            "id": snapshot_id,
            "tenant_id": tenant_id,
            "tax_year": tax_year,
            "tax_quarter": tax_quarter,
            "snapshot_kind": snapshot_kind,
            "gross_income_cents": gross_income_cents,
            "deductible_expenses_cents": deductible_expenses_cents,
            "net_income_cents": net_income_cents,
            "reserve_estimate_cents": reserve_estimate_cents,
            "unresolved_transaction_count": unresolved_transaction_count,
            "missing_document_count": missing_document_count,
            "data": data,
        },
        query_owner=f"{_OWNER}.create_tax_snapshot",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO business_finance_tax_snapshots returned no row for id={snapshot_id}")
    return row


async def update_tax_snapshot(
    conn: psycopg.AsyncConnection,
    *,
    snapshot_id: uuid.UUID,
    tenant_id: uuid.UUID,
    gross_income_cents: int,
    deductible_expenses_cents: int,
    net_income_cents: int,
    reserve_estimate_cents: int,
    unresolved_transaction_count: int,
    missing_document_count: int,
    data: dict[str, Any],
) -> dict[str, Any] | None:
    """Update a tax snapshot."""
    return await fetchone(
        conn,
        """
        UPDATE business_finance_tax_snapshots
        SET gross_income_cents = %(gross_income_cents)s,
            deductible_expenses_cents = %(deductible_expenses_cents)s,
            net_income_cents = %(net_income_cents)s,
            reserve_estimate_cents = %(reserve_estimate_cents)s,
            unresolved_transaction_count = %(unresolved_transaction_count)s,
            missing_document_count = %(missing_document_count)s,
            data = %(data)s::jsonb,
            updated_at = NOW()
        WHERE id = %(snapshot_id)s
          AND tenant_id = %(tenant_id)s
          AND deleted_at IS NULL
        RETURNING
            id, tenant_id, tax_year, tax_quarter, snapshot_kind,
            gross_income_cents, deductible_expenses_cents, net_income_cents,
            reserve_estimate_cents, unresolved_transaction_count,
            missing_document_count, data,
            created_at, updated_at, version
        """,
        {
            "snapshot_id": snapshot_id,
            "tenant_id": tenant_id,
            "gross_income_cents": gross_income_cents,
            "deductible_expenses_cents": deductible_expenses_cents,
            "net_income_cents": net_income_cents,
            "reserve_estimate_cents": reserve_estimate_cents,
            "unresolved_transaction_count": unresolved_transaction_count,
            "missing_document_count": missing_document_count,
            "data": data,
        },
        query_owner=f"{_OWNER}.update_tax_snapshot",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Business Finance Export Runs
# ---------------------------------------------------------------------------

async def create_export_run(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
    export_kind: str,
    export_scope: str,
    tax_year: int | None,
    status: str,
    artifact_bucket: str | None,
    artifact_key: str | None,
    artifact_count: int,
    note: str | None,
) -> dict[str, Any]:
    """Create an export run."""
    export_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO business_finance_export_runs (
            id, tenant_id, requested_by_user_id, export_kind, export_scope,
            tax_year, status, artifact_bucket, artifact_key, artifact_count,
            note, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(requested_by_user_id)s, %(export_kind)s, %(export_scope)s,
            %(tax_year)s, %(status)s, %(artifact_bucket)s, %(artifact_key)s, %(artifact_count)s,
            %(note)s, 1
        )
        RETURNING
            id, tenant_id, requested_by_user_id, export_kind, export_scope,
            tax_year, status, artifact_bucket, artifact_key, artifact_count,
            note, created_at, updated_at, version
        """,
        {
            "id": export_id,
            "tenant_id": tenant_id,
            "requested_by_user_id": requested_by_user_id,
            "export_kind": export_kind,
            "export_scope": export_scope,
            "tax_year": tax_year,
            "status": status,
            "artifact_bucket": artifact_bucket,
            "artifact_key": artifact_key,
            "artifact_count": artifact_count,
            "note": note,
        },
        query_owner=f"{_OWNER}.create_export_run",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO business_finance_export_runs returned no row for id={export_id}")
    return row


async def get_export_run_by_id(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    export_run_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Get an export run by ID."""
    return await fetchone(
        conn,
        """
        SELECT
            id, tenant_id, requested_by_user_id, export_kind, export_scope,
            tax_year, status, artifact_bucket, artifact_key, artifact_count,
            note, created_at, updated_at, version
        FROM business_finance_export_runs
        WHERE tenant_id = %(tenant_id)s
          AND id = %(export_run_id)s
          AND deleted_at IS NULL
        """,
        {"tenant_id": tenant_id, "export_run_id": export_run_id},
        query_owner=f"{_OWNER}.get_export_run_by_id",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Business Finance Audit Events
# ---------------------------------------------------------------------------

async def create_business_audit_event(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    details: dict[str, Any],
) -> dict[str, Any]:
    """Create a business finance audit event."""
    event_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO business_finance_audit_events (
            id, tenant_id, actor_user_id, domain, action, entity_type, entity_id, details
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(actor_user_id)s, 'business_finance', %(action)s,
            %(entity_type)s, %(entity_id)s, %(details)s::jsonb
        )
        RETURNING
            id, tenant_id, actor_user_id, domain, action, entity_type, entity_id, details, created_at
        """,
        {
            "id": event_id,
            "tenant_id": tenant_id,
            "actor_user_id": actor_user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
        },
        query_owner=f"{_OWNER}.create_business_audit_event",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO business_finance_audit_events returned no row for id={event_id}")
    return row


async def list_business_audit_events(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """List recent business finance audit events."""
    return await fetchall(
        conn,
        """
        SELECT
            id, tenant_id, actor_user_id, domain, action, entity_type, entity_id, details, created_at
        FROM business_finance_audit_events
        WHERE tenant_id = %(tenant_id)s
        ORDER BY created_at DESC
        LIMIT %(limit)s
        """,
        {"tenant_id": tenant_id, "limit": limit},
        query_owner=f"{_OWNER}.list_business_audit_events",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Subscription data (from tenant_subscriptions table)
# ---------------------------------------------------------------------------

async def get_stripe_subscription_snapshot(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Get subscription data for revenue calculation."""
    return await fetchall(
        conn,
        """
        SELECT data, created_at
        FROM tenant_subscriptions
        WHERE tenant_id = %(tenant_id)s
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        {"tenant_id": tenant_id},
        query_owner=f"{_OWNER}.get_stripe_subscription_snapshot",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Personal Tax Documents
# ---------------------------------------------------------------------------

async def create_personal_tax_document(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    tax_year: int,
    document_type: str,
    review_status: str,
    ocr_status: str,
    storage_bucket: str,
    storage_key: str,
    normalized_bucket: str | None,
    normalized_key: str | None,
    original_filename: str,
    content_type: str,
    byte_size: int,
    ocr_text: str | None,
    summary_text: str | None,
    ai_confidence: float | None,
    metadata_json: dict[str, Any],
) -> dict[str, Any]:
    """Create a personal tax document."""
    document_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO personal_tax_documents (
            id, tenant_id, owner_user_id, tax_year, document_type, review_status,
            ocr_status, storage_bucket, storage_key, normalized_bucket, normalized_key,
            original_filename, content_type, byte_size, ocr_text, summary_text,
            ai_confidence, metadata_json, version
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(owner_user_id)s, %(tax_year)s, %(document_type)s, %(review_status)s,
            %(ocr_status)s, %(storage_bucket)s, %(storage_key)s, %(normalized_bucket)s, %(normalized_key)s,
            %(original_filename)s, %(content_type)s, %(byte_size)s, %(ocr_text)s, %(summary_text)s,
            %(ai_confidence)s, %(metadata_json)s::jsonb, 1
        )
        RETURNING
            id, tenant_id, owner_user_id, tax_year, document_type, review_status,
            ocr_status, storage_bucket, storage_key, normalized_bucket, normalized_key,
            original_filename, content_type, byte_size, summary_text,
            ai_confidence, created_at, updated_at, version
        """,
        {
            "id": document_id,
            "tenant_id": tenant_id,
            "owner_user_id": owner_user_id,
            "tax_year": tax_year,
            "document_type": document_type,
            "review_status": review_status,
            "ocr_status": ocr_status,
            "storage_bucket": storage_bucket,
            "storage_key": storage_key,
            "normalized_bucket": normalized_bucket,
            "normalized_key": normalized_key,
            "original_filename": original_filename,
            "content_type": content_type,
            "byte_size": byte_size,
            "ocr_text": ocr_text,
            "summary_text": summary_text,
            "ai_confidence": ai_confidence,
            "metadata_json": metadata_json,
        },
        query_owner=f"{_OWNER}.create_personal_tax_document",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO personal_tax_documents returned no row for id={document_id}")
    return row


async def list_personal_tax_documents(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    tax_year: int | None = None,
) -> list[dict[str, Any]]:
    """List personal tax documents."""
    if tax_year is not None:
        sql = """
        SELECT
            id, tenant_id, owner_user_id, tax_year, document_type, review_status,
            ocr_status, original_filename, summary_text, ai_confidence,
            created_at, updated_at, version
        FROM personal_tax_documents
        WHERE tenant_id = %(tenant_id)s
          AND owner_user_id = %(owner_user_id)s
          AND tax_year = %(tax_year)s
          AND deleted_at IS NULL
        ORDER BY tax_year DESC, created_at DESC
        """
        params = {"tenant_id": tenant_id, "owner_user_id": owner_user_id, "tax_year": tax_year}
    else:
        sql = """
        SELECT
            id, tenant_id, owner_user_id, tax_year, document_type, review_status,
            ocr_status, original_filename, summary_text, ai_confidence,
            created_at, updated_at, version
        FROM personal_tax_documents
        WHERE tenant_id = %(tenant_id)s
          AND owner_user_id = %(owner_user_id)s
          AND deleted_at IS NULL
        ORDER BY tax_year DESC, created_at DESC
        """
        params = {"tenant_id": tenant_id, "owner_user_id": owner_user_id}

    return await fetchall(
        conn,
        sql,
        params,
        query_owner=f"{_OWNER}.list_personal_tax_documents",
        tenant_id=str(tenant_id),
    )


async def get_personal_tax_document_by_id(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    document_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Get a personal tax document by ID."""
    return await fetchone(
        conn,
        """
        SELECT
            id, tenant_id, owner_user_id, tax_year, document_type, review_status,
            ocr_status, storage_bucket, storage_key, normalized_bucket, normalized_key,
            original_filename, content_type, byte_size, summary_text,
            ai_confidence, created_at, updated_at, version
        FROM personal_tax_documents
        WHERE tenant_id = %(tenant_id)s
          AND owner_user_id = %(owner_user_id)s
          AND id = %(document_id)s
          AND deleted_at IS NULL
        """,
        {"tenant_id": tenant_id, "owner_user_id": owner_user_id, "document_id": document_id},
        query_owner=f"{_OWNER}.get_personal_tax_document_by_id",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Personal Tax Audit Events
# ---------------------------------------------------------------------------

async def create_personal_tax_audit_event(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    details: dict[str, Any],
) -> dict[str, Any]:
    """Create a personal tax audit event."""
    event_id = uuid.uuid4()
    row = await fetchone(
        conn,
        """
        INSERT INTO personal_tax_audit_events (
            id, tenant_id, owner_user_id, actor_user_id, action,
            entity_type, entity_id, details
        )
        VALUES (
            %(id)s, %(tenant_id)s, %(owner_user_id)s, %(actor_user_id)s, %(action)s,
            %(entity_type)s, %(entity_id)s, %(details)s::jsonb
        )
        RETURNING
            id, tenant_id, owner_user_id, actor_user_id, action,
            entity_type, entity_id, details, created_at
        """,
        {
            "id": event_id,
            "tenant_id": tenant_id,
            "owner_user_id": owner_user_id,
            "actor_user_id": actor_user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
        },
        query_owner=f"{_OWNER}.create_personal_tax_audit_event",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT INTO personal_tax_audit_events returned no row for id={event_id}")
    return row
