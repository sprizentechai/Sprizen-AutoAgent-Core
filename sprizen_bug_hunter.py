#!/usr/bin/env python3
"""
Sprizen Bug Hunter v2.0 — Autonomous AI Agent for Edge Devices (Termux/Android)
Parallel scanning, SHA256 caching, Markdown reports — sirf stdlib + requests.
"""

import os
import sys
import json
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from provider_router import ProviderRouter


@dataclass
class BugHunterConfig:
    """BugHunter ki configuration — dataclass se clean aur type-safe hai."""
    cache_enabled: bool = True
    parallel_workers: int = 4
    output_dir: str = "./sprizen_reports"
    max_file_size_kb: int = 500
    file_extensions: tuple = (".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".php", ".rb", ".sh")


class GitHubConnector:
    """
    GitHub integration placeholder — future mein issues create karne ke liye.
    Abhi sirf structure ready hai, actual API calls baad mein add karenge.
    """

    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        self.token = token
        self.repo = repo

    def create_issue(self, title: str, body: str, labels: List[str] = None) -> Dict[str, Any]:
        """GitHub issue create karne ka placeholder — abhi mock return karta hai."""
        return {
            "status": "placeholder",
            "message": "GitHubConnector abhi placeholder hai. Token aur repo set karo.",
            "title": title,
            "body": body[:100] + "...",
            "labels": labels or ["bug", "security"]
        }

    def is_configured(self) -> bool:
        """Check karta hai ki GitHub token set hai ya nahi."""
        return bool(self.token and self.repo)


class BugHunter:
    """
    Main BugHunter class — files scan karta hai, AI se analyze karwata hai, aur report generate karta hai.
    ThreadPoolExecutor se parallel processing, SHA256 cache se duplicate work avoid karta hai.
    """

    SYSTEM_PROMPT = """You are Sprizen Bug Hunter v2.0, an elite AI security analyst.
Analyze the provided code for:
1. Security vulnerabilities (SQL injection, XSS, command injection, path traversal, etc.)
2. Logic bugs and error handling issues
3. Performance anti-patterns
4. Code smell and maintainability issues

Respond in this exact format:
SEVERITY: [CRITICAL/HIGH/MEDIUM/LOW/INFO]
LINE: [line number or N/A]
ISSUE: [brief description]
FIX: [suggested fix]

If no issues found, respond: NO_ISSUES_FOUND"""

    def __init__(self, router: ProviderRouter, config: Optional[BugHunterConfig] = None):
        self.router = router
        self.config = config or BugHunterConfig()
        self.cache: Dict[str, str] = {}
        self.cache_path = ".sprizen_cache.json"
        self.github = GitHubConnector()
        self._load_cache()
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Output directory create karta hai agar exist nahi karti."""
        os.makedirs(self.config.output_dir, exist_ok=True)

    def _load_cache(self):
        """SHA256 cache load karta hai — unchanged files skip karne ke liye."""
        if not self.config.cache_enabled:
            return
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                print(f"[CACHE] {len(self.cache)} entries load ho gayi.")
        except (json.JSONDecodeError, IOError) as e:
            print(f"[CACHE ERROR] Cache load fail: {e}")
            self.cache = {}

    def _save_cache(self):
        """Cache ko disk pe save karta hai."""
        if not self.config.cache_enabled:
            return
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            print(f"[CACHE ERROR] Cache save fail: {e}")

    def _compute_sha256(self, file_path: str) -> str:
        """File ka SHA256 hash compute karta hai — cache key ke liye."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _is_cache_valid(self, file_path: str) -> bool:
        """Check karta hai ki file unchanged hai (cache hit)."""
        if not self.config.cache_enabled:
            return False
        if not os.path.exists(file_path):
            return False
        try:
            current_hash = self._compute_sha256(file_path)
            cached_hash = self.cache.get(file_path)
            return cached_hash == current_hash
        except (IOError, OSError):
            return False

    def _update_cache(self, file_path: str):
        """File ka hash cache mein update karta hai."""
        if not self.config.cache_enabled:
            return
        try:
            self.cache[file_path] = self._compute_sha256(file_path)
        except (IOError, OSError) as e:
            print(f"[CACHE] {file_path} cache update fail: {e}")

    def _read_file(self, file_path: str) -> str:
        """File ko safely read karta hai — binary files skip karta hai."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except (IOError, OSError) as e:
            return f"[ERROR] File read fail: {e}"

    def _should_scan_file(self, file_path: str) -> bool:
        """Check karta hai ki file scan ke layak hai ya nahi."""
        # Extension check
        if not file_path.endswith(self.config.file_extensions):
            return False

        # Size check
        try:
            size_kb = os.path.getsize(file_path) / 1024
            if size_kb > self.config.max_file_size_kb:
                print(f"[SKIP] {file_path} ({size_kb:.0f}KB) — max size {self.config.max_file_size_kb}KB exceed.")
                return False
        except (IOError, OSError):
            return False

        return True

    def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Single file ko AI se analyze karwata hai — core logic yahan hai."""
        result = {
            "file": file_path,
            "status": "pending",
            "issues": [],
            "error": None,
            "scan_time": None
        }

        # Cache check
        if self._is_cache_valid(file_path):
            result["status"] = "cached"
            result["issues"] = [{"severity": "INFO", "line": "N/A", "issue": "File unchanged — cached result", "fix": "N/A"}]
            return result

        start_time = time.time()
        code = self._read_file(file_path)

        if code.startswith("[ERROR]"):
            result["status"] = "error"
            result["error"] = code
            return result

        # Privacy check — sensitive files ke liye local model use karo
        basename = os.path.basename(file_path).lower()
        privacy_keywords = ["secret", "password", "token", "key", "credential", "config", ".env"]
        is_private = any(kw in basename for kw in privacy_keywords)

        context = {"privacy_sensitive": is_private}

        try:
            prompt = f"Analyze this code for bugs and security issues:\n\n```\n{code}\n```"
            response = self.router.route(prompt, system_prompt=self.SYSTEM_PROMPT, context=context)

            # Parse AI response
            issues = self._parse_ai_response(response)
            result["issues"] = issues
            result["status"] = "completed"
            self._update_cache(file_path)

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        result["scan_time"] = round(time.time() - start_time, 2)
        return result

    def _parse_ai_response(self, response: str) -> List[Dict[str, str]]:
        """AI response ko structured issues mein parse karta hai."""
        issues = []
        lines = response.strip().split("\n")

        current_issue = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_issue:
                    issues.append(current_issue)
                    current_issue = {}
                continue

            if line.upper().startswith("SEVERITY:"):
                current_issue["severity"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("LINE:"):
                current_issue["line"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("ISSUE:"):
                current_issue["issue"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("FIX:"):
                current_issue["fix"] = line.split(":", 1)[1].strip()
            elif "NO_ISSUES_FOUND" in line.upper():
                return [{"severity": "INFO", "line": "N/A", "issue": "No issues detected", "fix": "N/A"}]

        if current_issue:
            issues.append(current_issue)

        if not issues:
            issues.append({"severity": "INFO", "line": "N/A", "issue": "No structured issues found", "fix": "N/A"})

        return issues

    def _collect_files(self, path: str) -> List[str]:
        """Path se scan karne layak files collect karta hai — recursive."""
        files = []
        target = Path(path)

        if target.is_file():
            if self._should_scan_file(str(target)):
                files.append(str(target))
        elif target.is_dir():
            for ext in self.config.file_extensions:
                for file_path in target.rglob(f"*{ext}"):
                    if self._should_scan_file(str(file_path)):
                        files.append(str(file_path))
        else:
            print(f"[ERROR] Path exist nahi karta: {path}")

        return files

    def scan(self, path: str) -> Dict[str, Any]:
        """
        Main scan method — auto detect file ya directory, parallel scan karta hai.
        Markdown report generate karta hai.
        """
        print(f"\n{'='*60}")
        print(f"  Sprizen Bug Hunter v2.0 — Scan Started")
        print(f"  Target: {path}")
        print(f"  Workers: {self.config.parallel_workers}")
        print(f"  Cache: {'Enabled' if self.config.cache_enabled else 'Disabled'}")
        print(f"{'='*60}\n")

        files = self._collect_files(path)
        if not files:
            print("[INFO] Koi scan karne layak file nahi mili.")
            return {"status": "no_files", "files_scanned": 0, "issues_found": 0}

        print(f"[INFO] {len(files)} files scan karne hain...\n")

        results: List[Dict[str, Any]] = []
        completed = 0
        cached = 0
        errors = 0

        # Parallel scanning with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            future_to_file = {executor.submit(self._analyze_file, fp): fp for fp in files}

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result["status"] == "cached":
                        cached += 1
                        print(f"[CACHED] {file_path}")
                    elif result["status"] == "error":
                        errors += 1
                        print(f"[ERROR] {file_path} — {result.get('error', 'Unknown')}")
                    else:
                        completed += 1
                        issue_count = len([i for i in result["issues"] if i.get("severity") != "INFO"])
                        print(f"[DONE] {file_path} — {issue_count} issues ({result.get('scan_time', 0)}s)")

                except Exception as e:
                    errors += 1
                    print(f"[FATAL] {file_path} — {e}")
                    results.append({"file": file_path, "status": "error", "error": str(e), "issues": []})

        # Save cache
        self._save_cache()

        # Generate report
        report_path = self._generate_markdown_report(results, path)

        summary = {
            "status": "completed",
            "target": path,
            "files_scanned": len(files),
            "completed": completed,
            "cached": cached,
            "errors": errors,
            "report_path": report_path,
            "results": results
        }

        print(f"\n{'='*60}")
        print(f"  Scan Complete!")
        print(f"  Files: {len(files)} | Done: {completed} | Cached: {cached} | Errors: {errors}")
        print(f"  Report: {report_path}")
        print(f"{'='*60}\n")

        return summary

    def _generate_markdown_report(self, results: List[Dict[str, Any]], target: str) -> str:
        """Markdown format mein report generate karta hai — GitHub/GitLab compatible."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_name = f"sprizen_report_{timestamp}.md"
        report_path = os.path.join(self.config.output_dir, report_name)

        total_issues = 0
        critical = 0
        high = 0
        medium = 0
        low = 0

        for r in results:
            for issue in r.get("issues", []):
                sev = issue.get("severity", "INFO").upper()
                if sev == "CRITICAL":
                    critical += 1
                elif sev == "HIGH":
                    high += 1
                elif sev == "MEDIUM":
                    medium += 1
                elif sev == "LOW":
                    low += 1
                if sev != "INFO":
                    total_issues += 1

        lines = []
        lines.append("# Sprizen Bug Hunter v2.0 — Security Audit Report")
        lines.append("")
        lines.append(f"**Target:** `{target}`")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| Files Scanned | {len(results)} |")
        lines.append(f"| Total Issues | {total_issues} |")
        lines.append(f"| Critical | {critical} |")
        lines.append(f"| High | {high} |")
        lines.append(f"| Medium | {medium} |")
        lines.append(f"| Low | {low} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        for result in results:
            file_path = result["file"]
            status = result["status"]
            scan_time = result.get("scan_time", "N/A")

            lines.append(f"## {file_path}")
            lines.append("")
            lines.append(f"**Status:** `{status}` | **Scan Time:** {scan_time}s")
            lines.append("")

            if result.get("error"):
                lines.append(f"> Error: `{result['error']}`")
                lines.append("")

            issues = result.get("issues", [])
            if issues and not (len(issues) == 1 and issues[0].get("severity") == "INFO"):
                lines.append("| Severity | Line | Issue | Fix |")
                lines.append("|----------|------|-------|-----|")
                for issue in issues:
                    sev = issue.get("severity", "INFO")
                    line = issue.get("line", "N/A")
                    desc = issue.get("issue", "N/A").replace("|", "\\|")
                    fix = issue.get("fix", "N/A").replace("|", "\\|")
                    lines.append(f"| {sev} | {line} | {desc} | {fix} |")
                lines.append("")
            else:
                lines.append("No issues found.")
                lines.append("")

            lines.append("---")
            lines.append("")

        lines.append("*Report generated by Sprizen Bug Hunter v2.0*")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return report_path

    def set_github_connector(self, token: str, repo: str):
        """GitHub connector configure karta hai — issues auto-create ke liye."""
        self.github = GitHubConnector(token=token, repo=repo)

    def get_config(self) -> Dict[str, Any]:
        """Current config return karta hai."""
        return asdict(self.config)


def create_bug_hunter(router: Optional[ProviderRouter] = None,
                      config: Optional[BugHunterConfig] = None) -> BugHunter:
    """
    Factory function — backward compatible, simple se BugHunter instance create karta hai.
    Agar router nahi diya to default ProviderRouter use karega.
    """
    if router is None:
        router = ProviderRouter()
    return BugHunter(router=router, config=config)


if __name__ == "__main__":
    # Demo run
    router = ProviderRouter()
    hunter = create_bug_hunter(router=router)
    
    # Health check
    health = router.get_provider_health()
    print("=== Provider Health ===")
    for name, status in health.items():
        print(f"  {name}: {status}")
    
    print("\n=== Config ===")
    print(json.dumps(hunter.get_config(), indent=2))
