"""
Project X — Database Schema Validator
======================================
Connects to a PostgreSQL database and validates that all expected tables,
columns, indexes, constraints, and partitions exist and match the schema
defined in project_x_schema_complete.md (v6).

Usage:
    python validate_schema.py

You will be prompted for connection credentials interactively.
"""

import getpass
import sys
from collections import defaultdict

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 not installed. Install it with:")
    print("  pip install psycopg2-binary")
    sys.exit(1)


# ---------------------------------------------------------------------------
# EXPECTED SCHEMA DEFINITION (from project_x_schema_complete.md v6)
# ---------------------------------------------------------------------------

# Format: table_name -> { column_name: expected_type_prefix }
# Types are lowercase prefixes — the validator checks that the actual
# PostgreSQL type STARTS WITH the expected prefix, so "varchar" matches
# "character varying", "uuid" matches "uuid", etc.

TYPE_MAP = {
    "uuid": "uuid",
    "varchar": "character varying",
    "text": "text",
    "boolean": "boolean",
    "timestamptz": "timestamp with time zone",
    "timestamp with time zone": "timestamp with time zone",
    "date": "date",
    "smallint": "smallint",
    "integer": "integer",
    "numeric": "numeric",
    "inet": "inet",
    "jsonb": "jsonb",
}


def t(type_key):
    """Resolve a short type key to the expected PostgreSQL type prefix."""
    return TYPE_MAP.get(type_key, type_key)


