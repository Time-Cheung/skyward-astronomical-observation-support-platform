"""Contracts for the bilingual Skyward data-notes page."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"


def test_about_and_api_titles_reuse_home_v0_title_class():
    index = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    about = (TEMPLATES / "about.html").read_text(encoding="utf-8")
    api = (TEMPLATES / "api.html").read_text(encoding="utf-8")
    assert 'class="v0-title" data-i18n="homeTitle"' in index
    assert 'class="v0-title" data-i18n="aboutTitle"' in about
    assert 'class="v0-title" data-i18n="apiTitle"' in api


def test_data_notes_have_usage_and_separate_current_goal_future_scope():
    about = (TEMPLATES / "about.html").read_text(encoding="utf-8")
    script = (STATIC / "about.js").read_text(encoding="utf-8")
    for key in (
        "currentStageLabel",
        "goalStageLabel",
        "futureStageLabel",
        "usageTitle",
        "usageStep1Body",
        "usageStep2Body",
        "usageStep3Body",
        "usageStep4Body",
    ):
        assert f'data-about-i18n="{key}"' in about
        assert key in script
    assert "只有确认后才加载所选源表数据并绘制标记" in script
    assert "geometry-only" in script
    assert "不构成观测批准" in script
    assert "天气与大气" in script and "机械轨迹限位" in script and "联合观测证据" in script


def test_catalogue_guide_is_one_select_with_five_targeted_choices():
    about = (TEMPLATES / "about.html").read_text(encoding="utf-8")
    select = re.search(r'<select id="about-catalogue-select"[^>]*>(.*?)</select>', about, re.S)
    assert select is not None
    assert " multiple" not in select.group(0)
    values = re.findall(r'<option value="([^"]+)">', select.group(1))
    assert values == ["2lhaaso", "fermi-fl16y", "fermi-3fhl", "tevcat", "gaia-dr3"]
    assert 'data-i18n="catalogueTitle"' not in about
    assert 'data-about-i18n="catalogueGuideTitle"' in about


def test_catalogue_counts_and_scientific_boundaries_are_explicit_in_both_languages():
    script = (STATIC / "about.js").read_text(encoding="utf-8")
    for value in ("190 installed records", "7,224 installed records", "1,556 installed records"):
        assert value in script
    assert "361-row snapshot · cutoff 2026-09-16" in script
    assert "2,000 hard maximum per request" in script
    assert "no fixed local record total" in script
    assert "Localization uncertainty is not physical extension" in script
    assert "All 361 hard footprints are unknown" in script
    assert "not the brightest N or a representative sample" in script
    for value in ("本地已安装 190 条记录", "本地已安装 7,224 条记录", "本地已安装 1,556 条记录"):
        assert value in script
    assert "本地快照 361 条 · 截止 2026-09-16" in script
    assert "硬上限 2,000 条/次" in script


def test_about_assets_are_local_and_follow_shared_language_event():
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    script = (STATIC / "about.js").read_text(encoding="utf-8")
    stylesheet = (STATIC / "about.css").read_text(encoding="utf-8")
    assert "path='/about.css'" in base
    assert "path='/about.js'" in base
    assert 'localStorage.getItem("skyward.language")' in script
    assert 'document.addEventListener("skyward:language-change", applyLanguage)' in script
    assert "fetch(" not in script
    assert "@media (max-width: 760px)" in stylesheet
