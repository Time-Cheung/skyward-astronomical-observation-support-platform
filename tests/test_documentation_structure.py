"""Acceptance contracts for the consolidated bilingual documentation."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FORMAL = [
    DOCS / "README.zh-CN.md", DOCS / "README.en.md",
    DOCS / "DEPLOYMENT.zh-CN.md", DOCS / "DEPLOYMENT.en.md",
    DOCS / "DEVELOPMENT.zh-CN.md", DOCS / "DEVELOPMENT.en.md",
]
REMOVED = [
    ROOT / "DEPLOYMENT.md", ROOT / "README.en.md", ROOT / "README.zh-CN.md",
    DOCS / "README.md", DOCS / "developer-notes.md", DOCS / "offline-deployment.md",
    DOCS / "tevcat-acquisition.md", DOCS / "ui-refinement-20260919.md",
    DOCS / "upgrade-acceptance-20260916.md", DOCS / "en", DOCS / "zh",
]

def test_documentation_is_one_root_entry_plus_six_formal_guides():
    assert (ROOT / "README.md").is_file()
    assert all(path.is_file() for path in FORMAL)
    assert all(not path.exists() for path in REMOVED)
    assert sorted(path.name for path in DOCS.iterdir()) == sorted(path.name for path in FORMAL)
    root = (ROOT / "README.md").read_text(encoding="utf-8")
    assert len(root.splitlines()) <= 20
    assert "V2.1" in root and "2.1.20260924" in root
    assert 'version="2.1.20260924"' in (ROOT / "app/main.py").read_text(encoding="utf-8")
    for path in FORMAL:
        assert f"docs/{path.name}" in root

def test_documented_contracts_match_the_formal_release():
    zh_user, en_user, zh_deploy, en_deploy, zh_dev, en_dev = [path.read_text(encoding="utf-8") for path in FORMAL]
    combined = "\n".join((zh_user, en_user, zh_deploy, en_deploy, zh_dev, en_dev))
    for fact in ("30 天", "30 days", "363", "223", "140", "10°", "5°", "4.15", "result_local_fov_only"):
        assert fact in combined
    assert "2.1.20260924" in zh_dev and "2.1.20260924" in en_dev
    assert "2.1 候选" not in zh_dev and "2.1 candidate" not in en_dev
    assert "skyward-v<主版本.小版本>.zip" in zh_dev
    assert "skyward-v<major.minor>.zip" in en_dev
    assert "skyward-v2.1.zip" in combined
    assert "361-row snapshot" not in combined
    assert "本地快照 361" not in combined
    assert "最长 1 天" not in combined and "one day" not in combined.lower()
    assert "Gaia DR3 只在结果页局部图" in zh_user
    assert "available only" in en_user and "result local map" in en_user
    assert "红/绿色十字符号" in zh_user and "red/green cross symbols" in en_user
    for text in (zh_user, en_user, zh_deploy, en_deploy, zh_dev, en_dev):
        assert "Copyright © 2026 Wei Zhang" in text
    assert "开发者：**张炜（Wei Zhang）**" in zh_dev
    assert "Developer: **Wei Zhang (张炜)**" in en_dev

def test_all_relative_markdown_links_resolve():
    markdown = [ROOT / "README.md", *FORMAL]
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            assert resolved.exists(), f"broken link in {path}: {target}"