EXPECTED_TABLES = {
    # ── Account Domain ──
    "account": {
        "id": t("uuid"),
        "phone": t("varchar"),
        "phone_verified": t("boolean"),
        "email": t("varchar"),
        "email_verified": t("boolean"),
        "full_name": t("varchar"),
        "date_of_birth": t("date"),
        "gender": t("varchar"),
        "photo_s3_key": t("text"),
        "photo_uploaded_at": t("timestamptz"),
        "status": t("varchar"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
        "last_login_at": t("timestamptz"),
        "deleted_at": t("timestamptz"),
    },
    "account_address": {
        "id": t("uuid"),
        "account_id": t("uuid"),
        "address_type": t("varchar"),
        "address_line_1": t("varchar"),
        "address_line_2": t("varchar"),
        "landmark": t("varchar"),
        "city": t("varchar"),
        "district": t("varchar"),
        "state": t("varchar"),
        "pincode": t("varchar"),
        "country": t("varchar"),
        "is_same_as_current": t("boolean"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "account_pan": {
        "id": t("uuid"),
        "account_id": t("uuid"),
        "pan_number": t("text"),
        "name_on_pan": t("varchar"),
        "is_verified": t("boolean"),
        "verified_at": t("timestamptz"),
        "verification_source": t("varchar"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    # ── Auth Domain ──
    "account_otp_session": {
        "id": t("uuid"),
        "phone": t("varchar"),
        "otp_hash": t("text"),
        "purpose": t("varchar"),
        "attempts": t("smallint"),
        "max_attempts": t("smallint"),
        "expires_at": t("timestamptz"),
        "verified_at": t("timestamptz"),
        "verified_expires_at": t("timestamptz"),
        "consumed_at": t("timestamptz"),
        "created_at": t("timestamptz"),
        "ip_address": t("inet"),
        "user_agent": t("text"),
    },
    "account_auth_token": {
        "id": t("uuid"),
        "account_id": t("uuid"),
        "jti": t("uuid"),
        "token_type": t("varchar"),
        "active_profile_id": t("uuid"),
        "device_name": t("varchar"),
        "ip_address": t("inet"),
        "user_agent": t("text"),
        "expires_at": t("timestamptz"),
        "revoked_at": t("timestamptz"),
        "revoke_reason": t("varchar"),
        "created_at": t("timestamptz"),
        "last_used_at": t("timestamptz"),
    },
    # ── Profile Domain ──
    "profile": {
        "id": t("uuid"),
        "account_id": t("uuid"),
        "profile_type": t("varchar"),
        "is_active": t("boolean"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    # ── Nominee & Access Domain ──
    "account_nominee": {
        "id": t("uuid"),
        "primary_account_id": t("uuid"),
        "added_by_account_id": t("uuid"),
        "full_name": t("varchar"),
        "relationship": t("varchar"),
        "phone": t("varchar"),
        "email": t("varchar"),
        "share_percentage": t("numeric"),
        "status": t("varchar"),
        "linked_account_id": t("uuid"),
        "linked_at": t("timestamptz"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "account_nominee_scope": {
        "id": t("uuid"),
        "account_nominee_id": t("uuid"),
        "added_by_account_id": t("uuid"),
        "container_id": t("uuid"),
        "permission": t("varchar"),
        "is_active": t("boolean"),
        "is_visible": t("boolean"),
        "visibility_triggered_at": t("timestamptz"),
        "visibility_trigger_source": t("varchar"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "profile_access": {
        "id": t("uuid"),
        "accessor_profile_id": t("uuid"),
        "primary_profile_id": t("uuid"),
        "status": t("varchar"),
        "granted_at": t("timestamptz"),
        "revoked_at": t("timestamptz"),
        "revoke_reason": t("text"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "profile_access_scope": {
        "id": t("uuid"),
        "profile_access_id": t("uuid"),
        "container_id": t("uuid"),
        "permission": t("varchar"),
        "source_nominee_scope_id": t("uuid"),
        "is_visible": t("boolean"),
        "visibility_triggered_at": t("timestamptz"),
        "visibility_trigger_source": t("varchar"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    # ── Asset Registry Domain ──
    "asset_container": {
        "id": t("uuid"),
        "account_id": t("uuid"),
        "added_by_account_id": t("uuid"),
        "container_type": t("varchar"),
        "institution_name": t("varchar"),
        "approximate_value": t("numeric"),
        "notes": t("text"),
        "is_active": t("boolean"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_bank_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "account_number_encrypted": t("text"),
        "account_number_masked": t("varchar"),
        "account_type": t("varchar"),
        "ifsc_code": t("varchar"),
        "branch_name": t("varchar"),
        "city": t("varchar"),
        "state": t("varchar"),
        "maturity_date": t("date"),
        "interest_rate": t("numeric"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_demat_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "dp_id": t("varchar"),
        "client_id_encrypted": t("text"),
        "client_id_masked": t("varchar"),
        "depository": t("varchar"),
        "broker_name": t("varchar"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_mutual_fund_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "folio_number_encrypted": t("text"),
        "folio_number_masked": t("varchar"),
        "amc_name": t("varchar"),
        "rta_name": t("varchar"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_retirement_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "account_type": t("varchar"),
        "reference_number_encrypted": t("text"),
        "reference_number_masked": t("varchar"),
        "employer_name": t("varchar"),
        "fund_manager": t("varchar"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_insurance_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "policy_number_encrypted": t("text"),
        "policy_number_masked": t("varchar"),
        "policy_type": t("varchar"),
        "sum_assured": t("numeric"),
        "premium_amount": t("numeric"),
        "premium_frequency": t("varchar"),
        "policy_start_date": t("date"),
        "maturity_date": t("date"),
        "is_active_policy": t("boolean"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_real_estate_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "property_type": t("varchar"),
        "address": t("text"),
        "city": t("varchar"),
        "state": t("varchar"),
        "pincode": t("varchar"),
        "registration_number_encrypted": t("text"),
        "registration_number_masked": t("varchar"),
        "co_owner_name": t("varchar"),
        "ownership_percentage": t("numeric"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_loan_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "loan_type": t("varchar"),
        "loan_account_encrypted": t("text"),
        "loan_account_masked": t("varchar"),
        "outstanding_amount": t("numeric"),
        "emi_amount": t("numeric"),
        "emi_frequency": t("varchar"),
        "loan_start_date": t("date"),
        "loan_end_date": t("date"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_business_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "business_type": t("varchar"),
        "business_name": t("varchar"),
        "ownership_percentage": t("numeric"),
        "cin_encrypted": t("text"),
        "cin_masked": t("varchar"),
        "registered_address": t("text"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_govt_savings_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "scheme_type": t("varchar"),
        "account_number_encrypted": t("text"),
        "account_number_masked": t("varchar"),
        "post_office_branch": t("varchar"),
        "maturity_date": t("date"),
        "interest_rate": t("numeric"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_crypto_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "custody_type": t("varchar"),
        "exchange_name": t("varchar"),
        "registered_email_encrypted": t("text"),
        "registered_email_masked": t("varchar"),
        "wallet_address": t("varchar"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_receivable_detail": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "receivable_type": t("varchar"),
        "counterparty_name": t("varchar"),
        "counterparty_contact": t("varchar"),
        "expected_amount": t("numeric"),
        "due_date": t("date"),
        "description": t("text"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    "asset_document": {
        "id": t("uuid"),
        "container_id": t("uuid"),
        "account_id": t("uuid"),
        "added_by_account_id": t("uuid"),
        "document_type": t("varchar"),
        "s3_key": t("text"),
        "file_name_hash": t("text"),
        "file_size_bytes": t("integer"),
        "mime_type": t("varchar"),
        "is_active": t("boolean"),
        "created_at": t("timestamptz"),
    },
    # ── Inactivity Engine Domain ──
    "account_inactivity_state": {
        "id": t("uuid"),
        "account_id": t("uuid"),
        "current_state": t("varchar"),
        "last_active_at": t("timestamptz"),
        "reminder_sent_at": t("timestamptz"),
        "escalation_sent_at": t("timestamptz"),
        "trigger_initiated_at": t("timestamptz"),
        "hold_started_at": t("timestamptz"),
        "hold_expires_at": t("timestamptz"),
        "released_at": t("timestamptz"),
        "cancelled_at": t("timestamptz"),
        "reminder_count": t("smallint"),
        "created_at": t("timestamptz"),
        "updated_at": t("timestamptz"),
    },
    # ── Audit Domain ──
    "audit_log": {
        "id": t("uuid"),
        "account_id": t("uuid"),
        "actor_account_id": t("uuid"),
        "actor_type": t("varchar"),
        "profile_id": t("uuid"),
        "event_type": t("varchar"),
        "event_domain": t("varchar"),
        "entity_type": t("varchar"),
        "entity_id": t("uuid"),
        "ip_address": t("inet"),
        "user_agent": t("text"),
        "metadata": t("jsonb"),
        "status": t("varchar"),
        "failure_reason": t("text"),
        "created_at": t("timestamptz"),
    },
    "audit_resource_access": {
        "id": t("uuid"),
        "account_id": t("uuid"),
        "actor_account_id": t("uuid"),
        "actor_type": t("varchar"),
        "entity_type": t("varchar"),
        "entity_id": t("uuid"),
        "access_type": t("varchar"),
        "first_accessed_at": t("timestamptz"),
        "ip_address": t("inet"),
        "user_agent": t("text"),
    },
}

# Expected indexes: table_name -> [index_name, ...]
EXPECTED_INDEXES = {
    "account_otp_session": ["idx_otp_phone_purpose"],
    "account_auth_token": ["idx_auth_token_account", "idx_auth_token_jti"],
    "profile": ["idx_profile_account"],
    "account_nominee": [
        "idx_nominee_primary",
        "idx_nominee_added_by",
        "idx_nominee_linked",
    ],
    "account_nominee_scope": [
        "idx_nominee_scope_nominee",
        "idx_nominee_scope_container",
        "idx_nominee_scope_visible",
        "idx_nominee_scope_active",
    ],
    "profile_access": [
        "idx_profile_access_primary",
        "idx_profile_access_accessor",
    ],
    "profile_access_scope": [
        "idx_access_scope_access",
        "idx_access_scope_container",
        "idx_access_scope_visible",
    ],
    "asset_container": [
        "idx_asset_container_account",
        "idx_asset_container_type",
        "idx_asset_container_added_by",
    ],
    "asset_document": [
        "idx_asset_document_container",
        "idx_asset_document_account",
        "idx_asset_document_added_by",
    ],
    "account_inactivity_state": [
        "idx_inactivity_state",
        "idx_inactivity_last_active",
    ],
    "audit_log": [
        "idx_audit_account_id",
        "idx_audit_actor",
        "idx_audit_event_type",
        "idx_audit_entity",
        "idx_audit_domain",
    ],
    "audit_resource_access": [
        "idx_resource_access_account",
        "idx_resource_access_actor",
        "idx_resource_access_entity",
    ],
}

# Expected unique constraints (beyond primary keys)
# table_name -> [list of column tuples that should be unique]
EXPECTED_UNIQUE_CONSTRAINTS = {
    "account": [("phone",), ("email",)],
    "account_address": [("account_id", "address_type")],
    "account_pan": [("account_id",)],
    "account_auth_token": [("jti",)],
    "profile": [("account_id", "profile_type")],
    "account_nominee_scope": [("account_nominee_id", "container_id")],
    "profile_access": [("accessor_profile_id", "primary_profile_id")],
    "profile_access_scope": [("profile_access_id", "container_id")],
    "account_inactivity_state": [("account_id",)],
    "audit_resource_access": [("actor_account_id", "entity_type", "entity_id")],
    # Detail tables: unique on container_id
    "asset_bank_detail": [("container_id",)],
    "asset_demat_detail": [("container_id",)],
    "asset_mutual_fund_detail": [("container_id",)],
    "asset_retirement_detail": [("container_id",)],
    "asset_insurance_detail": [("container_id",)],
    "asset_real_estate_detail": [("container_id",)],
    "asset_loan_detail": [("container_id",)],
    "asset_business_detail": [("container_id",)],
    "asset_govt_savings_detail": [("container_id",)],
    "asset_crypto_detail": [("container_id",)],
    "asset_receivable_detail": [("container_id",)],
}

# Check constraints
EXPECTED_CHECK_CONSTRAINTS = {
    "profile_access": ["accessor_profile_id <> primary_profile_id"],
}

# Expected partitions for audit_log
EXPECTED_PARTITIONS = ["audit_log_2025", "audit_log_2026"]


# ---------------------------------------------------------------------------
# VALIDATION LOGIC
# ---------------------------------------------------------------------------


class SchemaValidator:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def log(self, status, category, message):
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}[status]
        self.results.append((status, category, message))
        print(f"  {icon} [{category}] {message}")
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        elif status == "WARN":
            self.warnings += 1

    def get_tables(self, schema="public"):
        """Get all tables including partitioned parents."""
        self.cursor.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = %s
            ORDER BY tablename;
        """,
            (schema,),
        )
        return {row["tablename"] for row in self.cursor.fetchall()}

    def get_columns(self, table_name, schema="public"):
        """Get columns and their types for a table."""
        self.cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
        """,
            (schema, table_name),
        )
        return {row["column_name"]: row for row in self.cursor.fetchall()}

    def get_indexes(self, table_name, schema="public"):
        """Get index names for a table."""
        self.cursor.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE schemaname = %s AND tablename = %s;
        """,
            (schema, table_name),
        )
        return {row["indexname"] for row in self.cursor.fetchall()}

    def get_unique_constraints(self, table_name, schema="public"):
        """Get unique constraint column sets for a table."""
        self.cursor.execute(
            """
            SELECT con.conname, array_agg(att.attname ORDER BY u.ord) AS columns
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            CROSS JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS u(attnum, ord)
            JOIN pg_attribute att ON att.attrelid = cls.oid AND att.attnum = u.attnum
            WHERE nsp.nspname = %s
              AND cls.relname = %s
              AND con.contype = 'u'
            GROUP BY con.conname;
        """,
            (schema, table_name),
        )
        return [tuple(row["columns"]) for row in self.cursor.fetchall()]

    def get_check_constraints(self, table_name, schema="public"):
        """Get check constraint definitions for a table."""
        self.cursor.execute(
            """
            SELECT con.conname, pg_get_constraintdef(con.oid) AS definition
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            WHERE nsp.nspname = %s
              AND cls.relname = %s
              AND con.contype = 'c';
        """,
            (schema, table_name),
        )
        return {row["conname"]: row["definition"] for row in self.cursor.fetchall()}

    def check_partitioned(self, table_name, schema="public"):
        """Check if a table is partitioned."""
        self.cursor.execute(
            """
            SELECT relkind FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s;
        """,
            (schema, table_name),
        )
        row = self.cursor.fetchone()
        if row:
            return row["relkind"] == "p"  # 'p' = partitioned table
        return False

    def get_foreign_keys(self, table_name, schema="public"):
        """Get foreign key references for a table."""
        self.cursor.execute(
            """
            SELECT
                con.conname,
                att.attname AS column_name,
                ref_cls.relname AS ref_table
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            JOIN pg_class ref_cls ON ref_cls.oid = con.confrelid
            CROSS JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS u(attnum, ord)
            JOIN pg_attribute att ON att.attrelid = cls.oid AND att.attnum = u.attnum
            WHERE nsp.nspname = %s
              AND cls.relname = %s
              AND con.contype = 'f'
            ORDER BY con.conname, u.ord;
        """,
            (schema, table_name),
        )
        fks = defaultdict(list)
        for row in self.cursor.fetchall():
            fks[row["conname"]].append(
                {
                    "column": row["column_name"],
                    "ref_table": row["ref_table"],
                }
            )
        return fks

    # ── Validation Steps ──

    def validate_tables(self):
        print("\n═══ TABLE EXISTENCE ═══")
        db_tables = self.get_tables()

        for table_name in sorted(EXPECTED_TABLES.keys()):
            if table_name in db_tables:
                self.log("PASS", "TABLE", f"{table_name} exists")
            else:
                self.log("FAIL", "TABLE", f"{table_name} is MISSING")

        # Check for unexpected tables
        expected_set = set(EXPECTED_TABLES.keys()) | set(EXPECTED_PARTITIONS)
        extra = db_tables - expected_set
        # Filter out common system/extension tables
        extra = {t for t in extra if not t.startswith(("pg_", "sql_"))}
        if extra:
            for tbl in sorted(extra):
                self.log("WARN", "TABLE", f"Unexpected table found: {tbl}")

    def validate_columns(self):
        print("\n═══ COLUMN VALIDATION ═══")
        db_tables = self.get_tables()

        for table_name, expected_cols in sorted(EXPECTED_TABLES.items()):
            if table_name not in db_tables:
                continue  # already reported as missing

            db_cols = self.get_columns(table_name)

            missing = set(expected_cols.keys()) - set(db_cols.keys())
            extra = set(db_cols.keys()) - set(expected_cols.keys())

            if missing:
                for col in sorted(missing):
                    self.log("FAIL", "COLUMN", f"{table_name}.{col} is MISSING")

            if extra:
                for col in sorted(extra):
                    self.log("WARN", "COLUMN", f"{table_name}.{col} is extra (not in schema spec)")

            # Type check for columns that exist
            for col_name, expected_type in expected_cols.items():
                if col_name in db_cols:
                    actual_type = db_cols[col_name]["data_type"]
                    if actual_type.startswith(expected_type) or actual_type == expected_type:
                        pass  # silent pass for types to reduce noise
                    else:
                        self.log(
                            "FAIL",
                            "TYPE",
                            f"{table_name}.{col_name}: "
                            f"expected '{expected_type}', got '{actual_type}'",
                        )

    def validate_indexes(self):
        print("\n═══ INDEX VALIDATION ═══")
        db_tables = self.get_tables()

        for table_name, expected_idxs in sorted(EXPECTED_INDEXES.items()):
            if table_name not in db_tables:
                continue

            # For partitioned tables, indexes may be on partitions
            db_idxs = self.get_indexes(table_name)

            # Also check partition indexes if table is partitioned
            if self.check_partitioned(table_name):
                for part in EXPECTED_PARTITIONS:
                    if part in db_tables:
                        db_idxs |= self.get_indexes(part)

            for idx_name in expected_idxs:
                # Check exact match or partition-prefixed match
                found = idx_name in db_idxs or any(idx_name in di for di in db_idxs)
                if found:
                    self.log("PASS", "INDEX", f"{table_name} → {idx_name}")
                else:
                    self.log("FAIL", "INDEX", f"{table_name} → {idx_name} is MISSING")

    def validate_unique_constraints(self):
        print("\n═══ UNIQUE CONSTRAINT VALIDATION ═══")
        db_tables = self.get_tables()

        for table_name, expected_uniques in sorted(EXPECTED_UNIQUE_CONSTRAINTS.items()):
            if table_name not in db_tables:
                continue

            db_uniques = self.get_unique_constraints(table_name)

            for expected_cols in expected_uniques:
                found = any(set(expected_cols) == set(db_u) for db_u in db_uniques)
                col_str = ", ".join(expected_cols)
                if found:
                    self.log("PASS", "UNIQUE", f"{table_name} ({col_str})")
                else:
                    self.log("FAIL", "UNIQUE", f"{table_name} ({col_str}) is MISSING")

    def validate_check_constraints(self):
        print("\n═══ CHECK CONSTRAINT VALIDATION ═══")
        db_tables = self.get_tables()

        for table_name, expected_checks in sorted(EXPECTED_CHECK_CONSTRAINTS.items()):
            if table_name not in db_tables:
                continue

            db_checks = self.get_check_constraints(table_name)
            all_defs = " ".join(db_checks.values()).lower()

            for check_fragment in expected_checks:
                # Normalize: remove spaces around operators for comparison
                normalized = check_fragment.lower().replace(" ", "")
                all_normalized = all_defs.replace(" ", "")
                if normalized in all_normalized:
                    self.log("PASS", "CHECK", f"{table_name}: {check_fragment}")
                else:
                    self.log("FAIL", "CHECK", f"{table_name}: {check_fragment} is MISSING")

    def validate_partitions(self):
        print("\n═══ PARTITION VALIDATION ═══")
        db_tables = self.get_tables()

        is_partitioned = self.check_partitioned("audit_log")
        if is_partitioned:
            self.log("PASS", "PARTITION", "audit_log is partitioned")
        else:
            if "audit_log" in db_tables:
                self.log("FAIL", "PARTITION", "audit_log exists but is NOT partitioned")
            else:
                self.log("FAIL", "PARTITION", "audit_log table is missing")

        for part in EXPECTED_PARTITIONS:
            if part in db_tables:
                self.log("PASS", "PARTITION", f"{part} exists")
            else:
                self.log("FAIL", "PARTITION", f"{part} is MISSING")

    def validate_foreign_keys(self):
        print("\n═══ FOREIGN KEY SPOT CHECK ═══")
        db_tables = self.get_tables()

        # Spot-check a few critical FK relationships
        critical_fks = {
            "account_address": {"account_id": "account"},
            "account_pan": {"account_id": "account"},
            "account_auth_token": {"account_id": "account"},
            "profile": {"account_id": "account"},
            "account_nominee": {"primary_account_id": "account"},
            "profile_access": {
                "accessor_profile_id": "profile",
                "primary_profile_id": "profile",
            },
            "asset_container": {"account_id": "account"},
            "asset_document": {"container_id": "asset_container"},
            "account_nominee_scope": {
                "account_nominee_id": "account_nominee",
                "container_id": "asset_container",
            },
            "profile_access_scope": {
                "profile_access_id": "profile_access",
                "container_id": "asset_container",
            },
        }

        for table_name, expected_refs in sorted(critical_fks.items()):
            if table_name not in db_tables:
                continue

            fks = self.get_foreign_keys(table_name)
            # Build column -> ref_table map
            col_ref_map = {}
            for _fk_name, fk_cols in fks.items():
                for fc in fk_cols:
                    col_ref_map[fc["column"]] = fc["ref_table"]

            for col, expected_ref in expected_refs.items():
                if col in col_ref_map:
                    if col_ref_map[col] == expected_ref:
                        self.log("PASS", "FK", f"{table_name}.{col} → {expected_ref}")
                    else:
                        self.log(
                            "FAIL",
                            "FK",
                            f"{table_name}.{col} references "
                            f"'{col_ref_map[col]}' instead of '{expected_ref}'",
                        )
                else:
                    self.log("FAIL", "FK", f"{table_name}.{col} → {expected_ref} FK is MISSING")

    def validate_security_columns(self):
        """Verify that no forbidden columns exist (Aadhaar, private keys, etc.)."""
        print("\n═══ SECURITY CHECKS ═══")
        db_tables = self.get_tables()

        forbidden = {
            "asset_crypto_detail": ["private_key", "seed_phrase", "mnemonic"],
            "account": ["aadhaar", "aadhaar_number", "aadhar"],
        }

        for table_name, bad_cols in forbidden.items():
            if table_name not in db_tables:
                continue
            db_cols = self.get_columns(table_name)
            for col in bad_cols:
                if col in db_cols:
                    self.log(
                        "FAIL",
                        "SECURITY",
                        f"{table_name}.{col} MUST NOT exist (security violation)",
                    )
                else:
                    self.log("PASS", "SECURITY", f"{table_name} has no '{col}' column")

    def run_all(self):
        print("=" * 60)
        print("  Project X — Database Schema Validation Report")
        print("=" * 60)

        self.validate_tables()
        self.validate_columns()
        self.validate_indexes()
        self.validate_unique_constraints()
        self.validate_check_constraints()
        self.validate_partitions()
        self.validate_foreign_keys()
        self.validate_security_columns()

        print("\n" + "=" * 60)
        print(
            f"  SUMMARY:  ✅ {self.passed} passed  |  "
            f"❌ {self.failed} failed  |  ⚠️  {self.warnings} warnings"
        )
        print("=" * 60)

        if self.failed == 0:
            print("\n  🎉 All schema validations passed!\n")
        else:
            print(f"\n  ⚠️  {self.failed} issue(s) need attention.\n")

        return self.failed == 0


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main():
    print("\n🔐 Project X — Schema Validator")
    print("─" * 40)
    print("Enter your PostgreSQL connection details:\n")

    host = input("  Host [localhost]: ").strip() or "localhost"
    port = input("  Port [5432]: ").strip() or "5432"
    dbname = input("  Database name: ").strip()
    user = input("  Username: ").strip()
    password = getpass.getpass("  Password: ")
    _schema = input("  Schema [public]: ").strip() or "public"

    if not dbname or not user:
        print("\n❌ Database name and username are required.")
        sys.exit(1)

    print(f"\n  Connecting to {host}:{port}/{dbname} as {user}...")

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=10,
        )
        conn.set_session(readonly=True)
        print("  ✅ Connected successfully!\n")
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed: {e}")
        sys.exit(1)

    try:
        validator = SchemaValidator(conn)
        success = validator.run_all()
        sys.exit(0 if success else 1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
