/* About-page catalogue and scope copy. Uses the shared language preference
 * without extending the large application controller. */
(() => {
  const catalogueSelect = document.getElementById("about-catalogue-select");
  if (!catalogueSelect) return;

  const copy = {
    zh: {
      skywardOverviewTitle: "Skyward 介绍",
      skywardScopeStatement: "V0 只给出可解释的几何可行性候选；不判断运行就绪状态，也不构成观测批准。",
      currentStageLabel: "现有功能",
      currentStageTitle: "当前可用",
      currentStageBody: "浏览已支持的源表，查看全天图和局部视场几何、源详情，并按明确的几何约束计算源中心与完整源窗口。",
      goalStageLabel: "平台目标",
      goalStageTitle: "可解释的决策辅助",
      goalStageBody: "提供只读、可复现、可解释的证据，帮助操作人员或科研人员准备观测决策。",
      futureStageLabel: "未来开发",
      futureStageTitle: "尚未接入的运行证据",
      futureStageBody: "只有在取得权威输入并完成验证后，未来版本才可能接入实时指向与设备遥测、天气与大气、机械轨迹限位、仪器可用性和联合观测证据。",
      usageTitle: "使用说明",
      usageStep1Title: "打开天图。",
      usageStep1Body: "返回“天区与规划”，在天图区域打开源表选择器。",
      usageStep2Title: "勾选源表并确认。",
      usageStep2Body: "在天图内勾选需要的源表并确认；只有确认后才加载所选源表数据并绘制标记。",
      usageStep3Title: "选择目标和条件。",
      usageStep3Body: "选定目标源，设置时间范围与几何约束，再计算观测窗口。",
      usageStep4Title: "按范围解读结果。",
      usageStep4Body: "绿、黄、红只描述几何条件；天气、设备状态、机械条件和运行批准必须另行确认。",
      openPlanner: "打开天区与规划 →",
      catalogueGuideTitle: "源表介绍",
      catalogueGuideLabel: "单选一个源表查看适用范围",
      catalogueBoundaryLabel: "边界",
    },
    en: {
      skywardOverviewTitle: "About Skyward",
      skywardScopeStatement: "V0 reports explainable geometric-feasibility candidates only. It does not determine operational readiness or approve an observation.",
      currentStageLabel: "AVAILABLE NOW",
      currentStageTitle: "Current functions",
      currentStageBody: "Browse supported catalogues, inspect all-sky and local-field geometry and source details, and calculate centre and full-footprint windows under explicit geometric constraints.",
      goalStageLabel: "PRODUCT GOAL",
      goalStageTitle: "Explainable decision support",
      goalStageBody: "Provide read-only, reproducible and explainable evidence that helps an operator or scientist prepare an observing decision.",
      futureStageLabel: "FUTURE DEVELOPMENT",
      futureStageTitle: "Operational evidence not yet connected",
      futureStageBody: "Only after authoritative inputs and validation are available may future versions add live pointing and device telemetry, weather and atmosphere, mechanical trajectory limits, instrument availability, and joint-observation evidence.",
      usageTitle: "How to use Skyward",
      usageStep1Title: "Open the sky map.",
      usageStep1Body: "Return to “Sky map & planner” and open the catalogue selector inside the sky-map area.",
      usageStep2Title: "Select catalogue layers and confirm.",
      usageStep2Body: "Check the catalogues you need inside the sky map and confirm the selection. The page loads their data and draws their markers only after confirmation.",
      usageStep3Title: "Choose a target and conditions.",
      usageStep3Body: "Select a source, set the time range and geometric constraints, then calculate the windows.",
      usageStep4Title: "Interpret the result within scope.",
      usageStep4Body: "Green, yellow and red describe geometry only. Check weather, device state, mechanics and operating approval separately.",
      openPlanner: "Open Sky map & planner →",
      catalogueGuideTitle: "Catalogue guide",
      catalogueGuideLabel: "Select one catalogue to read its scope",
      catalogueBoundaryLabel: "Boundary",
    },
  };

  const catalogues = {
    "2lhaaso": {
      name: "2LHAASO",
      zh: {
        count: "本地已安装 190 条记录",
        summary: "用于源检索和几何计算；保留源表坐标与 extension 字段。",
        boundary: "190 是源表记录数，不代表 190 个互不重复的物理天体；extension 只作为名义圆半径参与仅几何判断。",
      },
      en: {
        count: "190 installed records",
        summary: "Used for source search and geometry calculations while preserving catalogue coordinates and extension fields.",
        boundary: "190 is a row count, not a claim of 190 distinct physical objects. Extension is used only as a nominal circular radius in the geometry-only model.",
      },
    },
    "fermi-fl16y": {
      name: "Fermi FL16Y",
      zh: {
        count: "本地已安装 7,224 条记录",
        summary: "用于检索 Fermi-LAT FL16Y 条目及显示其源表位置和原始字段。",
        boundary: "位置不确定度不等于物理延展；缺失的 footprint 保持未知，不能按 0 或“完整容纳”处理。",
      },
      en: {
        count: "7,224 installed records",
        summary: "Used to search Fermi-LAT FL16Y entries and display their catalogue positions and original fields.",
        boundary: "Localization uncertainty is not physical extension. A missing footprint remains unknown and is never treated as zero or fully contained.",
      },
    },
    "fermi-3fhl": {
      name: "Fermi 3FHL",
      zh: {
        count: "本地已安装 1,556 条记录",
        summary: "用于检索 3FHL 高能伽马射线源表条目及查看其位置和源表字段。",
        boundary: "定位误差不能代替 extension；footprint 未知时不评估完整源，除非用户明确提供名义半径。",
      },
      en: {
        count: "1,556 installed records",
        summary: "Used to search 3FHL high-energy gamma-ray catalogue entries and inspect their positions and catalogue fields.",
        boundary: "Localization error is not extension. When the footprint is unknown, the full footprint is not evaluated unless the operator explicitly supplies a nominal radius.",
      },
    },
    "tevcat": {
      name: "TeVCat",
      zh: {
        count: "本地快照 361 条 · 截止 2026-09-16",
        summary: "用于检索 TeVCat 候选事实快照中的甚高能伽马射线条目。",
        boundary: "包含候选分组，并非 361 个条目都已确认；361 个条目的硬 footprint 均未知，位置近邻关联也未升级为已确认关联。",
      },
      en: {
        count: "361-row snapshot · cutoff 2026-09-16",
        summary: "Used to search very-high-energy gamma-ray entries in the local TeVCat candidate-fact snapshot.",
        boundary: "Candidate groups are included and not all 361 entries are confirmed. All 361 hard footprints are unknown, and positional neighbours are not promoted to confirmed associations.",
      },
    },
    "gaia-dr3": {
      name: "Gaia DR3",
      zh: {
        count: "按需在线查询 · 默认 500 条/次 · 硬上限 2,000 条/次",
        summary: "在指定天区按需获取候选定标星；它不是预装的全表，也没有固定的本地记录总数。",
        boundary: "结果是有界无序子集，不是最亮 N 颗或代表性抽样；上游不可用时查询可能失败，候选星的定标适用性未评估。",
      },
      en: {
        count: "On-demand query · 500 rows by default · 2,000 hard maximum per request",
        summary: "Fetches candidate calibration stars on demand for a selected sky region; it is not a preinstalled full table and has no fixed local record total.",
        boundary: "The result is a bounded unordered subset, not the brightest N or a representative sample. Upstream queries can fail, and calibration suitability is not evaluated.",
      },
    },
  };

  const language = () => localStorage.getItem("skyward.language") === "en" ? "en" : "zh";

  const renderCatalogue = () => {
    const selected = catalogues[catalogueSelect.value] || catalogues["2lhaaso"];
    const text = selected[language()];
    document.getElementById("about-catalogue-name").textContent = selected.name;
    document.getElementById("about-catalogue-count").textContent = text.count;
    document.getElementById("about-catalogue-summary").textContent = text.summary;
    document.getElementById("about-catalogue-boundary").textContent = text.boundary;
  };

  const applyLanguage = () => {
    const text = copy[language()];
    document.querySelectorAll("[data-about-i18n]").forEach((element) => {
      const translated = text[element.dataset.aboutI18n];
      if (translated !== undefined) element.textContent = translated;
    });
    renderCatalogue();
  };

  catalogueSelect.addEventListener("change", renderCatalogue);
  document.addEventListener("skyward:language-change", applyLanguage);
  applyLanguage();
})();
