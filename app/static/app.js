/*
 * Skyward display controller
 * ---------------------------
 * The application is LAN-only and deliberately uses no framework or external
 * assets. Theme and language choices are stored in localStorage, so each
 * operator keeps their own display preference without adding server accounts.
 */
(() => {
  const STORAGE_KEYS = Object.freeze({ theme: "skyward.theme", language: "skyward.language", timezone: "skyward.timezone" });
  const THEMES = ["auto", "light", "dark"];
  const TIMEZONES = Object.freeze({ local: "Asia/Shanghai", utc: "UTC" });

  const translations = {
    zh: {
      brandHome: "Skyward 首页", brandDescriptor: "天文观测辅助平台", primaryNavigation: "主导航", displaySettings: "显示设置",
      navPlanner: "天区与规划", navData: "数据说明", language: "语言", switchTheme: "切换主题", themeAuto: "自动", themeLight: "亮色", themeDark: "暗色", timezoneLocal: "北京: UTC+8", timezoneUtc: "UTC",
      site: "站点", altitude: "海拔", geometryOnly: "仅几何判断", calculationContext: "计算上下文", footerDisclaimer: "局域网原型。未评估天气、设备状态、机械安全或 LHAASO 联合观测条件。",
      currentSky: "当前天区", homeTitle: "从源表到可解释的几何窗口。", homeLead: "浏览 190 个 2LHAASO 源，设置日月与天顶角约束，并比较中心与完整源窗口。",
      skySummary: "天区摘要", catalogue: "源表", aboveHorizon: "地平线上", belowHorizon: "地平线下", inputValidation: "输入校验", calculationConditions: "计算条件", windowPlanner: "观测窗口规划", blankDisables: "不可留空",
      targetSource: "目标源", sourceSearchPlaceholder: "输入源名筛选，例如 J0534 或 Geminga", startTime: "开始时间", endTime: "结束时间", maximum31Days: "最长 1 天", optionalConstraints: "几何约束",
      sunMaxAltitude: "太阳最大高度角", sunPlaceholder: "例如 -18", sunConstraintHelp: "要求太阳高度 ≤ 此值", moonMinSeparation: "月亮最小角距", moonPlaceholder: "例如 30", moonConstraintHelp: "目标中心与月心角距",
      targetMinZenith: "目标最小天顶角", optional: "可留空", minZenithHelp: "避免过近天顶", targetMaxZenith: "目标最大天顶角", maxZenithPlaceholder: "例如 50", maxZenithHelp: "避免过近地平线",
      minimumWindow: "最短连续窗口", minimumWindowPlaceholder: "例如 1800", minimumWindowHelp: "0 表示不按持续时间筛除", calculateWindows: "计算窗口",
      horizonCoordinates: "地平坐标", allSkyTitle: "LACT 站点全天图", statusLegend: "状态图例", greenStatus: "完整源满足", yellowStatus: "中心满足，边缘不满足", redStatus: "中心不满足",
      allSkyNote: "图心是天顶和站点标记，不代表 LACT 当前实际机械光轴。点击星形查看源详情。", centreWindow: "中心窗口", centreWindowDescription: "源中心满足地平线和已启用约束。",
      fullWindow: "完整源窗口", fullWindowDescription: "名义 extension 完整落入 8.3°硬 FoV，并满足边缘约束。", secondBoundary: "秒级边界", secondBoundaryDescription: "粗采样定位约束交叉点，再将边界细化至 1 秒以内。",
      backToPlanner: "← 返回规划", windowResult: "窗口结果", displayTime: "显示时间", j2000Coordinates: "J2000 坐标", nominalExtension: "名义 extension", startingStatus: "起始状态", beijingTime: "北京时间", to: "至",
      centreWindows: "中心窗口", fullWindows: "完整源窗口", enabledConstraints: "启用约束", allSky: "全天图", green: "绿色", yellow: "黄色", red: "红色", pointingCentre: "指向中心", localFovTitle: "LACT 8.3°局部 FoV", hardBoundary: "硬边界",
      localFovNote: "灰色实线圆表示局部视场图的显示边界，蓝色虚线圆表示望远镜 FoV 硬边界，青色虚线圆表示目标源的名义 extension。名义 extension 很小时，青色圆可能被中央目标标记遮住而看不到。", conditionsOverTime: "条件随时间变化", plotTitle: "几何量与完整源窗口", plotHelp: "绿色背景表示完整源窗口",
      centreConditions: "中心条件", duration: "持续", minimumZenith: "最小天顶角", minimumMoonSeparation: "最小月距", noCentreWindows: "当前条件下没有中心窗口。", fullExtension: "完整 extension", maximumSunAltitude: "最大太阳高度", noFullWindows: "源中心可能满足，但名义 extension 没有完整窗口。",
      sourceDetails: "源详情", catalogueAndEnrichment: "2LHAASO 与待核验补充信息", openDetails: "打开详情", galacticCoordinates: "银河坐标", positionError: "95% 位置误差", astropyWarnings: "Astropy 警告",
      methodAndBoundary: "方法与边界", aboutTitle: "数据、坐标和几何模型。", aboutLead: "记录第一稿采用的固定参数、数据版本和刻意未纳入的观测条件。", lactSite: "LACT 站点", longitude: "经度", latitude: "纬度", timezone: "时区", source: "来源",
      diameter: "直径", radius: "半径", model: "模型", hardCircle: "理想圆形硬边界", notModelled: "未模拟", fovNotModelled: "离轴响应、PSF、遮挡和灵敏度衰减", catalogueTitle: "2LHAASO 源表", records: "记录数", coordinates: "坐标", extensionMeaning: "度，作为名义圆形半径",
      iersOffline: "IERS 离线数据", currentCoverage: "当前覆盖", autoDownload: "自动下载", disabled: "关闭", file: "文件", statusDefinition: "绿黄红状态", greenDefinition: "源中心及名义 extension 均满足地平线、启用约束和 8.3°硬 FoV。",
      yellowDefinition: "源中心满足，但 extension 边缘不能完整满足 FoV、地平线、天顶角或月距条件。", redDefinition: "源中心本身不满足基础地平线、太阳或启用的中心约束。", notEvaluated: "未评估条件", implemented: "已实现", notImplemented: "未实现", aboutDisclaimer: "计算结果不是正式观测批准。天气、设备状态、机械限位、跟踪误差和联合观测条件均未纳入。",
      jsonApi: "JSON 接口", apiTitle: "局域网 API 参考。", apiLead: "所有接口均无账号认证，只能在受控局域网中开放。交互式 Swagger 已禁用，避免浏览器加载公网 CDN；机器可读 schema 保留在 <code>/openapi.json</code>。", endpoints: "端点", windowRequestExample: "窗口请求示例", apiDisclaimer: "响应中的", apiDisclaimerEnd: "表示未评估天气、遥测、机械安全或联合观测条件。",
      apiDescription1: "源表、IERS 与补充数据健康状态", apiDescription2: "站点、FoV 与能力边界", apiDescription3: "检索 2LHAASO 源", apiDescription4: "源详情与指定时刻几何状态", apiDescription5: "全天图 SVG 与 190 源状态", apiDescription6: "中心和完整 footprint 观测窗口", apiDescription7: "机器可读 OpenAPI schema",
      loading: "载入中", closeDetails: "关闭详情", loadingDetail: "正在计算当前地平坐标和状态。", failedDetail: "无法载入源详情", noData: "暂无数据，待核验", centrePass: "源中心通过", centreFail: "源中心未通过", footprintPass: "完整 extension 通过", footprintFail: "完整 extension 未通过",
      sexagesimal: "时分秒 / 度分秒", extension: "Extension", positionErrorLabel: "95% 位置误差", altAzZenith: "高度 / 方位 / 天顶角", moonSeparation: "月亮角距", sunAltitude: "太阳高度", statusReasons: "状态原因", enrichment: "待核验扩展信息", verification: "核验状态", associatedSources: "关联源", sourceSearchEmpty: "没有匹配的源", allFieldsRequired: "所有项目必须填写", planningConstraints: "观测规划约束", sunConstraintLimited: "必须为 -15° 或更低", addTargetOption: "添加新目标", targetName: "目标名称", temporaryNamePlaceholder: "留空自动生成 TMP JHHMM±DDMM", temporaryNameHelp: "留空将根据 RA 和 Dec 自动生成 TMP JHHMM±DDMM 名称。", regionRa: "天区 RA（J2000）", regionDec: "天区 Dec（J2000）", regionRadius: "天区半径", skyMode: "全天图模式", liveSky: "实时，每分钟刷新", fixedSky: "指定时间", skyTime: "全天图时间", applySkyTime: "应用", localDateTime: "本地日期和时间", sunHorizonCoordinates: "太阳 高度 / 方位", moonHorizonCoordinates: "月亮 高度 / 方位", useForPlanner: "填入观测规划", replaceAndCalculate: "替换并重新计算", currentFovWindowResult: "当前望远镜视野", currentFovTitle: "当前望远镜视野内源的观测窗口。", currentFovLead: "在接入望远镜实时指向前，指向占位为天顶。仅计算所选开始时刻处于当前望远镜视野内的源。", fovSources: "视野内源", pointingMode: "指向", fixedZenith: "固定天顶", currentFovWindows: "当前视野窗口", noFovSources: "所选时刻的固定天顶视野内没有源", planObservation: "加入观测计划", observationPlan: "观测计划", plannedStart: "计划开始时间", plannedEnd: "计划结束时间", notes: "备注", planRangeHint: "默认填写当前完整源窗口中经逐秒复核有效的计划时间。计划时间必须留在该窗口内。", planRangeError: "计划时间必须位于当前完整源窗口内，且结束时间晚于开始时间。", planSecondUnavailable: "该窗口内没有可表示为完整秒的有效观测计划区间。", downloadPlan: "下载 TXT 计划表", planAdded: "已加入计划表", constraints: "约束条件",
    },
    en: {
      brandHome: "Skyward home", brandDescriptor: "ASTRONOMICAL OBSERVATION SUPPORT PLATFORM", primaryNavigation: "Primary navigation", displaySettings: "Display settings",
      navPlanner: "Sky map & planner", navData: "Data notes", language: "Language", switchTheme: "Switch theme", themeAuto: "Auto", themeLight: "Light", themeDark: "Dark", timezoneLocal: "Beijing: UTC+8", timezoneUtc: "UTC",
      site: "Site", altitude: "Altitude", geometryOnly: "GEOMETRY ONLY", calculationContext: "Calculation context", footerDisclaimer: "LAN prototype. Weather, device state, mechanical safety and LHAASO joint observation are not evaluated.",
      currentSky: "CURRENT SKY", homeTitle: "Turn a source catalogue into observable geometry.", homeLead: "Browse 190 2LHAASO sources, apply optional solar, lunar and zenith constraints, then compare centre and full-footprint windows.",
      skySummary: "Sky summary", catalogue: "Catalogue", aboveHorizon: "Above horizon", belowHorizon: "Below horizon", inputValidation: "Input validation", calculationConditions: "CALCULATION CONDITIONS", windowPlanner: "Window planner", blankDisables: "Cannot be blank",
      targetSource: "Target source", sourceSearchPlaceholder: "Filter by source name, e.g. J0534 or Geminga", startTime: "Start time", endTime: "End time", maximum31Days: "Maximum 1 day", optionalConstraints: "Geometric constraints",
      sunMaxAltitude: "Maximum Sun altitude", sunPlaceholder: "e.g. -18", sunConstraintHelp: "Require Sun altitude ≤ value", moonMinSeparation: "Minimum Moon separation", moonPlaceholder: "e.g. 30", moonConstraintHelp: "Between target centre and Moon",
      targetMinZenith: "Minimum target zenith angle", optional: "optional", minZenithHelp: "Avoid pointing too near zenith", targetMaxZenith: "Maximum target zenith angle", maxZenithPlaceholder: "e.g. 50", maxZenithHelp: "Avoid pointing too near horizon",
      minimumWindow: "Minimum continuous window", minimumWindowPlaceholder: "e.g. 1800", minimumWindowHelp: "0 keeps all durations", calculateWindows: "Calculate windows",
      horizonCoordinates: "HORIZON COORDINATES", allSkyTitle: "LACT all-sky view", statusLegend: "Status legend", greenStatus: "Full footprint passes", yellowStatus: "Centre passes, edge fails", redStatus: "Centre fails",
      allSkyNote: "The centre is zenith and the site marker, not LACT's actual mechanical pointing. Select a star for details.", centreWindow: "Centre window", centreWindowDescription: "The source centre passes horizon and enabled constraints.",
      fullWindow: "Full-footprint window", fullWindowDescription: "The nominal extension fits entirely within the 8.3° hard FoV and edge constraints.", secondBoundary: "Second-scale boundaries", secondBoundaryDescription: "Coarse samples locate crossings, then boundaries are refined to within one second.",
      backToPlanner: "← Back to planner", windowResult: "WINDOW RESULT", displayTime: "Display time", j2000Coordinates: "J2000 coordinates", nominalExtension: "Nominal extension", startingStatus: "Starting status", beijingTime: "Beijing time", to: "to",
      centreWindows: "Centre windows", fullWindows: "Full-footprint windows", enabledConstraints: "Enabled constraints", allSky: "All-sky map", green: "Green", yellow: "Yellow", red: "Red", pointingCentre: "POINTING CENTRE", localFovTitle: "LACT 8.3° local FoV", hardBoundary: "Hard boundary",
      localFovNote: "The grey solid circle is the local-map display boundary, the blue dashed circle is the telescope hard-FoV boundary, and the cyan dashed circle is the target nominal extension. A very small nominal extension can be hidden beneath the central target marker.", conditionsOverTime: "CONDITIONS OVER TIME", plotTitle: "Geometry and full-footprint windows", plotHelp: "Green shading marks full-footprint windows",
      centreConditions: "CENTRE CONDITIONS", duration: "Duration", minimumZenith: "Minimum zenith", minimumMoonSeparation: "Minimum Moon separation", noCentreWindows: "No centre windows under the current conditions.", fullExtension: "FULL EXTENSION", maximumSunAltitude: "Maximum Sun altitude", noFullWindows: "The centre may pass, but the nominal extension has no full-footprint window.",
      sourceDetails: "SOURCE DETAILS", catalogueAndEnrichment: "2LHAASO and unverified enrichment", openDetails: "Open details", galacticCoordinates: "Galactic coordinates", positionError: "95% position error", astropyWarnings: "Astropy warnings",
      methodAndBoundary: "METHOD & BOUNDARY", aboutTitle: "Data, coordinates and geometry.", aboutLead: "Fixed parameters, catalogue provenance and the conditions intentionally excluded from this first release.", lactSite: "LACT site", longitude: "Longitude", latitude: "Latitude", timezone: "Time zone", source: "Source",
      diameter: "Diameter", radius: "Radius", model: "Model", hardCircle: "Ideal circular hard boundary", notModelled: "Not modelled", fovNotModelled: "Off-axis response, PSF, obstruction or sensitivity falloff", catalogueTitle: "2LHAASO catalogue", records: "Records", coordinates: "Coordinates", extensionMeaning: "Degrees, used as a nominal circular radius",
      iersOffline: "Offline IERS data", currentCoverage: "Current coverage", autoDownload: "Automatic download", disabled: "Disabled", file: "File", statusDefinition: "Green, yellow and red", greenDefinition: "The source centre and nominal extension both pass horizon, enabled constraints and the 8.3° hard FoV.",
      yellowDefinition: "The centre passes, but an extension edge cannot fully meet FoV, horizon, zenith-angle or Moon-separation requirements.", redDefinition: "The centre itself fails the baseline horizon, solar or enabled centre constraints.", notEvaluated: "Not evaluated", implemented: "Implemented", notImplemented: "Not implemented", aboutDisclaimer: "This is not a formal observing approval. Weather, device state, mechanical limits, tracking error and joint-observation conditions are excluded.",
      jsonApi: "JSON API", apiTitle: "LAN API reference.", apiLead: "All endpoints are unauthenticated and must remain inside the controlled LAN. Interactive Swagger is disabled so a browser never tries to load a public CDN. The machine-readable schema remains at <code>/openapi.json</code>.", endpoints: "Endpoints", windowRequestExample: "Window request example", apiDisclaimer: "A response with", apiDisclaimerEnd: "does not evaluate weather, telemetry, mechanical safety or joint-observation conditions.",
      apiDescription1: "Catalogue, IERS and enrichment health", apiDescription2: "Site, FoV and capability boundaries", apiDescription3: "Search 2LHAASO sources", apiDescription4: "Source detail and geometry at a chosen time", apiDescription5: "All-sky SVG and 190 source states", apiDescription6: "Centre and full-footprint observing windows", apiDescription7: "Machine-readable OpenAPI schema",
      loading: "Loading", closeDetails: "Close details", loadingDetail: "Computing current horizon coordinates and status.", failedDetail: "Unable to load source details", noData: "No data, pending verification", centrePass: "Centre passes", centreFail: "Centre fails", footprintPass: "Full extension passes", footprintFail: "Full extension fails",
      sexagesimal: "Sexagesimal", extension: "Extension", positionErrorLabel: "95% position error", altAzZenith: "Alt / Az / Zenith", moonSeparation: "Moon separation", sunAltitude: "Sun altitude", statusReasons: "Status reasons", enrichment: "Unverified enrichment", verification: "Verification", associatedSources: "Associated sources", sourceSearchEmpty: "No matching sources", allFieldsRequired: "All fields are required", planningConstraints: "Planning constraints", sunConstraintLimited: "Must be -15° or below", addTargetOption: "Add new target", targetName: "Target name", temporaryNamePlaceholder: "Leave blank for TMP JHHMM±DDMM", temporaryNameHelp: "Leave blank to derive a TMP JHHMM±DDMM name from RA and Dec.", regionRa: "Region RA (J2000)", regionDec: "Region Dec (J2000)", regionRadius: "Region radius", skyMode: "Sky mode", liveSky: "Live, refresh each minute", fixedSky: "Specific time", skyTime: "Sky time", applySkyTime: "Apply", localDateTime: "Local date and time", sunHorizonCoordinates: "Sun Alt / Az", moonHorizonCoordinates: "Moon Alt / Az", useForPlanner: "Use for planning", replaceAndCalculate: "Replace and recalculate", currentFovWindowResult: "CURRENT TELESCOPE FoV", currentFovTitle: "Windows for sources in the current telescope FoV.", currentFovLead: "The pointing placeholder is zenith until telescope pointing telemetry is connected. Only sources inside the selected telescope FoV at the requested start time are evaluated.", fovSources: "FoV sources", pointingMode: "Pointing", fixedZenith: "Fixed zenith", currentFovWindows: "Current FoV windows", noFovSources: "No catalogue source lies inside the current fixed zenith FoV at the selected time.", planObservation: "Add to observing plan", observationPlan: "Observing plan", plannedStart: "Planned start", plannedEnd: "Planned end", notes: "Notes", planRangeHint: "The prefilled plan is checked at whole-second precision inside this full-footprint window. Planned times must stay within the valid interval.", planRangeError: "Planned times must lie inside this full-footprint window, with an end later than its start.", planSecondUnavailable: "No valid whole-second observing-plan interval exists within this window.", downloadPlan: "Download TXT plan", planAdded: "Added to plan", constraints: "Constraints",
    }
  };


  // API contracts keep machine codes; the local UI maps them to readable bilingual labels.
  Object.assign(translations.zh, {
    homeTitle: 'V0版本：仅几何判断', homeLead: '目前仅导入2LHAASO源表。', localFovTitle: '局部视场', allSkyTitle: '站点全天图',
    allSkyNote: '颜色由当前指向、望远镜硬视场和默认几何约束共同判定。实时指向尚未接入，当前固定为天顶；点击星形查看源详情。',
    telescopeSettings: '望远镜设置', telescope: '望远镜', lactTelescope: 'LACT', customTelescope: '自定义望远镜',
    telescopeFutureHelp: '当前已接入 LACT；后续可扩展其他望远镜。', customTelescopeHelp: '本次计算临时使用 WGS-84 配置，不会保存到服务器。',
    customLongitude: '经度（WGS-84）', customLatitude: '纬度（WGS-84）', customAltitude: '海拔', customTimezone: '本地 UTC 偏移', customFov: '望远镜视场直径',
    skyZoom: '全天图缩放', zoomIn: '放大', zoomOut: '缩小', zoomReset: '重置缩放',
    reasonAllPass: '所有已启用的几何条件均满足', reasonRangeStart: '请求时间范围起点', reasonRangeEnd: '请求时间范围终点', reasonBoundary: '约束边界', reasonBecameValid: '在以下条件恢复有效后', reasonBecameInvalid: '在以下条件失效后', reasonCentre: '源中心', reasonExtension: '源边缘',
    altAz: '高度 / 方位', addZenithOverlay: '添加 Zenith - Time 曲线', removeZenithOverlay: '撤回 Zenith - Time 曲线', savePlot: '保存几何量与完整源窗口图（SVG）', chooseZoomCentre: '指定缩放中心', resultStatusMode: '全天图状态', statusInstant: '实时', statusTrajectory: '观测窗口', instantStatusExplanation: '实时：绿色表示完整源在当前时刻可观测，黄色表示仅源中心可观测，红色表示源中心不可观测。', trajectoryStatusExplanation: '观测窗口：目标源完整源窗口内的可观测性；所有源、太阳和月亮统一显示在目标源第一个完整源窗口的起始时刻（无完整源窗口时使用计算开始时刻）的位置。', trackedFovSource: '跟踪视场内源', refreshRealtime: '更新实时全天图/视场图', localFovMode: '局部视场模式', zenithCurveManagement: 'Zenith-Time 曲线管理', curveColour: '曲线颜色', curveLineStyle: '曲线线形', removeCurve: '删除曲线', confirmAddPlan: '确认添加', downloadObservationPlan: '下载观测计划', duplicatePlanPrompt: '该源已存在计划记录。请选择覆盖之前的记录、作为新条目添加，或放弃本次添加。', duplicatePlanKicker: '重复计划', duplicatePlanTitle: '该源已有保存的观测计划', overwritePrevious: '覆盖', addAsNewEntry: '作为新条目添加', cancelAddition: '放弃添加', noSavedPlan: '尚未保存观测计划。', legendGreenMeaning: '完整源可观测', legendYellowMeaning: '仅源中心可观测', legendRedMeaning: '源中心不可观测', uploadCatalogue: '上传源表（CSV）', catalogueUploadHelp: 'UTF-8 CSV：必须包含 name、ra、dec；可选 ext。上传仅临时保存在内存中。', catalogueUploading: '正在上传源表', catalogueUploaded: '源表已加载', catalogueUploadFailed: '源表上传失败',
    target_above_horizon: '目标高于地平线', target_inside_current_fov: '目标在当前视场内', sun_altitude: '太阳高度角', moon_separation: '月亮角距', target_min_zenith: '目标最小天顶角', target_max_zenith: '目标最大天顶角', extension_inside_fov: '源扩展落入视场', extension_inside_current_fov: '源扩展落入当前视场', extension_above_horizon: '源扩展高于地平线', extension_max_zenith: '源扩展不超出地平线限制', minimum_window: '最短连续窗口',
  });
  Object.assign(translations.en, {
    homeTitle: 'V0: geometry assessment only', homeLead: 'Currently imported: the 2LHAASO source catalogue.', localFovTitle: 'local FoV', allSkyTitle: 'Station all-sky view',
    allSkyNote: 'Colours use the current pointing, telescope hard FoV and default geometric constraints. Pointing is fixed to zenith until telemetry is connected; select a star for details.',
    telescopeSettings: 'Telescope settings', telescope: 'Telescope', lactTelescope: 'LACT', customTelescope: 'Custom telescope',
    telescopeFutureHelp: 'LACT is active now; additional observatories can be connected later.', customTelescopeHelp: 'This temporary WGS-84 configuration is used only by this calculation and is not saved.',
    customLongitude: 'Longitude (WGS-84)', customLatitude: 'Latitude (WGS-84)', customAltitude: 'Altitude', customTimezone: 'Local UTC offset', customFov: 'Telescope FoV diameter',
    skyZoom: 'Sky map zoom', zoomIn: 'Zoom in', zoomOut: 'Zoom out', zoomReset: 'Reset zoom',
    reasonAllPass: 'All enabled geometry conditions pass', reasonRangeStart: 'Requested-range start', reasonRangeEnd: 'Requested-range end', reasonBoundary: 'Constraint boundary', reasonBecameValid: 'Became valid after', reasonBecameInvalid: 'Became invalid after', reasonCentre: 'Target centre', reasonExtension: 'Source edge',
    altAz: 'Alt / Az', addZenithOverlay: 'Add Zenith - Time curve', removeZenithOverlay: 'Remove Zenith - Time curve', savePlot: 'Save geometry and full-footprint plot (SVG)', chooseZoomCentre: 'Choose centre', resultStatusMode: 'Map status', statusInstant: 'Real-time', statusTrajectory: 'Observation window', instantStatusExplanation: 'Real-time: green means the full source is observable now, yellow means only its centre is observable, and red means its centre is unavailable.', trajectoryStatusExplanation: 'Observation window: observability inside the target full-footprint windows; all sources, Sun and Moon are shown at the target first full-footprint-window start, or the calculation start when none exists.', trackedFovSource: 'Tracked-FoV source', refreshRealtime: 'Refresh live all-sky / FoV maps', localFovMode: 'Local FoV mode', zenithCurveManagement: 'Zenith-Time curve management', curveColour: 'Curve colour', curveLineStyle: 'Curve line style', removeCurve: 'Remove curve', confirmAddPlan: 'Confirm addition', downloadObservationPlan: 'Download observing plan', duplicatePlanPrompt: 'A plan for this source already exists. Choose overwrite, add as a new entry, or cancel this addition.', duplicatePlanKicker: 'Duplicate plan', duplicatePlanTitle: 'This source already has a saved plan', overwritePrevious: 'Overwrite', addAsNewEntry: 'Add as new entry', cancelAddition: 'Cancel addition', noSavedPlan: 'No observing plan has been saved.', legendGreenMeaning: 'Full source observable', legendYellowMeaning: 'Centre only', legendRedMeaning: 'Centre unavailable', uploadCatalogue: 'Upload source catalogue (CSV)', catalogueUploadHelp: 'UTF-8 CSV: name, ra, dec are required; ext is optional. Uploads are temporary and stored only in memory.', catalogueUploading: 'Uploading catalogue', catalogueUploaded: 'Catalogue loaded', catalogueUploadFailed: 'Catalogue upload failed',
    target_above_horizon: 'target above horizon', target_inside_current_fov: 'target inside current FoV', sun_altitude: 'Sun altitude', moon_separation: 'Moon separation', target_min_zenith: 'minimum target zenith angle', target_max_zenith: 'maximum target zenith angle', extension_inside_fov: 'extension inside FoV', extension_inside_current_fov: 'extension inside current FoV', extension_above_horizon: 'extension above horizon', extension_max_zenith: 'extension within horizon limit', minimum_window: 'minimum continuous window',
  });
  const formatCondition = (code) => translate(code, String(code || '').replaceAll('_', ' '));
  const formatReason = (code) => {
    const value = String(code || '');
    if (value === 'all_enabled_geometry_conditions_pass') return translate('reasonAllPass');
    if (value === 'range_start') return translate('reasonRangeStart');
    if (value === 'range_end') return translate('reasonRangeEnd');
    if (value === 'constraint_boundary') return translate('reasonBoundary');
    if (value.startsWith('became_valid_after: ')) return translate('reasonBecameValid') + ': ' + value.slice(20).split(', ').map(formatCondition).join(', ');
    if (value.startsWith('became_invalid_after: ')) return translate('reasonBecameInvalid') + ': ' + value.slice(22).split(', ').map(formatCondition).join(', ');
    if (value === 'center_cannot_hold_for_minimum_window') return translate('reasonCentre') + ': ' + translate('minimum_window');
    if (value === 'extension_cannot_hold_for_minimum_window') return translate('reasonExtension') + ': ' + translate('minimum_window');
    if (value.startsWith('center_')) return translate('reasonCentre') + ': ' + formatCondition(value.slice(7));
    if (value === 'extension_edge_exceeds_fov') return translate('reasonExtension') + ': ' + translate('extension_inside_fov');
    if (value === 'extension_edge_exceeds_current_fov') return translate('reasonExtension') + ': ' + translate('extension_inside_current_fov');
    if (value === 'extension_edge_below_horizon') return translate('reasonExtension') + ': ' + translate('extension_above_horizon');
    if (value === 'extension_edge_exceeds_horizon_limit') return translate('reasonExtension') + ': ' + translate('extension_max_zenith');
    if (value.startsWith('extension_edge_')) return translate('reasonExtension') + ': ' + formatCondition(value.slice(15));
    return value.replaceAll('_', ' ');
  };
  const refreshReasonText = () => document.querySelectorAll('[data-reason-codes]').forEach((element) => {
    const codes = (element.dataset.reasonCodes || '').split('|').filter(Boolean);
    element.textContent = codes.map(formatReason).join(' · ') || '—';
  });

  let refreshTimeDisplays = () => {};
  const getLanguage = () => localStorage.getItem(STORAGE_KEYS.language) || "zh";
  const getThemePreference = () => localStorage.getItem(STORAGE_KEYS.theme) || "auto";
  const getTimezonePreference = () => localStorage.getItem(STORAGE_KEYS.timezone) || "local";
  const resultTelescopeContext = () => document.getElementById("detail-query-context");
  const isCustomTelescope = () => (document.getElementById("telescope_mode")?.value || resultTelescopeContext()?.dataset.telescopeMode) === "custom";
  const observerOffsetHours = () => {
    const contextValue = resultTelescopeContext()?.dataset.customTimezoneOffsetHours;
    const value = Number(document.getElementById("custom_timezone_offset_hours")?.value ?? contextValue);
    return isCustomTelescope() && Number.isFinite(value) ? value : 8;
  };
  const displayTimezone = () => {
    if (getTimezonePreference() === "utc") return "UTC";
    if (!isCustomTelescope()) return TIMEZONES.local;
    const offset = observerOffsetHours(); const sign = offset >= 0 ? "+" : "-";
    const absolute = Math.abs(offset); const hours = Math.floor(absolute); const minutes = Math.round((absolute - hours) * 60);
    return sign + String(hours).padStart(2, "0") + ":" + String(minutes).padStart(2, "0");
  };
  const observerTimezoneLabel = () => {
    const offset = observerOffsetHours();
    const sign = offset >= 0 ? "+" : "-";
    const absolute = Math.abs(offset);
    const hours = Math.floor(absolute);
    const minutes = Math.round((absolute - hours) * 60);
    return `UTC${sign}${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
  };
  const translate = (key, fallback = "") => translations[getLanguage()]?.[key] ?? fallback;

  const timezoneLabel = () => {
    if (getTimezonePreference() === "utc") return translate("timezoneUtc", "UTC");
    return isCustomTelescope() ? observerTimezoneLabel() : translate("timezoneLocal", "Beijing: UTC+8");
  };
  const updateLocalTimezoneOption = () => {
    const option = document.querySelector('#timezone-select option[value="local"]');
    if (option) option.textContent = isCustomTelescope() ? observerTimezoneLabel() : translate("timezoneLocal", "Beijing: UTC+8");
  };

  const dateFormatter = (options = {}) => new Intl.DateTimeFormat(
    getLanguage() === "zh" ? "zh-CN" : "en-CA",
    { timeZone: displayTimezone(), ...options },
  );

  const updatePlotTimezoneLabels = () => {
    document.querySelectorAll("[data-plot-timezone]").forEach((plot) => {
      plot.setAttribute("data-display-timezone", timezoneLabel());
    });
  };

  const formatDisplayTime = (value, options = { dateStyle: "medium", timeStyle: "medium" }) => {
    const date = value instanceof Date ? value : new Date(value);
    if (getTimezonePreference() !== "utc" && isCustomTelescope()) {
      const shifted = new Date(date.getTime() + observerOffsetHours() * 3600_000);
      return new Intl.DateTimeFormat(getLanguage() === "zh" ? "zh-CN" : "en-CA", { timeZone: "UTC", ...options }).format(shifted);
    }
    return dateFormatter(options).format(date);
  };

  const applyLanguage = (language) => {
    const selected = translations[language] ? language : "zh";
    localStorage.setItem(STORAGE_KEYS.language, selected);
    document.documentElement.lang = selected === "zh" ? "zh-CN" : "en";
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const key = element.dataset.i18n;
      const text = translations[selected][key];
      if (text !== undefined) element.innerHTML = text;
    });
    updatePlotTimezoneLabels();
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      const text = translations[selected][element.dataset.i18nPlaceholder];
      if (text !== undefined) element.setAttribute("placeholder", text);
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
      const text = translations[selected][element.dataset.i18nAriaLabel];
      if (text !== undefined) element.setAttribute("aria-label", text);
    });
    document.querySelectorAll("[data-i18n-title]").forEach((element) => {
      const text = translations[selected][element.dataset.i18nTitle];
      if (text !== undefined) element.setAttribute("title", text);
    });
    const selector = document.getElementById("language-select");
    if (selector) selector.value = selected;
    updateLocalTimezoneOption();
    document.querySelectorAll("[data-timezone-label]").forEach((element) => { element.textContent = timezoneLabel(); });
    refreshTimeDisplays();
    refreshReasonText();
    document.dispatchEvent(new Event("skyward:language-change"));
    updateThemeButton();
  };

  const resolvedTheme = (theme) => theme === "auto"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : theme;

  const updateThemeButton = () => {
    const button = document.getElementById("theme-toggle");
    if (!button) return;
    const theme = document.documentElement.dataset.theme || "auto";
    button.querySelector(".theme-label").textContent = translate(`theme${theme[0].toUpperCase()}${theme.slice(1)}`, theme);
    button.querySelector(".theme-icon").textContent = resolvedTheme(theme) === "dark" ? "◐" : "◑";
    button.setAttribute("aria-pressed", String(theme === "dark"));
  };

  const applyTheme = (theme, { notify = true, persist = true } = {}) => {
    const selected = THEMES.includes(theme) ? theme : "auto";
    const previousTheme = document.documentElement.dataset.theme;
    const previousResolved = document.documentElement.dataset.resolvedTheme;
    if (persist) localStorage.setItem(STORAGE_KEYS.theme, selected);
    document.documentElement.dataset.theme = selected;
    document.documentElement.dataset.resolvedTheme = resolvedTheme(selected);
    document.documentElement.style.colorScheme = selected === "auto" ? "light dark" : selected;
    updateThemeButton();
    if (notify && (previousTheme !== selected || previousResolved !== document.documentElement.dataset.resolvedTheme)) {
      document.dispatchEvent(new CustomEvent("skyward:theme-change", { detail: { theme: selected } }));
    }
  };

  const applyTimezone = (preference, { notify = true } = {}) => {
    const selected = Object.hasOwn(TIMEZONES, preference) ? preference : "local";
    const previous = getTimezonePreference();
    // Let datetime-local controls capture unsaved wall-clock edits before the
    // preference changes, so Beijing and UTC are never confused as instants.
    if (notify && previous !== selected) {
      document.dispatchEvent(new CustomEvent("skyward:timezone-will-change", { detail: { previous, timezone: selected } }));
    }
    localStorage.setItem(STORAGE_KEYS.timezone, selected);
    const selector = document.getElementById("timezone-select");
    if (selector) selector.value = selected;
    updateLocalTimezoneOption();
    document.querySelectorAll("[data-timezone-label]").forEach((element) => { element.textContent = timezoneLabel(); });
    updatePlotTimezoneLabels();
    if (notify && previous !== selected) document.dispatchEvent(new CustomEvent("skyward:timezone-change", { detail: { previous, timezone: selected } }));
  };

  const initialiseDisplaySettings = () => {
    const initialTheme = getThemePreference();
    applyTheme(initialTheme, { persist: false, notify: false });
    applyTimezone(getTimezonePreference(), { notify: false });
    applyLanguage(getLanguage());
    document.getElementById("language-select")?.addEventListener("change", (event) => applyLanguage(event.target.value));
    document.getElementById("timezone-select")?.addEventListener("change", (event) => applyTimezone(event.target.value));
    document.getElementById("theme-toggle")?.addEventListener("click", () => {
      const current = document.documentElement.dataset.theme || "auto";
      applyTheme(THEMES[(THEMES.indexOf(current) + 1) % THEMES.length]);
    });
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if ((document.documentElement.dataset.theme || "auto") === "auto") {
        document.documentElement.dataset.resolvedTheme = resolvedTheme("auto");
        updateThemeButton();
        document.dispatchEvent(new CustomEvent("skyward:theme-change", { detail: { theme: "auto" } }));
      }
    });
  };

  const dialog = document.getElementById("source-dialog");
  const dialogTitle = document.getElementById("dialog-title");
  const dialogBody = document.getElementById("dialog-body");
  const dialogUseSource = document.getElementById("dialog-use-source");
  const dialogAddZenith = document.getElementById("dialog-add-zenith");

  // API fields are data, not markup. Escape every dynamic value before adding it
  // to the dialog template, including locally curated enrichment records.
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

  const displayValue = (value) => {
    if (value === null || value === undefined || value === "") return translate("noData");
    if (Array.isArray(value)) return value.length ? value.join(", ") : translate("noData");
    return String(value);
  };

  const appendTelescopeParameters = (params, context = null) => {
    const from = (dataset, input) => context?.dataset?.[dataset] ?? document.getElementById(input)?.value;
    const mode = from('telescopeMode', 'telescope_mode') || 'lact';
    params.set('telescope_mode', mode);
    // Preserve a short-lived upload token with every request that needs the selected catalogue.
    const catalogueToken = context?.dataset?.catalogToken ?? document.getElementById('catalog-token-input')?.value;
    if (catalogueToken) params.set('catalog_token', catalogueToken);
    if (mode !== 'custom') return params;
    const fields = [
      ['customLongitudeDeg', 'custom_longitude_deg'], ['customLatitudeDeg', 'custom_latitude_deg'],
      ['customAltitudeM', 'custom_altitude_m'], ['customTimezoneOffsetHours', 'custom_timezone_offset_hours'],
      ['customFovDiameterDeg', 'custom_fov_diameter_deg'],
    ];
    fields.forEach(([dataset, input]) => { const value = from(dataset, input); if (value !== undefined && value !== '') params.set(input, value); });
    return params;
  };

  // The all-sky panel may be inspecting a fixed instant that differs from the
  // planner's start field. Preserve that instant for source-detail requests so
  // a clicked marker and its dialog always describe the same sky state.
  let activeSkyInstant = null;

  const activeParameters = () => {
    const context = document.getElementById("detail-query-context");
    if (context) {
      const params = new URLSearchParams();
      const mapping = { atTime: "at_time", sunMaxAltitudeDeg: "sun_max_altitude_deg", moonMinSeparationDeg: "moon_min_separation_deg", targetMinZenithDeg: "target_min_zenith_deg", targetMaxZenithDeg: "target_max_zenith_deg", minimumWindowSeconds: "minimum_window_seconds" };
      Object.entries(mapping).forEach(([key, parameter]) => {
        const value = context.dataset[key];
        if (value !== undefined && value !== "") params.set(parameter, value);
      });
      if (activeSkyInstant) params.set("at_time", activeSkyInstant.toISOString());
      return appendTelescopeParameters(params, context);
    }
    const ids = ["sun_max_altitude_deg", "moon_min_separation_deg", "target_min_zenith_deg", "target_max_zenith_deg", "minimum_window_seconds"];
    const params = new URLSearchParams();
    const canonicalStart = document.getElementById("planner-start-utc")?.value;
    const startInput = document.getElementById("start_time");
    // Use the current wall-clock form value so source details honor an
    // operator's unsaved date/time edits. Fall back to the canonical initial
    // instant only when no planner input is available.
    if (activeSkyInstant) params.set("at_time", activeSkyInstant.toISOString());
    else if (startInput?.value) params.set("at_time", selectedInputDate(startInput).toISOString());
    else if (canonicalStart) params.set("at_time", canonicalStart);
    ids.forEach((id) => {
      const element = document.getElementById(id);
      if (!element?.value) return;
      params.set(id, element.value);
    });
    return appendTelescopeParameters(params);
  };

  const statusClass = (status) => String(status || "RED").toLowerCase();

  const detailMarkup = (data) => {
    const status = data.status || {}, geometry = status.geometry || {}, enrichment = data.enrichment || {}, reasons = status.reasons || [];
    const centreLabel = status.center_pass ? translate("centrePass") : translate("centreFail");
    const footprintLabel = status.footprint_pass ? translate("footprintPass") : translate("footprintFail");
    const measured = (value, digits = 3) => (value === null || value === undefined || value === "")
      ? escapeHtml(translate("noData")) : Number(value).toFixed(digits) + "°";
    const extension = Number(data.ext).toFixed(3) + "°";
    const extensionError = data.ext_err === null || data.ext_err === undefined
      ? escapeHtml(translate("noData")) : Number(data.ext_err).toFixed(3) + "°";
    return `
      <div class="detail-status"><span class="status-chip ${statusClass(status.status)}">${escapeHtml(status.status)}</span><span>${escapeHtml(centreLabel)} / ${escapeHtml(footprintLabel)}</span></div>
      <dl class="detail-grid">
        <div><dt>RA / Dec (${escapeHtml(data.coordinate_frame)})</dt><dd>${Number(data.ra).toFixed(3)}°, ${Number(data.dec).toFixed(3)}°</dd></div>
        <div><dt>${escapeHtml(translate("galacticCoordinates"))}</dt><dd>${Number(data.l).toFixed(3)}°, ${Number(data.b).toFixed(3)}°</dd></div>
        <div><dt>${escapeHtml(translate("extension"))}</dt><dd>${extension} ± ${extensionError}</dd></div>
        <div><dt>${escapeHtml(translate("positionErrorLabel"))}</dt><dd>${measured(data["p_err(95%)"])}</dd></div>
        <div><dt>${escapeHtml(translate("altAz"))}</dt><dd>${Number(geometry.target_altitude_deg).toFixed(2)}° / ${Number(geometry.target_azimuth_deg).toFixed(2)}°</dd></div>
        <div><dt>${escapeHtml(translate("moonSeparation"))}</dt><dd>${Number(geometry.moon_separation_deg).toFixed(2)}°</dd></div>
        <div><dt>${escapeHtml(translate("sunAltitude"))}</dt><dd>${Number(geometry.sun_altitude_deg).toFixed(2)}°</dd></div>
      </dl>
      <section class="detail-section"><h3>${escapeHtml(translate("statusReasons"))}</h3><ul class="reason-list">${reasons.map((reason) => `<li>${escapeHtml(formatReason(reason))}</li>`).join("")}</ul></section>
      <section class="detail-section"><h3>${escapeHtml(translate("enrichment"))}</h3><dl class="detail-grid">
        <div><dt>Spectral model</dt><dd>${escapeHtml(displayValue(enrichment.spectral_model))}</dd></div>
        <div><dt>Spatial model</dt><dd>${escapeHtml(displayValue(enrichment.spatial_model))}</dd></div>
        <div><dt>Distance</dt><dd>${escapeHtml(displayValue(enrichment.distance))}</dd></div>
        <div><dt>${escapeHtml(translate("associatedSources"))}</dt><dd>${escapeHtml(displayValue(enrichment.associated_sources))}</dd></div>
        <div><dt>TeVCat</dt><dd>${enrichment.tevcat_url ? `<a href="${escapeHtml(enrichment.tevcat_url)}" rel="noreferrer">${escapeHtml(enrichment.tevcat_name || "TeVCat")}</a>` : escapeHtml(translate("noData"))}</dd></div>
        <div><dt>${escapeHtml(translate("verification"))}</dt><dd>${escapeHtml(displayValue(enrichment.verification_status))}</dd></div>
      </dl></section>`;
  };

  const zenithOverlayIndexes = new Set();
  const overlayPalette = ["#ff8c42", "#8b5cf6", "#00a6a6", "#d14f9b", "#8a9a22", "#7a6ff0"];
  const zenithOverlayStyles = new Map();
  const overlayStyle = (index) => {
    if (!zenithOverlayStyles.has(Number(index))) {
      zenithOverlayStyles.set(Number(index), { colour: overlayPalette[zenithOverlayStyles.size % overlayPalette.length], lineStyle: "dashdot", label: "Source " + index });
    }
    return zenithOverlayStyles.get(Number(index));
  };

  const openSource = async (sourceIndex) => {
    if (!dialog) return;
    dialogTitle.textContent = translate("loading");
    dialogUseSource.hidden = true;
    dialogUseSource.dataset.useSource = "";
    if (dialogAddZenith) dialogAddZenith.hidden = true;
    dialogBody.innerHTML = `<p class="dialog-loading">${escapeHtml(translate("loadingDetail"))}</p>`;
    dialog.showModal();
    try {
      const detailParameters = activeParameters();
      const windowMode = document.getElementById('result-status-mode')?.value === 'trajectory';
      detailParameters.set("enforce_current_pointing", windowMode ? "false" : "true");
      const response = await fetch('/api/v1/sources/' + sourceIndex + '?' + detailParameters.toString(), { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      dialogTitle.textContent = data.display_name;
      dialogUseSource.dataset.useSource = String(data.index);
      // The dialog button fills the planner on the homepage or replaces the
      // selected target on an individual result page. Bulk results expose
      // neither route, so do not show an action that cannot be completed.
      dialogUseSource.hidden = !(
        document.getElementById("source_index")
        || document.getElementById("replace-source-form")
      );
      dialogBody.innerHTML = detailMarkup(data);
      const resultTarget = document.getElementById("detail-query-context")?.dataset.resultSourceIndex;
      if (dialogAddZenith) {
        dialogAddZenith.hidden = !(resultTarget !== undefined && resultTarget !== String(data.index) && !zenithOverlayIndexes.has(data.index));
        dialogAddZenith.onclick = async () => {
          zenithOverlayIndexes.add(data.index);
          overlayStyle(data.index).label = data.display_name;
          await refreshZenithOverlays();
          dialogAddZenith.hidden = true;
        };
      }
    } catch (error) {
      dialogTitle.textContent = translate("failedDetail");
      dialogBody.innerHTML = `<p class="dialog-error">${escapeHtml(error.message)}</p>`;
    }
  };

  const useSourceForPlanner = (sourceIndex) => {
    const plannerSelect = document.getElementById("source_index");
    if (plannerSelect) {
      plannerSelect.value = String(sourceIndex);
      plannerSelect.dispatchEvent(new Event("change", { bubbles: true }));
      dialog?.close();
      plannerSelect.scrollIntoView({ behavior: "smooth", block: "center" });
      plannerSelect.focus();
      return;
    }
    const replacementForm = document.getElementById("replace-source-form");
    if (replacementForm) {
      replacementForm.elements.source_index.value = String(sourceIndex);
      // Keep original result instants explicit. This matters for the legacy
      // bulk page because its visible values are Beijing wall time while an
      // operator may switch the header to UTC before replacing a source.
      const resultContext = document.querySelector("[data-result-time-context]");
      if (resultContext?.dataset.startUtc && replacementForm.elements.start_time) replacementForm.elements.start_time.value = resultContext.dataset.startUtc;
      if (resultContext?.dataset.endUtc && replacementForm.elements.end_time) replacementForm.elements.end_time.value = resultContext.dataset.endUtc;
      // Preserve the browser preference when replacing a target on a result
      // page. The resolved palette is a separate server-rendering concern.
      if (replacementForm.elements.display_theme) replacementForm.elements.display_theme.value = getThemePreference();
      if (replacementForm.elements.plot_theme) replacementForm.elements.plot_theme.value = document.documentElement.dataset.resolvedTheme || "light";
      if (replacementForm.elements.display_timezone) replacementForm.elements.display_timezone.value = getTimezonePreference();
      replacementForm.requestSubmit();
    }
  };

  const initialiseResultDisplayPreferences = () => {
    const preferences = document.getElementById("result-display-preferences");
    if (!preferences) return;
    // LocalStorage is the per-operator preference source. Server attributes
    // describe only how this already-rendered plot was painted.
    applyTheme(getThemePreference(), { persist: false, notify: false });
    applyTimezone(getTimezonePreference(), { notify: false });
  };

  const initialiseResultThemePlot = () => {
    const preferences = document.getElementById("result-display-preferences");
    const plot = document.querySelector("[data-plot-timezone]");
    if (!preferences || !plot) return;
    const palettes = {
      light: { figure: "#f7f7f8", axes: "#ffffff", edge: "#9fa6b2", text: "#151820", tick: "#4f5865", grid: "#d6dae1", target: "#3333ff", sun: "#c65d10", moon: "#4e5968", threshold: "#9a6500", window: "#197447" },
      dark: { figure: "#0c1117", axes: "#111923", edge: "#4c5a68", text: "#e8eef4", tick: "#b9c5d1", grid: "#344250", target: "#73b7ff", sun: "#e4852f", moon: "#d2d9e2", threshold: "#d7a93c", window: "#3fa86b" },
    };
    const colourMap = (from, to) => new Map(Object.keys(from).map((key) => [from[key].toLowerCase(), to[key]]));
    const recolourPlot = () => {
      const svg = plot.querySelector("svg"); if (!svg) return;
      const desired = document.documentElement.dataset.resolvedTheme === "dark" ? "dark" : "light";
      const current = preferences.dataset.plotTheme === "dark" ? "dark" : "light";
      if (desired === current) return;
      const replacements = colourMap(palettes[current], palettes[desired]);
      svg.querySelectorAll("[style]").forEach((element) => {
        if (element.closest('[id^="zenith-overlay-"]')) return;
        let style = element.getAttribute("style");
        replacements.forEach((replacement, colour) => { style = style.replaceAll(colour, replacement); });
        element.setAttribute("style", style);
      });
      preferences.dataset.plotTheme = desired;
    };
    window.queueMicrotask(recolourPlot);
    document.addEventListener("skyward:theme-change", recolourPlot);
    const relabelTimezone = () => {
      const svg = plot.querySelector('svg'); if (!svg) return;
      const offset = getTimezonePreference() === 'utc' ? 0 : observerOffsetHours();
      const labels = [...svg.querySelectorAll('text')];
      const xLabel = labels.find((label) => label.textContent === preferences.dataset.plotTimezoneLabel);
      for (let index = 0; index < labels.length - 1; index += 1) {
        if (!/^\d{2}-\d{2}$/.test(labels[index].textContent || '') || !/^\d{2}:\d{2}$/.test(labels[index + 1].textContent || '')) continue;
        const [month, day] = labels[index].textContent.split('-').map(Number);
        const [hour, minute] = labels[index + 1].textContent.split(':').map(Number);
        const shifted = new Date(Date.UTC(2000, month - 1, day, hour - Number(preferences.dataset.plotOffsetHours || 0), minute) + offset * 3600_000);
        labels[index].textContent = String(shifted.getUTCMonth() + 1).padStart(2, '0') + '-' + String(shifted.getUTCDate()).padStart(2, '0');
        labels[index + 1].textContent = String(shifted.getUTCHours()).padStart(2, '0') + ':' + String(shifted.getUTCMinutes()).padStart(2, '0');
      }
      const label = getTimezonePreference() === 'utc' ? 'UTC' : observerTimezoneLabel();
      if (xLabel) xLabel.textContent = label;
      preferences.dataset.plotTimezoneLabel = label; preferences.dataset.plotOffsetHours = String(offset);
    };
    preferences.dataset.plotTimezoneLabel = preferences.dataset.timezone === 'utc' ? 'UTC' : observerTimezoneLabel();
    preferences.dataset.plotOffsetHours = String(preferences.dataset.timezone === 'utc' ? 0 : observerOffsetHours());
    document.addEventListener("skyward:timezone-change", relabelTimezone);
  };

  const initialiseSourceDialog = () => {
    document.addEventListener("click", (event) => {
      const marker = event.target.closest("[data-source-index]");
      const explicit = event.target.closest("[data-open-source]");
      const useSource = event.target.closest("[data-use-source]") || (event.target.closest("#dialog-use-source")?.dataset.useSource ? event.target.closest("#dialog-use-source") : null);
      const replaceSource = event.target.closest("[data-replace-source]");
      if (useSource) useSourceForPlanner(useSource.dataset.useSource);
      else if (replaceSource) useSourceForPlanner(replaceSource.dataset.replaceSource);
      else if (explicit) openSource(explicit.dataset.openSource);
      else if (marker) openSource(marker.dataset.sourceIndex);
      if (event.target.closest("[data-close-dialog]")) dialog?.close();
    });
    document.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === " ") && event.target.matches("[data-source-index]")) { event.preventDefault(); openSource(event.target.dataset.sourceIndex); }
    });
    dialog?.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  };

  const temporaryTargetName = (ra, dec) => {
    const parsedRa = Number(ra);
    const parsedDec = Number(dec);
    if (!Number.isFinite(parsedRa) || !Number.isFinite(parsedDec)) return "";
    const raMinutes = Math.floor((((parsedRa % 360) + 360) % 360) / 15 * 60) % (24 * 60);
    const hours = Math.floor(raMinutes / 60);
    const minutes = raMinutes % 60;
    const decMinutesTotal = Math.floor(Math.abs(parsedDec) * 60);
    const degrees = Math.floor(decMinutesTotal / 60);
    const decMinutes = decMinutesTotal % 60;
    const sign = parsedDec >= 0 ? "+" : "-";
    return `TMP J${String(hours).padStart(2, "0")}${String(minutes).padStart(2, "0")}${sign}${String(degrees).padStart(2, "0")}${String(decMinutes).padStart(2, "0")}`;
  };

  const initialiseSourceSearch = () => {
    const select = document.querySelector("[data-source-select]");
    const regionFields = document.getElementById("region-fields");
    const nameInput = document.getElementById("region_name");
    const raInput = document.getElementById("region_ra_deg");
    const decInput = document.getElementById("region_dec_deg");
    if (!select) return;
    // A server validation rerender retains the submitted value.  Treat that as
    // deliberate unless it already matches the automatic coordinate name.
    const initialGenerated = temporaryTargetName(raInput?.value, decInput?.value);
    if (nameInput?.value.trim() && nameInput.value.trim() !== initialGenerated) nameInput.dataset.userEdited = "true";
    const syncTemporaryName = () => {
      if (!nameInput || nameInput.dataset.userEdited === "true") return;
      const generated = temporaryTargetName(raInput?.value, decInput?.value);
      if (generated) nameInput.value = generated;
    };
    const syncTargetMode = () => {
      const isRegion = select.value === "region";
      if (regionFields) regionFields.hidden = !isRegion;
      regionFields?.querySelectorAll("input").forEach((input) => { input.required = isRegion && input.id !== "region_name"; });
      if (isRegion) syncTemporaryName();
    };
    nameInput?.addEventListener("input", () => { nameInput.dataset.userEdited = nameInput.value.trim() ? "true" : "false"; if (!nameInput.value.trim()) syncTemporaryName(); });
    raInput?.addEventListener("input", syncTemporaryName);
    decInput?.addEventListener("input", syncTemporaryName);
    select.addEventListener("change", syncTargetMode);
    syncTargetMode();
  };

  const localDatetimeValue = (date, timeZone = displayTimezone(), includeSeconds = false) => {
    // datetime-local has no offset. For a custom numeric offset, shift the
    // instant and render in UTC; otherwise use the selected IANA display zone.
    const shifted = getTimezonePreference() !== "utc" && isCustomTelescope() && timeZone === displayTimezone();
    const effectiveDate = shifted ? new Date(date.getTime() + observerOffsetHours() * 3600_000) : date;
    const effectiveZone = shifted ? "UTC" : timeZone;
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: effectiveZone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", ...(includeSeconds ? { second: "2-digit" } : {}), hourCycle: "h23",
    }).formatToParts(effectiveDate).reduce((values, item) => ({ ...values, [item.type]: item.value }), {});
    const suffix = includeSeconds ? `:${parts.second}` : "";
    return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}${suffix}`;
  };

  const selectedInputDate = (input) => {
    if (!input?.value) return new Date();
    // Hidden/server-generated controls carry an explicit ISO offset or Z.  Do
    // not reinterpret those instants when the user switches the display zone.
    if (/[zZ]$|[+-]\d\d:\d\d$/.test(input.value)) return new Date(input.value);
    const [datePart, timePart = "00:00"] = input.value.split("T");
    const [year, month, day] = datePart.split("-").map(Number);
    const [hours, minutes, seconds = 0] = timePart.split(":").map(Number);
    if (getTimezonePreference() === "utc") return new Date(Date.UTC(year, month - 1, day, hours, minutes, seconds));
    // Local display is Beijing for LACT, or the supplied UTC offset for a
    // temporary custom telescope. This mirrors the server-side form parser.
    return new Date(Date.UTC(year, month - 1, day, hours - observerOffsetHours(), minutes, seconds));
  };

  const updateClock = (moment = new Date()) => {
    const clock = document.getElementById("sky-clock");
    if (!clock) return;
    clock.textContent = `${formatDisplayTime(moment)} ${timezoneLabel()}`;
  };

  const initialiseTelescopeControls = () => {
    const select = document.getElementById('telescope_mode');
    const fields = document.getElementById('custom-telescope-fields');
    if (!select || !fields) return;
    const sync = () => {
      const custom = select.value === 'custom';
      fields.hidden = !custom;
      fields.querySelectorAll('input').forEach((input) => { input.required = custom; });
      updateLocalTimezoneOption();
      document.dispatchEvent(new Event('skyward:telescope-change'));
    };
    select.addEventListener('change', sync);
    fields.querySelectorAll('input').forEach((input) => input.addEventListener('change', () => { if (select.value === 'custom') document.dispatchEvent(new Event('skyward:telescope-change')); }));
    sync();
  };

  const skyQueryParameters = (date) => {
    const params = new URLSearchParams({ at_time: date.toISOString(), language: getLanguage() });
    ['sun_max_altitude_deg', 'moon_min_separation_deg', 'target_min_zenith_deg', 'target_max_zenith_deg', 'minimum_window_seconds'].forEach((id) => {
      const value = document.getElementById(id)?.value;
      if (value !== undefined && value !== '') params.set(id, value);
    });
    return appendTelescopeParameters(params);
  };

  const installZoomControls = (frame, controls, explicitCentreButton = null) => {
    if (!frame) return;
    let zoom = 1;
    let choosingCentre = false;
    let centre = { x: 0.5, y: 0.5 };
    const root = controls || document;
    const findControl = (selector, fallbackId) => root.querySelector?.(selector) || (fallbackId ? document.getElementById(fallbackId) : null);
    const reset = findControl('[data-zoom-reset]', 'sky-zoom-reset');
    const initialViewportHeight = frame.getBoundingClientRect().height;
    if (initialViewportHeight > 0) frame.style.height = initialViewportHeight + 'px';
    const centreButton = findControl('[data-zoom-centre]', null) || explicitCentreButton;
    const svg = () => frame.querySelector('svg');
    const scrollToCentre = (smooth = true) => {
      const image = svg();
      if (!image || zoom <= 1) return;
      frame.scrollTo({ left: Math.max(0, centre.x * image.scrollWidth - frame.clientWidth / 2), top: Math.max(0, centre.y * image.scrollHeight - frame.clientHeight / 2), behavior: smooth ? 'smooth' : 'auto' });
    };
    const apply = (next, keepCentre = true) => {
      const image = svg();
      const configuredMaximum = Number(controls?.dataset.zoomMax || frame.dataset.zoomMax || 3);
      zoom = Math.max(1, Math.min(configuredMaximum, Number(next.toFixed(2))));
      if (!image) return;
      image.style.width = (zoom * 100) + '%';
      image.style.maxWidth = 'none';
      image.style.maxHeight = 'none';
      image.style.minWidth = (zoom * 100) + '%';
      image.style.setProperty('--map-icon-scale', String(1 / zoom));
      if (reset) reset.textContent = String(Math.round(zoom * 100)) + '%';
      window.requestAnimationFrame(() => keepCentre && scrollToCentre(false));
    };
    const finishCentreChoice = () => { choosingCentre = false; frame.classList.remove('choose-zoom-centre'); centreButton?.setAttribute('aria-pressed', 'false'); };
    findControl('[data-zoom-out]', 'sky-zoom-out')?.addEventListener('click', () => apply(zoom - .25));
    findControl('[data-zoom-in]', 'sky-zoom-in')?.addEventListener('click', () => apply(zoom + .25));
    reset?.addEventListener('click', () => { centre = { x: .5, y: .5 }; apply(1, false); frame.scrollTo({ left: 0, top: 0, behavior: 'smooth' }); finishCentreChoice(); });
    centreButton?.addEventListener('click', () => { choosingCentre = !choosingCentre; frame.classList.toggle('choose-zoom-centre', choosingCentre); centreButton.setAttribute('aria-pressed', String(choosingCentre)); });
    frame.addEventListener('click', (event) => {
      if (!choosingCentre) return;
      const image = svg();
      if (!image) return;
      const box = image.getBoundingClientRect();
      centre = { x: Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)), y: Math.max(0, Math.min(1, (event.clientY - box.top) / box.height)) };
      if (zoom === 1) apply(1.5, false);
      window.requestAnimationFrame(() => scrollToCentre());
      finishCentreChoice();
      event.preventDefault();
      event.stopPropagation();
    }, true);
    frame.addEventListener('skyward:map-replaced', () => apply(zoom, false));
    apply(1, false);
  };

  const updateTelescopeContext = (telescope = null) => {
    const mode = document.getElementById('telescope_mode')?.value || 'lact';
    const longitude = telescope?.longitude_deg ?? document.getElementById('custom_longitude_deg')?.value;
    const latitude = telescope?.latitude_deg ?? document.getElementById('custom_latitude_deg')?.value;
    const altitude = telescope?.altitude_m ?? document.getElementById('custom_altitude_m')?.value;
    const fov = telescope?.fov_diameter_deg ?? document.getElementById('custom_fov_diameter_deg')?.value;
    if (mode === 'custom' && [longitude, latitude, altitude, fov].some((value) => value === '' || value === undefined)) return;
    const name = telescope?.name || (mode === 'custom' ? translate('customTelescope') : 'LACT');
    const site = document.getElementById('context-site');
    const altitudeNode = document.getElementById('context-altitude');
    const fovNode = document.getElementById('context-fov');
    if (site) site.innerHTML = '<b>' + escapeHtml(translate('site')) + '</b> ' + Number(latitude).toFixed(6) + '° N, ' + Number(longitude).toFixed(6) + '° E';
    if (altitudeNode) altitudeNode.innerHTML = '<b>' + escapeHtml(translate('altitude')) + '</b> ' + Math.round(Number(altitude)) + ' m';
    if (fovNode) fovNode.textContent = name + ' FoV ' + Number(fov).toFixed(2) + '°';
  };

  const replaceSourceOptions = (sources) => {
    const select = document.querySelector('[data-source-select]');
    if (!select) return;
    const option = '<option value="region">' + escapeHtml(translate('addTargetOption')) + '</option>';
    select.innerHTML = option + sources.map((source) => '<option value="' + source.index + '">' + escapeHtml(source.display_name) + ' | RA ' + Number(source.ra).toFixed(3) + '° | Dec ' + Number(source.dec).toFixed(3) + '°</option>').join('');
    select.value = 'region';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  };

  const initialiseCatalogueControls = () => {
    const select = document.getElementById('catalogue-select');
    const upload = document.getElementById('catalogue-upload');
    const status = document.getElementById('catalogue-upload-status');
    const token = document.getElementById('catalog-token-input');
    if (!select || !upload) return;
    const catalogueSources = new Map();
    const refreshSky = () => document.getElementById('sky-mode')?.dispatchEvent(new Event('change'));
    const loadSources = async (catalogueToken) => {
      if (catalogueSources.has(catalogueToken)) return catalogueSources.get(catalogueToken);
      const query = new URLSearchParams({ limit: '190' });
      if (catalogueToken) query.set('catalog_token', catalogueToken);
      const response = await fetch('/api/v1/sources?' + query.toString());
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const rows = (await response.json()).sources || [];
      catalogueSources.set(catalogueToken, rows);
      return rows;
    };
    upload.addEventListener('change', async () => {
      const file = upload.files?.[0];
      if (!file) return;
      if (status) status.textContent = translate('catalogueUploading');
      const body = new FormData();
      body.append('file', file);
      try {
        const response = await fetch('/api/v1/catalogues/upload', { method: 'POST', body });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
        select.replaceChildren(new Option('2LHAASO', ''), new Option(data.label + ' (' + data.count + ')', data.token, true, true));
        catalogueSources.set(data.token, data.sources || []);
        if (token) token.value = data.token;
        replaceSourceOptions(data.sources || []);
        if (status) status.textContent = translate('catalogueUploaded');
        refreshSky();
      } catch (error) {
        if (status) status.textContent = translate('catalogueUploadFailed') + ': ' + error.message;
      }
    });
    select.addEventListener('change', async () => {
      const requestedToken = select.value;
      try {
        const rows = await loadSources(requestedToken);
        // Keep target choices and catalogue token atomic to avoid index drift.
        replaceSourceOptions(rows);
        if (token) token.value = requestedToken;
        refreshSky();
      } catch (error) {
        if (status) status.textContent = translate('catalogueUploadFailed') + ': ' + error.message;
        select.value = token?.value || '';
      }
    });
  };

  const liveTimestamp = (date) => {
    const time = formatDisplayTime(date, { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
    return translate("statusInstant", "Real-time") + ": " + time.split(" ").slice(-1)[0] + " " + timezoneLabel();
  };
  const stampLiveOption = (option, date = new Date()) => {
    if (!option) return;
    option.dataset.liveRefreshedAt = date.toISOString();
    option.textContent = liveTimestamp(date);
  };
  const refreshLiveOptionLabels = () => document.querySelectorAll('[data-live-option]').forEach((option) => {
    stampLiveOption(option, new Date(option.dataset.liveRefreshedAt || Date.now()));
  });

  const initialiseSkyControls = () => {
    const mapFrame = document.querySelector('[data-map-frame]');
    const mode = document.getElementById('sky-mode');
    const timeControl = document.getElementById('sky-time-control');
    const timeInput = document.getElementById('sky-at-time');
    const applyButton = document.getElementById('sky-time-apply');
    const sun = document.getElementById('sun-coordinates');
    const moon = document.getElementById('moon-coordinates');
    if (!mapFrame || !mode || !timeInput) return;
    let activeDate = new Date();
    installZoomControls(mapFrame, null, document.getElementById('sky-zoom-centre'));
    const renderReadout = (data, date) => {
      // The global header always represents real time; fixed maps do not own it.
      if (mode.value === 'live') {
        if (sun) sun.textContent = Number(data.sun.altitude_deg).toFixed(2) + '° / ' + Number(data.sun.azimuth_deg).toFixed(2) + '°';
        if (moon) moon.textContent = Number(data.moon.altitude_deg).toFixed(2) + '° / ' + Number(data.moon.azimuth_deg).toFixed(2) + '°';
      }
      updateTelescopeContext(data.telescope);
    };
    const refresh = async (date) => {
      activeDate = date;
      activeSkyInstant = date;
      try {
        const response = await fetch('/api/v1/sky/current?' + skyQueryParameters(date).toString(), { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const data = await response.json();
        mapFrame.innerHTML = data.svg;
        mapFrame.dispatchEvent(new Event('skyward:map-replaced'));
        renderReadout(data, date);
        if (mode.value === 'live') stampLiveOption(mode.querySelector('[data-live-option]'), date);
      } catch (error) { console.warn('Sky refresh failed', error); }
    };
    const configure = () => {
      const live = mode.value === 'live';
      timeControl.hidden = live;
      if (live) {
        const now = new Date();
        timeInput.value = localDatetimeValue(now);
        refresh(now);
      } else refresh(selectedInputDate(timeInput));
    };
    mode.addEventListener('change', configure);
    applyButton?.addEventListener('click', () => { if (mode.value === 'fixed' && timeInput.value) refresh(selectedInputDate(timeInput)); });
    document.addEventListener('skyward:language-change', () => refresh(activeDate));
    document.addEventListener('skyward:timezone-change', () => { timeInput.value = localDatetimeValue(activeDate); updateClock(activeDate); if (mode.value === 'fixed') refresh(activeDate); });
    document.addEventListener('skyward:telescope-change', () => { timeInput.value = localDatetimeValue(activeDate); updateTelescopeContext(); refresh(activeDate); });
    document.addEventListener('skyward:refresh-realtime', () => { if (mode.value === 'live') refresh(new Date()); });
    updateClock(activeDate);
    configure();
  };

  const refreshZenithOverlays = async () => {
    const context = document.getElementById('detail-query-context');
    const target = document.querySelector('[data-plan-source-name]');
    const plot = document.querySelector('.scientific-plot');
    if (!context || !target || !plot) return;
    const params = activeParameters();
    params.set('catalog_token', context.dataset.catalogToken || '');
    [...zenithOverlayIndexes].forEach((sourceIndex) => {
      const style = overlayStyle(sourceIndex);
      params.append('comparison_source_index', String(sourceIndex));
      params.append('comparison_colour', style.colour);
      params.append('comparison_line_style', style.lineStyle);
    });
    params.set('start_time', context.dataset.resultStart);
    params.set('end_time', context.dataset.resultEnd);
    if (Number(context.dataset.resultSourceIndex) >= 0) params.set('target_source_index', context.dataset.resultSourceIndex);
    else {
      params.set('target_ra_deg', context.dataset.resultSourceRa);
      params.set('target_dec_deg', context.dataset.resultSourceDec);
      params.set('target_radius_deg', context.dataset.resultSourceRadius);
      params.set('target_name', target.dataset.planSourceName);
    }
    const requestedTheme = document.documentElement.dataset.resolvedTheme || 'light';
    const requestedTimezone = getTimezonePreference();
    params.set('theme', requestedTheme);
    params.set('timezone_label', requestedTimezone === 'utc' ? 'UTC' : observerTimezoneLabel());
    const response = await fetch('/api/v1/windows/plot-overlay?' + params.toString());
    if (!response.ok) return;
    const payload = await response.json();
    if (requestedTheme !== (document.documentElement.dataset.resolvedTheme || 'light') || requestedTimezone !== getTimezonePreference()) return;
    plot.innerHTML = payload.svg;
    const preferences = document.getElementById('result-display-preferences');
    if (preferences) { preferences.dataset.plotTheme = requestedTheme; preferences.dataset.plotTimezoneLabel = requestedTimezone === 'utc' ? 'UTC' : observerTimezoneLabel(); preferences.dataset.plotOffsetHours = String(requestedTimezone === 'utc' ? 0 : observerOffsetHours()); }
    payload.comparison_sources?.forEach((source) => { overlayStyle(source.index).label = source.display_name; });
    renderZenithCurveControls();
  };

  const renderZenithCurveControls = () => {
    const panel = document.getElementById('zenith-curve-controls');
    const list = document.getElementById('zenith-curve-list');
    if (!panel || !list) return;
    panel.hidden = zenithOverlayIndexes.size === 0;
    list.replaceChildren(...[...zenithOverlayIndexes].map((sourceIndex) => {
      const style = overlayStyle(sourceIndex);
      const row = document.createElement('div'); row.className = 'zenith-curve-row';
      const name = document.createElement('button'); name.type = 'button'; name.className = 'zenith-legend-source'; name.textContent = style.label;
      const colour = document.createElement('input'); colour.type = 'color'; colour.value = style.colour; colour.setAttribute('aria-label', translate('curveColour'));
      const line = document.createElement('select'); [['solid','—'],['dotted','··'],['dashdot','-·']].forEach(([value,label]) => line.add(new Option(label, value))); line.value = style.lineStyle; line.setAttribute('aria-label', translate('curveLineStyle'));
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'secondary-button'; remove.textContent = translate('removeCurve');
      const curveGroup = () => document.getElementById('zenith-overlay-' + sourceIndex);
      const applyVisualStyle = () => {
        const path = curveGroup()?.querySelector('path'); if (!path) return;
        path.style.stroke = style.colour;
        path.style.strokeDasharray = style.lineStyle === 'solid' ? 'none' : style.lineStyle === 'dotted' ? '1.35,2.7' : '8.64,2.16,1.35,2.16';
      };
      const update = () => { style.colour = colour.value; style.lineStyle = line.value; applyVisualStyle(); };
      colour.addEventListener('input', update); colour.addEventListener('change', update); line.addEventListener('change', update);
      remove.addEventListener('click', () => { curveGroup()?.remove(); zenithOverlayIndexes.delete(sourceIndex); zenithOverlayStyles.delete(Number(sourceIndex)); renderZenithCurveControls(); });
      name.addEventListener('click', () => { row.classList.toggle('editing'); colour.focus(); });
      row.append(name, colour, line, remove); return row;
    }));
  };

  const initialiseResultMaps = () => {
    const context = document.getElementById('detail-query-context');
    const allSky = document.querySelector('[data-result-sky-map]');
    if (!context || !allSky) return;
    document.querySelectorAll('[data-map-zoom-controls]').forEach((controls) => installZoomControls(controls.closest('.sky-panel')?.querySelector('.map-frame'), controls));
    const mode = document.getElementById('result-status-mode');
    let allSkyRequestGeneration = 0;
    const refresh = async () => {
      const generation = ++allSkyRequestGeneration;
      const requestMode = mode?.value || 'instant';
      const params = activeParameters();
      params.set('language', getLanguage());
      if (requestMode === 'trajectory' && context.dataset.highlightIndexes) {
        params.set('highlight_indexes', context.dataset.highlightIndexes);
      }
      if (Number(context.dataset.resultSourceIndex) >= 0) params.set('selected_source_index', context.dataset.resultSourceIndex);
      if (requestMode === 'trajectory') {
        activeSkyInstant = new Date(context.dataset.windowDisplayTime || context.dataset.resultStart);
        params.set('at_time', context.dataset.resultStart);
        params.set('trajectory_display_time', activeSkyInstant.toISOString());
        params.set('status_mode', 'trajectory');
        params.set('trajectory_end', context.dataset.resultEnd);
        params.set('trajectory_enforce_current_pointing', 'false');
        if (context.dataset.fullWindowRanges) params.set('trajectory_ranges', context.dataset.fullWindowRanges);
      } else {
        activeSkyInstant = new Date();
        params.set('at_time', activeSkyInstant.toISOString());
      }
      const response = await fetch('/api/v1/sky/current?' + params.toString());
      const timeLabel = document.querySelector('[data-result-map-time]');
      if (timeLabel) { timeLabel.dataset.utc = activeSkyInstant.toISOString(); timeLabel.textContent = formatDisplayTime(activeSkyInstant); }
      if (response.ok && generation === allSkyRequestGeneration && mode?.value === requestMode) {
        allSky.innerHTML = (await response.json()).svg;
        if (requestMode !== 'trajectory') stampLiveOption(mode?.querySelector('[data-live-option]'), activeSkyInstant);
        allSky.dispatchEvent(new Event('skyward:map-replaced'));
      }
    };
    const localMode = document.getElementById('local-fov-mode');
    const localTimeControl = document.getElementById('local-fov-time-control');
    const localTimeInput = document.getElementById('local-fov-time');
    let localRequestGeneration = 0;
    const refreshLocal = async (explicitDate = null) => {
      const generation = ++localRequestGeneration;
      const requestMode = localMode?.value || 'live';
      const local = document.querySelector('[data-local-fov-map]'); if (!local) return;
      const date = explicitDate || (localMode?.value === 'fixed' && localTimeInput?.value ? selectedInputDate(localTimeInput) : new Date());
      const params = activeParameters(); params.set('language', getLanguage()); params.set('at_time', date.toISOString());
      if (Number(context.dataset.resultSourceIndex) >= 0) params.set('target_source_index', context.dataset.resultSourceIndex);
      else { params.set('target_ra_deg', context.dataset.resultSourceRa); params.set('target_dec_deg', context.dataset.resultSourceDec); params.set('target_radius_deg', context.dataset.resultSourceRadius); }
      const response = await fetch('/api/v1/sky/local-fov?' + params.toString());
      if (response.ok && generation === localRequestGeneration && localMode?.value === requestMode) { local.innerHTML = (await response.json()).svg; if (requestMode !== 'fixed') stampLiveOption(localMode?.querySelector('[data-live-option]'), date); local.dispatchEvent(new Event('skyward:map-replaced')); }
    };
    const configureLocalMode = () => {
      const live = localMode?.value !== 'fixed'; if (localTimeControl) localTimeControl.hidden = live;
      if (live) refreshLocal(new Date()); else { if (localTimeInput && !localTimeInput.value) localTimeInput.value = localDatetimeValue(new Date()); refreshLocal(selectedInputDate(localTimeInput)); }
    };
    let localFixedInstant = null;
    localMode?.addEventListener('change', configureLocalMode);
    document.getElementById('local-fov-time-apply')?.addEventListener('click', () => { localFixedInstant = selectedInputDate(localTimeInput); refreshLocal(localFixedInstant); });
    document.addEventListener('skyward:refresh-realtime', () => { if (localMode?.value !== 'fixed') refreshLocal(new Date()); });
    const refreshExplanation = () => {
      const note = document.getElementById('result-status-explanation');
      document.getElementById('tracked-fov-legend')?.toggleAttribute('hidden', mode?.value !== 'trajectory');
      if (!note) return;
      const key = mode?.value === 'trajectory' ? 'trajectoryStatusExplanation' : 'instantStatusExplanation';
      note.dataset.i18n = key;
      note.textContent = translate(key);
    };
    mode?.addEventListener('change', () => { refreshExplanation(); refresh(); });
    document.addEventListener('skyward:refresh-realtime', () => { if (mode?.value !== 'trajectory') refresh(); });
    document.addEventListener('skyward:language-changed', refreshExplanation);
    refreshExplanation();
    window.queueMicrotask(() => { refresh(); configureLocalMode(); });
    document.addEventListener('skyward:language-change', () => { refresh(); refreshLocal(); });
    document.addEventListener('skyward:timezone-will-change', () => { if (localMode?.value === 'fixed' && localTimeInput?.value) localFixedInstant = selectedInputDate(localTimeInput); });
    document.addEventListener('skyward:timezone-change', () => {
      if (localMode?.value === 'fixed' && localTimeInput?.value && localFixedInstant) localTimeInput.value = localDatetimeValue(localFixedInstant);
    });
  };

  refreshTimeDisplays = () => {
    document.querySelectorAll('[data-time-display="single"]').forEach((element) => {
      if (!element.dataset.utc) return;
      element.textContent = formatDisplayTime(element.dataset.utc, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
    });
    document.querySelectorAll('[data-time-display="range"]').forEach((element) => {
      if (!element.dataset.startUtc || !element.dataset.endUtc) return;
      const start = formatDisplayTime(element.dataset.startUtc, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
      const end = formatDisplayTime(element.dataset.endUtc, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
      element.textContent = `${start} ${translate("to", "to")} ${end}`;
    });
  };

  const syncSubmissionPreferences = () => {
    const themeInput = document.getElementById("display-theme-input");
    const plotThemeInput = document.getElementById("plot-theme-input");
    const timezoneInput = document.getElementById("display-timezone-input");
    if (themeInput) themeInput.value = getThemePreference();
    if (plotThemeInput) plotThemeInput.value = document.documentElement.dataset.resolvedTheme || "light";
    if (timezoneInput) timezoneInput.value = getTimezonePreference();
  };

  const initialisePlannerTimezone = () => {
    const inputs = [...document.querySelectorAll('#planner-form input[type="datetime-local"]')];
    const plannerForm = document.getElementById("planner-form");
    const canonicalInputs = [
      document.getElementById("planner-start-utc"),
      document.getElementById("planner-end-utc"),
    ];
    if (!inputs.length) return;

    // Canonical inputs contain physical UTC instants supplied by the server.
    // Their separate mutable representation prevents a display-zone switch
    // from changing the underlying observing period by eight hours.
    let currentMoments = inputs.map((input, index) => {
      const canonical = canonicalInputs[index]?.value;
      return canonical ? new Date(canonical) : selectedInputDate(input);
    });
    const syncCanonicalFromWallTimes = () => inputs.forEach((input, index) => {
      if (!input.value) return;
      const instant = selectedInputDate(input);
      currentMoments[index] = instant;
      if (canonicalInputs[index]) canonicalInputs[index].value = instant.toISOString();
    });
    const syncWallTimes = () => inputs.forEach((input, index) => {
      input.value = localDatetimeValue(currentMoments[index]);
    });
    syncWallTimes();
    plannerForm?.addEventListener("submit", () => {
      syncCanonicalFromWallTimes();
      syncSubmissionPreferences();
    });
    syncSubmissionPreferences();
    document.addEventListener("skyward:timezone-will-change", () => {
      // At this point getTimezonePreference() still returns the old display
      // zone, which is how existing datetime-local values must be interpreted.
      syncCanonicalFromWallTimes();
    });
    document.addEventListener("skyward:timezone-change", () => {
      syncWallTimes();
      syncSubmissionPreferences();
    });
    // A telescope switch may change the observer's local UTC offset. Keep the
    // canonical instants authoritative, then redraw the wall-clock controls
    // in the newly selected observatory's local time.
    document.addEventListener("skyward:telescope-change", () => {
      syncWallTimes();
      syncSubmissionPreferences();
    });
    inputs.forEach((input, index) => input.addEventListener("change", () => {
      if (!input.value) return;
      const instant = selectedInputDate(input);
      currentMoments[index] = instant;
      if (canonicalInputs[index]) canonicalInputs[index].value = instant.toISOString();
    }));
  };

  const initialiseObservationPlan = () => {
    const dialog = document.getElementById("observation-plan-dialog"), form = document.getElementById("observation-plan-form");
    const startInput = document.getElementById("plan-start"), endInput = document.getElementById("plan-end"), notesInput = document.getElementById("plan-notes");
    const sourceElement = document.getElementById("plan-source-name"), constraintsElement = document.getElementById("plan-constraints"), errorElement = document.getElementById("plan-range-error");
    const savePlot = document.getElementById("plan-save-plot"), pagePlanContext = document.querySelector("[data-plan-source-name]");
    const duplicateDialog = document.getElementById("duplicate-plan-dialog");
    if (!dialog || !form || !pagePlanContext || !startInput || !endInput) return;
    let activeWindow = null; const planEntries = [];
    let resolveDuplicateChoice = null;
    const chooseDuplicateAction = () => new Promise((resolve) => {
      if (!duplicateDialog) { resolve('cancel'); return; }
      resolveDuplicateChoice = resolve; duplicateDialog.showModal();
    });
    duplicateDialog?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-duplicate-choice]');
      if (!button) return;
      const resolve = resolveDuplicateChoice; resolveDuplicateChoice = null; duplicateDialog.close(); resolve?.(button.dataset.duplicateChoice);
    });
    duplicateDialog?.addEventListener('cancel', (event) => { event.preventDefault(); const resolve = resolveDuplicateChoice; resolveDuplicateChoice = null; duplicateDialog.close(); resolve?.('cancel'); });
    const localPlanTime = (iso) => localDatetimeValue(new Date(iso), displayTimezone(), true);
    const showError = (message = "") => { errorElement.textContent = message; errorElement.hidden = !message; };
    const withinActiveWindow = () => { if (!activeWindow) return false; const a = selectedInputDate(startInput), b = selectedInputDate(endInput); return a >= new Date(activeWindow.start) && b <= new Date(activeWindow.end) && b > a; };
    const constraintText = () => { const raw = pagePlanContext.dataset.planConstraints || ""; return getLanguage() !== "zh" ? raw : raw.replace("Sun altitude", "太阳高度").replace("Moon separation", "月亮角距").replace("Zenith", "天顶角").replace("minimum", "最短窗口"); };
    const safeName = (value) => String(value || "target").replace(/[^\p{L}\p{N}._+-]+/gu, "_").replace(/^_+|_+$/g, "") || "target";
    const buildEntry = () => ({ source: pagePlanContext.dataset.planSourceName || "", ra: pagePlanContext.dataset.planRa || "", dec: pagePlanContext.dataset.planDec || "", radius: pagePlanContext.dataset.planRadius || "", constraints: pagePlanContext.dataset.planConstraints || "", windowStart: activeWindow.start, windowEnd: activeWindow.end, planStart: selectedInputDate(startInput).toISOString(), planEnd: selectedInputDate(endInput).toISOString(), notes: notesInput?.value.trim() || "", plotSvg: savePlot?.checked ? document.querySelector('.scientific-plot svg')?.outerHTML || null : null });
    const utf8 = new TextEncoder();
    const crcTable = Array.from({ length: 256 }, (_, value) => { let crc = value; for (let bit = 0; bit < 8; bit += 1) crc = (crc & 1) ? (0xedb88320 ^ (crc >>> 1)) : (crc >>> 1); return crc >>> 0; });
    const crc32 = (bytes) => { let crc = 0xffffffff; bytes.forEach((byte) => { crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8); }); return (crc ^ 0xffffffff) >>> 0; };
    const zipBytes = (files) => {
      const chunks = [], central = []; let offset = 0;
      const u16 = (value) => [value & 255, (value >>> 8) & 255];
      const u32 = (value) => [value & 255, (value >>> 8) & 255, (value >>> 16) & 255, (value >>> 24) & 255];
      files.forEach(({ name, content }) => {
        const filename = utf8.encode(name), data = utf8.encode(content), crc = crc32(data);
        const local = new Uint8Array([0x50,0x4b,0x03,0x04,...u16(20),...u16(0x0800),...u16(0),...u16(0),...u16(0),...u32(crc),...u32(data.length),...u32(data.length),...u16(filename.length),...u16(0),...filename]);
        chunks.push(local, data);
        central.push(new Uint8Array([0x50,0x4b,0x01,0x02,...u16(20),...u16(20),...u16(0x0800),...u16(0),...u16(0),...u16(0),...u32(crc),...u32(data.length),...u32(data.length),...u16(filename.length),...u16(0),...u16(0),...u16(0),...u16(0),...u32(0),...u32(offset),...filename]));
        offset += local.length + data.length;
      });
      const centralSize = central.reduce((sum, chunk) => sum + chunk.length, 0);
      const end = new Uint8Array([0x50,0x4b,0x05,0x06,...u16(0),...u16(0),...u16(files.length),...u16(files.length),...u32(centralSize),...u32(offset),...u16(0)]);
      return new Blob([...chunks, ...central, end], { type: 'application/zip' });
    };
    const downloadPlan = () => {
      if (!planEntries.length) { window.alert(translate('noSavedPlan')); return; }
      const heading = getLanguage() === "zh" ? "Skyward 观测计划" : "Skyward observing plan";
      const text = [heading, "Generated: " + new Date().toISOString(), "", ...planEntries.flatMap((entry, index) => ["[" + (index + 1) + "] " + entry.source, "J2000 RA/Dec/radius: " + entry.ra + " deg / " + entry.dec + " deg / " + entry.radius + " deg", "Constraints: " + entry.constraints, "Full-footprint window (UTC): " + entry.windowStart + " to " + entry.windowEnd, "Planned interval (UTC): " + entry.planStart + " to " + entry.planEnd, "Notes: " + (entry.notes || "-"), ""])].join("\n");
      const files = [{ name: 'skyward-observing-plan.txt', content: text }];
      planEntries.forEach((entry, index) => { if (entry.plotSvg) files.push({ name: "skyward-" + safeName(entry.source) + "-" + (index + 1) + "-geometry-full-footprint.svg", content: entry.plotSvg }); });
      const link = document.createElement('a'); link.href = URL.createObjectURL(zipBytes(files)); link.download = 'skyward-observing-plan.zip'; link.click(); window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    };
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-plan-window]");
      if (button) { activeWindow = { start: button.dataset.windowStart, end: button.dataset.windowEnd, planStart: button.dataset.planStart || button.dataset.windowStart, planEnd: button.dataset.planEnd || button.dataset.windowEnd }; sourceElement.textContent = pagePlanContext.dataset.planSourceName || ""; constraintsElement.textContent = constraintText(); startInput.value = localPlanTime(activeWindow.planStart); endInput.value = localPlanTime(activeWindow.planEnd); if (notesInput) notesInput.value = ""; if (savePlot) savePlot.checked = false; showError(); dialog.showModal(); }
      if (event.target.closest("[data-download-observation-plan]")) downloadPlan();
      if (event.target.closest("[data-close-plan-dialog]")) dialog.close();
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault(); if (!withinActiveWindow()) { showError(translate("planRangeError")); return; }
      showError(); const entry = buildEntry(); const matches = planEntries.map((item, index) => item.source === entry.source ? index : -1).filter((index) => index >= 0);
      if (matches.length) {
        const choice = await chooseDuplicateAction();
        if (choice === 'cancel') return;
        if (choice === 'overwrite') planEntries[matches[matches.length - 1]] = entry;
        else if (choice === 'append') planEntries.push(entry);
      } else planEntries.push(entry);
      form.querySelector("#plan-confirm").textContent = translate("planAdded"); window.setTimeout(() => { form.querySelector("#plan-confirm").textContent = translate("confirmAddPlan"); }, 1300); dialog.close();
    });
    document.addEventListener("skyward:timezone-change", () => { if (activeWindow) { startInput.value = localPlanTime(activeWindow.planStart); endInput.value = localPlanTime(activeWindow.planEnd); showError(); } });
    document.addEventListener("skyward:language-change", () => { if (activeWindow) constraintsElement.textContent = constraintText(); });
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  };

  const initialiseRealtimeHeader = () => {
    const button = document.getElementById('refresh-realtime');
    const tick = () => updateClock(new Date());
    const refreshBodies = async () => {
      const moment = new Date();
      const params = appendTelescopeParameters(new URLSearchParams({ at_time: moment.toISOString() }), resultTelescopeContext());
      try {
        const response = await fetch('/api/v1/sky/bodies?' + params.toString());
        if (!response.ok) return;
        const data = await response.json();
        const sun = document.getElementById('sun-coordinates'); const moon = document.getElementById('moon-coordinates');
        if (sun) sun.textContent = Number(data.sun.altitude_deg).toFixed(2) + '° / ' + Number(data.sun.azimuth_deg).toFixed(2) + '°';
        if (moon) moon.textContent = Number(data.moon.altitude_deg).toFixed(2) + '° / ' + Number(data.moon.azimuth_deg).toFixed(2) + '°';
      } catch (error) { console.warn('Header ephemeris refresh failed', error); }
    };
    tick(); refreshBodies(); document.querySelectorAll('[data-live-option]').forEach((option) => stampLiveOption(option, new Date())); window.setInterval(tick, 1000); window.setInterval(refreshBodies, 60_000);
    button?.addEventListener('click', () => { tick(); refreshBodies(); document.dispatchEvent(new CustomEvent('skyward:refresh-realtime', { detail: { at: new Date().toISOString() } })); });
  };

  document.addEventListener("skyward:timezone-change", () => { refreshTimeDisplays(); refreshLiveOptionLabels(); });
  initialiseDisplaySettings();
  initialiseResultDisplayPreferences();
  initialiseResultThemePlot();
  initialiseSourceDialog();
  initialiseSourceSearch();
  initialisePlannerTimezone();
  initialiseTelescopeControls();
  initialiseCatalogueControls();
  initialiseSkyControls();
  initialiseRealtimeHeader();
  initialiseResultMaps();
  initialiseObservationPlan();
  refreshTimeDisplays();
})();
