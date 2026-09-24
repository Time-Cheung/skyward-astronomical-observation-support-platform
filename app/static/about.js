/* About-page catalogue and scope copy. Uses the shared language preference
 * without extending the large application controller. */
(() => {
  const catalogueSelect = document.getElementById("about-catalogue-select");
  if (!catalogueSelect) return;

  const catalogueCounts = {};

  const copy = {
    zh: {
      skywardOverviewTitle: "Skyward 介绍",
      skywardScopeStatement: "V2.1 只给出可解释的几何可行性候选；不判断运行就绪状态，也不构成观测批准。",
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
      navigationNoteTitle: "返回已计算结果",
      navigationNoteBody: "从计算结果离开到数据说明或 API 时，当前浏览器标签页会保留已渲染的结果视图。通过“天区与规划”返回时直接恢复，不重新计算窗口，也不重新加载两幅图；直接刷新或浏览器存储不可用时才使用服务器正常重建。",
      observingPlanTitle: "观测计划",
      observingPlanBody: "完整源窗口区域只保留一组计划操作。每个可用窗口单独成行并默认勾选；点击加入后，所有已勾选窗口构成同一条目标计划。预览可分别修改各窗口时段，XLSX 为每个所选窗口写一条目标行，并把备选源记录在对应窗口下。用户可上传专用 CSV 备选源目录；上传后该计划只从该目录挑选备选源，否则使用当前已加载的普通源表。",
      observingPlanFormat: "下载工作簿使用纯黑色表头、黄色目标源行和绿色备选源行。文件仅在浏览器本地生成，观测计划不会上传到服务器。保存的观测窗口 SVG 含曲线图例；局部视场 SVG 使用亮色背景、目标编号 1 和源名图例。",
      catalogueGuideTitle: "源表介绍",
      catalogueGuideLabel: "单选一个源表查看适用范围",
      catalogueBoundaryLabel: "边界",
    },
    en: {
      skywardOverviewTitle: "About Skyward",
      skywardScopeStatement: "V2.1 reports explainable geometric-feasibility candidates only. It does not determine operational readiness or approve an observation.",
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
      navigationNoteTitle: "Return to a calculated result",
      navigationNoteBody: "When leaving a calculated result for Data notes or API, this browser tab keeps the rendered result view. Returning through Sky map & planner restores it without recalculating windows or reloading either map; a direct refresh or unavailable browser storage uses the normal server rebuild.",
      observingPlanTitle: "Observing plans",
      observingPlanBody: "The full-footprint section has one shared set of plan actions. Every valid window is a separate row and selected by default; adding creates one target plan containing all checked windows. Preview can edit each interval separately, and the XLSX writes one target row per selected window with alternatives under the corresponding window. A user-uploaded CSV can be selected as the exclusive alternative pool for that plan; otherwise the selected ordinary catalogues are used.",
      observingPlanFormat: "The downloaded workbook uses a solid black header, yellow target rows, and green alternative rows. It is generated only in the browser; no observing plan is uploaded to the server. Saved observing-window SVGs include comparison-curve legends; saved local-FoV SVGs use a light background, target ID 1, and a source-name legend.",
      catalogueGuideTitle: "Catalogue guide",
      catalogueGuideLabel: "Select one catalogue to read its scope",
      catalogueBoundaryLabel: "Boundary",
    },
  };

  const catalogues = {
    "1lhaaso": {
      name: "1LHAASO",
      zh: {
        count: "本地记录数由源表接口提供",
        summary: "公开论文 Table 2 的 90 个源用于检索和几何计算；保留 180 个 WCDA/KM2A 组件的坐标、r39、谱参数、上限和出处。",
        boundary: "r39 是二维高斯模型的 39% containment radius；测得扩展的误差为 1σ 统计误差，点源上限为 95% 置信上限。它不是硬边界，Table 2 关联项也只是论文的初步位置对应体；1LHAASO 因此按未知 footprint 的点源回退计算并保留警告。2LHAASO 尚未公开，不在本版本中提供或加载，临时上传也不能使用该保留名。",
      },
      en: {
        count: "Installed row count is provided by the catalogue API",
        summary: "The 90 public paper Table 2 sources support search and geometry; all 180 WCDA/KM2A component coordinates, r39 values, spectral fields, limits, and provenance are retained.",
        boundary: "Table 2 r39 is a 39% containment radius of a fitted two-dimensional Gaussian; measured-extension errors are 1-sigma statistical uncertainties and pointlike-source limits are at 95% confidence. It is not a hard boundary, and Table 2 associations are preliminary positional counterparts rather than Skyward-verified identities. 1LHAASO uses the explicit unknown-footprint fallback. The unpublished 2LHAASO catalogue is not shipped or served, and its reserved label is rejected for temporary uploads.",
      },
    },
    "fermi-fl16y": {
      name: "Fermi FL16Y",
      zh: {
        count: "本地记录数由源表接口提供",
        summary: "用于检索 Fermi-LAT FL16Y 条目及显示其源表位置和原始字段。",
        boundary: "位置不确定度不等于物理延展；缺失的 footprint 保持未知，不能按 0 或“完整容纳”处理。",
      },
      en: {
        count: "Installed row count is provided by the catalogue API",
        summary: "Used to search Fermi-LAT FL16Y entries and display their catalogue positions and original fields.",
        boundary: "Localization uncertainty is not physical extension. A missing footprint remains unknown and is never treated as zero or fully contained.",
      },
    },
    "fermi-3fhl": {
      name: "Fermi 3FHL",
      zh: {
        count: "本地记录数由源表接口提供",
        summary: "用于检索 3FHL 高能伽马射线源表条目及查看其位置和源表字段。",
        boundary: "定位误差不能代替 extension；footprint 未知时不评估完整源，除非用户明确提供名义半径。",
      },
      en: {
        count: "Installed row count is provided by the catalogue API",
        summary: "Used to search 3FHL high-energy gamma-ray catalogue entries and inspect their positions and catalogue fields.",
        boundary: "Localization error is not extension. When the footprint is unknown, the full footprint is not evaluated unless the operator explicitly supplies a nominal radius.",
      },
    },
    "tevcat": {
      name: "TeVCat",
      zh: {
        count: "本地快照 363 条 · 截止 2026-09-19",
        summary: "用于检索 TeVCat 候选事实快照中的甚高能伽马射线条目。",
        boundary: "223 条上游 Extended: No 记录按零半径点源处理；140 条 Extended: Yes 记录没有经核验的硬边界半径，保持未知 footprint。位置近邻不是已确认关联。",
      },
      en: {
        count: "363-row snapshot · cutoff 2026-09-19",
        summary: "Used to search very-high-energy gamma-ray entries in the local TeVCat candidate-fact snapshot.",
        boundary: "The 223 upstream Extended: No rows are zero-radius point sources. The 140 Extended: Yes rows without a verified hard-boundary radius retain unknown footprints. Positional neighbours are not confirmed associations.",
      },
    },
    "gaia-dr3": {
      name: "Gaia DR3",
      zh: {
        count: "按需在线查询 · 默认最近 10 条/次 · 硬上限 500 条/次",
        summary: "仅在计算结果页的局部视场图中，按目标中心 0.1–5° 范围按需获取候选定标星；默认半径 1°、最暗 G 星等 10、最多返回 10 颗，并按与目标的角距离由近到远选择。",
        boundary: "Gaia 不出现在全天图源表选择器或全天图图层中。局部十字按共享的实时/观测窗口/指定时间状态显示红或绿，但不判断定标适用性。查询结果在请求圆锥内按与目标的角距离由近到远排序并截取最近 N 颗；上游不可用时查询可能失败。",
      },
      en: {
        count: "On-demand query · 10 nearest rows by default · 500 hard maximum per request",
        summary: "Fetches candidate calibration stars only in the calculation result's local map, with a 0.1–5° radius. Defaults are 1°, faintest G=10 and 10 rows; returned rows are the nearest sources by angular distance to the target.",
        boundary: "Gaia does not appear in an all-sky catalogue picker or layer. Local crosses are red or green under the shared Real-time / Observation window / Specified time state, but calibration suitability is not evaluated. Rows are ordered by angular distance to the target and truncated to the nearest N sources by angular distance; upstream queries can fail.",
      },
    },
  };

  const language = () => localStorage.getItem("skyward.language") === "en" ? "en" : "zh";

  const renderCatalogue = () => {
    const selected = catalogues[catalogueSelect.value] || catalogues["1lhaaso"];
    const text = selected[language()];
    document.getElementById("about-catalogue-name").textContent = selected.name;
    const count = catalogueCounts[catalogueSelect.value];
    document.getElementById("about-catalogue-count").textContent = count === undefined ? text.count : (language() === "zh" ? String(Number(count).toLocaleString("zh-CN")) + " 条本地记录" : String(Number(count).toLocaleString("en-US")) + " installed records");
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
  fetch("/api/v1/catalogues").then((response) => response.ok ? response.json() : Promise.reject(new Error("HTTP " + response.status))).then((data) => {
    (data.catalogues || []).forEach((item) => { if (item.count !== undefined && item.count !== null) catalogueCounts[item.identifier] = item.count; });
    renderCatalogue();
  }).catch(() => { /* The static provenance copy remains available offline. */ });
})();
