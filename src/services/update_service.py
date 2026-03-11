"""Application update check service."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from ..config import get_config
from ..utils.errors import ServiceError


VersionPart = Union[int, str]


class UpdateService:
    """Check latest app version from configured remote source."""

    def __init__(self) -> None:
        self.config = get_config()
        self.current_version = self._resolve_current_version()

    def get_current_version(self) -> str:
        return self.current_version

    def check_update(self) -> Dict[str, Any]:
        checked_at = datetime.now(timezone.utc).isoformat()
        source = self._resolve_source()

        if source == "none":
            return self._status_payload(
                checked_at=checked_at,
                source=source,
                configured=False,
                reachable=False,
                message="未配置更新源，请设置 UPDATE_METADATA_URL 或 GITHUB_REPO",
            )

        try:
            remote = (
                self._fetch_from_metadata_url(self.config.update_metadata_url)
                if source == "metadata_url"
                else self._fetch_from_github(self.config.github_repo)
            )
        except requests.RequestException as exc:
            return self._status_payload(
                checked_at=checked_at,
                source=source,
                configured=True,
                reachable=False,
                message=f"更新源访问失败：{exc}",
            )

        latest = self._clean_version(str(remote.get("version") or ""))
        if not latest:
            return self._status_payload(
                checked_at=checked_at,
                source=source,
                configured=True,
                reachable=True,
                message="更新源返回格式不正确：缺少 version 字段",
            )

        has_update = self._compare_versions(latest, self.current_version) > 0
        return {
            "currentVersion": self.current_version,
            "latestVersion": latest,
            "hasUpdate": has_update,
            "releaseNotes": remote.get("releaseNotes") or "",
            "releaseUrl": remote.get("releaseUrl") or "",
            "downloadUrl": remote.get("downloadUrl") or "",
            "publishedAt": remote.get("publishedAt") or "",
            "source": source,
            "configured": True,
            "reachable": True,
            "checkedAt": checked_at,
        }

    def _status_payload(
        self,
        *,
        checked_at: str,
        source: str,
        configured: bool,
        reachable: bool,
        message: str,
    ) -> Dict[str, Any]:
        return {
            "currentVersion": self.current_version,
            "latestVersion": self.current_version,
            "hasUpdate": False,
            "releaseNotes": "",
            "releaseUrl": "",
            "downloadUrl": "",
            "publishedAt": "",
            "source": source,
            "configured": configured,
            "reachable": reachable,
            "message": message,
            "checkedAt": checked_at,
        }

    def _resolve_source(self) -> str:
        if self.config.update_metadata_url:
            return "metadata_url"
        if self.config.github_repo:
            return "github"
        return "none"

    def _resolve_current_version(self) -> str:
        app_version = self._clean_version(self.config.app_version)
        if app_version:
            return app_version

        package_json = Path(__file__).resolve().parents[2] / "electron" / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                version = self._clean_version(str(data.get("version") or ""))
                if version:
                    return version
            except Exception:
                pass

        return "0.1.0"

    def _fetch_from_metadata_url(self, url: str) -> Dict[str, Any]:
        headers = {"User-Agent": "SCIdrawer-UpdateChecker/1.0"}
        resp = requests.get(url, timeout=self.config.update_check_timeout, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ServiceError("更新源返回格式不正确：应为 JSON 对象")

        return {
            "version": data.get("version")
            or data.get("latestVersion")
            or data.get("tag")
            or data.get("tag_name")
            or "",
            "releaseNotes": data.get("releaseNotes") or data.get("notes") or data.get("body") or "",
            "releaseUrl": data.get("releaseUrl") or data.get("html_url") or data.get("url") or "",
            "downloadUrl": data.get("downloadUrl") or data.get("download_url") or "",
            "publishedAt": data.get("publishedAt") or data.get("published_at") or "",
        }

    def _fetch_from_github(self, repo: str) -> Dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SCIdrawer-UpdateChecker/1.0",
        }
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        resp = requests.get(api_url, timeout=self.config.update_check_timeout, headers=headers)
        if resp.status_code == 404:
            return self._fetch_from_github_tags(repo, headers)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ServiceError("GitHub 更新源返回格式不正确")

        return {
            "version": data.get("tag_name") or data.get("name") or "",
            "releaseNotes": data.get("body") or "",
            "releaseUrl": data.get("html_url") or "",
            "downloadUrl": self._extract_github_asset_url(data.get("assets")),
            "publishedAt": data.get("published_at") or "",
        }

    def _fetch_from_github_tags(self, repo: str, headers: Dict[str, str]) -> Dict[str, Any]:
        tags_url = f"https://api.github.com/repos/{repo}/tags"
        resp = requests.get(tags_url, timeout=self.config.update_check_timeout, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ServiceError("GitHub tags 返回格式不正确")
        if not data:
            raise ServiceError("GitHub 仓库未找到可用版本标签")

        latest_tag = data[0] if isinstance(data[0], dict) else {}
        tag_name = str(latest_tag.get("name") or "").strip()
        return {
            "version": tag_name,
            "releaseNotes": "",
            "releaseUrl": f"https://github.com/{repo}/tags",
            "downloadUrl": "",
            "publishedAt": "",
        }

    def _extract_github_asset_url(self, assets: Any) -> str:
        if not isinstance(assets, list):
            return ""

        preferred = (".exe", ".msi", ".zip", ".dmg", ".AppImage", ".deb")
        for ext in preferred:
            for item in assets:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").lower()
                if name.endswith(ext.lower()):
                    return str(item.get("browser_download_url") or "")

        for item in assets:
            if isinstance(item, dict) and item.get("browser_download_url"):
                return str(item.get("browser_download_url"))
        return ""

    def _clean_version(self, version: str) -> str:
        value = str(version or "").strip()
        if value.startswith(("v", "V")):
            value = value[1:]
        return value

    def _compare_versions(self, a: str, b: str) -> int:
        core_a, pre_a = self._split_version(a)
        core_b, pre_b = self._split_version(b)

        max_len = max(len(core_a), len(core_b))
        for idx in range(max_len):
            part_a = core_a[idx] if idx < len(core_a) else 0
            part_b = core_b[idx] if idx < len(core_b) else 0
            if part_a < part_b:
                return -1
            if part_a > part_b:
                return 1

        if not pre_a and not pre_b:
            return 0
        if not pre_a and pre_b:
            return 1
        if pre_a and not pre_b:
            return -1

        return self._compare_prerelease(pre_a, pre_b)

    def _split_version(self, version: str) -> Tuple[List[int], List[VersionPart]]:
        value = self._clean_version(version)
        base, _, pre = value.partition("-")
        base_parts = [int(p) if p.isdigit() else 0 for p in base.split(".") if p != ""]
        pre_parts: List[VersionPart] = []
        if pre:
            for token in re.split(r"[.\-]", pre):
                if not token:
                    continue
                pre_parts.append(int(token) if token.isdigit() else token.lower())
        return base_parts, pre_parts

    def _compare_prerelease(self, a: List[VersionPart], b: List[VersionPart]) -> int:
        max_len = max(len(a), len(b))
        for idx in range(max_len):
            if idx >= len(a):
                return -1
            if idx >= len(b):
                return 1

            part_a = a[idx]
            part_b = b[idx]
            if part_a == part_b:
                continue

            if isinstance(part_a, int) and isinstance(part_b, int):
                return -1 if part_a < part_b else 1
            if isinstance(part_a, int) and isinstance(part_b, str):
                return -1
            if isinstance(part_a, str) and isinstance(part_b, int):
                return 1
            return -1 if str(part_a) < str(part_b) else 1

        return 0


_update_service: Optional[UpdateService] = None


def get_update_service() -> UpdateService:
    global _update_service
    if _update_service is None:
        _update_service = UpdateService()
    return _update_service
