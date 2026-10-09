"""Local, bounded source checks and a signed Guardian scan queue."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import re

from flask import current_app
from sqlalchemy import select

from ...extensions import db
from ...models import AIGuardianFinding, AIGuardianScan, AIBuilderProject
from .project_files import normalize_project_files, project_digest


SCANNER_VERSION = "1"
MAX_FINDINGS = 200
_RULES = (
    (
        "secret.literal", "high",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
            r"\bAKIA[0-9A-Z]{16}\b|"
            r"(?i:\b(?:api[_-]?key|client[_-]?secret|password|passwd|secret|token)"
            r"\s*[:=]\s*['\"][A-Za-z0-9_./+=:-]{16,}['\"])"
        ),
        "Possible hard-coded credential detected. The matching source text is hidden.",
    ),
    (
        "python.dynamic-eval", "high", re.compile(r"\b(?:eval|exec)\s*\("),
        "Dynamic code evaluation can execute untrusted input.",
    ),
    (
        "python.shell-true", "high",
        re.compile(r"\bsubprocess\.(?:run|Popen|call|check_call|check_output)\s*\([^)]*shell\s*=\s*True", re.S),
        "A subprocess call enables shell parsing; validate input and avoid shell mode.",
    ),
    (
        "python.os-system", "high", re.compile(r"\bos\.system\s*\("),
        "A shell command is assembled through os.system.",
    ),
    (
        "python.pickle-load", "high", re.compile(r"\bpickle\.(?:load|loads)\s*\("),
        "Untrusted pickle data can execute code during deserialization.",
    ),
    (
        "flask.debug-enabled", "medium", re.compile(r"\bdebug\s*=\s*True\b"),
        "Debug mode should not be enabled in a deployable application.",
    ),
)


def scan_project(files):
    findings = []
    for item in normalize_project_files(files):
        for line_number, line in enumerate(item["content"].splitlines(), 1):
            for rule_id, severity, pattern, summary in _RULES:
                if pattern.search(line):
                    fingerprint = sha256(
                        f"{rule_id}\0{item['path']}\0{line_number}".encode("utf-8")
                    ).hexdigest()
                    findings.append({
                        "fingerprint": fingerprint,
                        "severity": severity,
                        "rule_id": rule_id,
                        "file_path": item["path"],
                        "line_number": line_number,
                        "summary": summary,
                    })
                    break
            if len(findings) >= MAX_FINDINGS:
                break
        if len(findings) >= MAX_FINDINGS:
            break
    return findings


def _queue_signature(scan):
    key = str(current_app.config.get("SECRET_KEY") or "").encode("utf-8")
    if len(key) < 8:
        raise RuntimeError("Guardian queue signing is unavailable.")
    created_at = scan.created_at
    if created_at is not None:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
    payload = json.dumps({
        "id": scan.id,
        "project_id": scan.project_id,
        "admin_user_id": scan.admin_user_id,
        "trigger": scan.trigger,
        "source_sha256": scan.source_sha256,
        "created_at": created_at.isoformat() if created_at else None,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, payload, sha256).hexdigest()


def create_scan(project: AIBuilderProject, *, trigger: str, actor_id: int) -> AIGuardianScan:
    if trigger not in {"manual", "deployment", "nightly"}:
        raise ValueError("Unsupported Guardian scan trigger.")
    files = json.loads(project.files_json)
    scan = AIGuardianScan(
        id=__import__("uuid").uuid4().hex,
        project_id=project.id,
        admin_user_id=actor_id,
        trigger=trigger,
        status="queued",
        source_sha256=project_digest(files),
        queue_signature="pending",
        scanner_version=SCANNER_VERSION,
        created_at=datetime.now(timezone.utc),
    )
    scan.queue_signature = _queue_signature(scan)
    db.session.add(scan)
    db.session.commit()
    return scan


def _signature_valid(scan):
    try:
        return hmac.compare_digest(scan.queue_signature, _queue_signature(scan))
    except (TypeError, ValueError, RuntimeError):
        return False


def process_scan(scan: AIGuardianScan):
    if scan.status != "queued" or not _signature_valid(scan):
        scan.status = "failed"
        scan.result_summary = "Guardian queue signature validation failed."
        scan.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return scan, []
    project = db.session.scalar(select(AIBuilderProject).where(
        AIBuilderProject.id == scan.project_id,
        AIBuilderProject.admin_user_id == scan.admin_user_id,
    ))
    if project is None:
        scan.status = "failed"
        scan.result_summary = "The project is no longer available to this Admin."
        scan.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return scan, []

    try:
        files = json.loads(project.files_json)
        if project_digest(files) != scan.source_sha256:
            scan.status = "warning"
            scan.result_summary = "Project source changed after the scan was queued."
            scan.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            return scan
        scan.status = "running"
        db.session.commit()
        results = scan_project(files)
        new_findings = []
        for item in results:
            existing = db.session.scalar(select(AIGuardianFinding).where(
                AIGuardianFinding.project_id == project.id,
                AIGuardianFinding.fingerprint == item["fingerprint"],
            ))
            if existing is None:
                existing = AIGuardianFinding(
                    project_id=project.id,
                    first_scan_id=scan.id,
                    latest_scan_id=scan.id,
                    **item,
                )
                db.session.add(existing)
                new_findings.append(existing)
            else:
                existing.latest_scan_id = scan.id
                existing.severity = item["severity"]
                existing.rule_id = item["rule_id"]
                existing.file_path = item["file_path"]
                existing.line_number = item["line_number"]
                existing.summary = item["summary"]
                if existing.status in {"fixed", "false_positive"}:
                    existing.status = "open"
                if existing.first_notified_at is None:
                    new_findings.append(existing)
        scan.status = "completed"
        scan.result_summary = (
            f"Guardian completed with {len(results)} finding(s)."
            if results else "Guardian completed with no findings."
        )
        scan.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return scan, new_findings
    except Exception:
        db.session.rollback()
        scan = db.session.get(AIGuardianScan, scan.id)
        if scan is not None:
            scan.status = "warning"
            scan.result_summary = "Guardian scan could not complete; no deployment block was raised."
            scan.completed_at = datetime.now(timezone.utc)
            db.session.commit()
        return scan, []
