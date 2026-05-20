from __future__ import annotations

import json
from pathlib import Path

from workspace.ribao_social_crawl import (
    PlatformExportResult,
    RibaoSocialCrawlRequest,
    run_ribao_social_crawl,
)


def test_run_ribao_social_crawl_returns_result_and_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_run_platform(**_: object) -> PlatformExportResult:
        return PlatformExportResult(
            platform="xhs",
            contents_csv=str(tmp_path / "xhs_contents.csv"),
            comments_csv=str(tmp_path / "xhs_comments.csv"),
            exit_code=0,
        )

    monkeypatch.setattr(
        "workspace.ribao_social_crawl._run_platform",
        fake_run_platform,
    )

    request = RibaoSocialCrawlRequest(
        target_date="20260520",
        output_dir=tmp_path,
        keywords=("河北 舆情", "河北 地震"),
        platforms=("xhs",),
    )

    result = run_ribao_social_crawl(request)

    assert result.success is True
    assert result.exit_code == 0
    assert result.manifest_path == tmp_path / "crawl_manifest.json"
    assert result.crawl_log_path == tmp_path / "crawl.log"

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["target_date"] == "20260520"
    assert manifest["keywords"] == ["河北 舆情", "河北 地震"]
    assert manifest["platforms"] == ["xhs"]
