/*
 * Skyward display controller
 * ---------------------------
 * The application is LAN-only and deliberately uses no framework or external
 * assets. Theme and language choices are stored in localStorage, so each
 * operator keeps their own display preference without adding server accounts.
 */
(() => {
  const STORAGE_KEYS = Object.freeze({ theme: "skyward.theme", language: "skyward.language", timezone: "skyward.timezone", coordinate: "skyward.coordinate" });
  const THEMES = ["auto", "light", "dark"];
  const TIMEZONES = Object.freeze({ local: "Asia/Shanghai", utc: "UTC" });
  const COORDINATE_FRAMES = Object.freeze({ altaz: "AltAz / Horizon", j2000: "J2000 equatorial", galactic: "Galactic" });

  const translations = {
    zh: {
      brandHome: "Skyward 首页", brandDescriptor: "天文观测辅助平台", primaryNavigation: "主导航", displaySettings: "显示设置",
      navPlanner: "天区与规划", navData: "数据说明", language: "语言", switchTheme: "切换主题", themeAuto: "自动", themeLight: "亮色", themeDark: "暗色", timezoneLocal: "北京: UTC+8", timezoneUtc: "UTC",
      site: "站点", altitude: "海拔", geometryOnly: "仅几何判断", calculationContext: "计算上下文", footerDisclaimer: "局域网原型。未评估天气、设备状态、机械安全或 LHAASO 联合观测条件。",
      currentSky: "当前天区", homeTitle: "从源表到可解释的几何窗口。", homeLead: "选择多个源表图层，设置日月与天顶角约束，并比较中心与完整源窗口。",
      skySummary: "天区摘要", catalogue: "源表", aboveHorizon: "地平线上", belowHorizon: "地平线下", inputValidation: "输入校验", calculationConditions: "计算条件", windowPlanner: "观测窗口规划", blankDisables: "不可留空",
      targetSource: "目标源", sourceSearchPlaceholder: "输入源名筛选，例如 J0534 或 Geminga", startTime: "开始时间", endTime: "结束时间", maximum31Days: "最长 30 天", optionalConstraints: "几何约束",
      sunMaxAltitude: "太阳最大高度角", sunPlaceholder: "例如 -18", sunConstraintHelp: "要求太阳高度 ≤ 此值", moonMinSeparation: "月亮最小角距", moonPlaceholder: "例如 30", moonConstraintHelp: "目标中心与月心角距",
      targetMinZenith: "目标最小天顶角", optional: "可留空", minZenithHelp: "避免过近天顶", targetMaxZenith: "目标最大天顶角", maxZenithPlaceholder: "例如 50", maxZenithHelp: "避免过近地平线",
      minimumWindow: "最短连续窗口", minimumWindowPlaceholder: "例如 1800", minimumWindowHelp: "0 表示不按持续时间筛除", calculateWindows: "计算窗口",
      horizonCoordinates: "地平坐标", allSkyTitle: "LACT 站点全天图", statusLegend: "状态图例", greenStatus: "完整源满足", yellowStatus: "中心满足，边缘不满足", redStatus: "中心不满足",
      allSkyNote: "图心是天顶和站点标记，不代表 LACT 当前实际机械光轴。点击源标记查看源详情。", centreWindow: "中心窗口", centreWindowDescription: "源中心满足地平线和已启用约束。",
      fullWindow: "完整源窗口", fullWindowDescription: "名义 extension 完整落入 8.3°硬 FoV，并满足边缘约束。", secondBoundary: "秒级边界", secondBoundaryDescription: "逐秒检查几何条件，并将边界细化至 1 秒以内。",
      backToPlanner: "← 返回规划", windowResult: "窗口结果", displayTime: "显示时间", j2000Coordinates: "J2000 坐标", nominalExtension: "名义 extension", startingStatus: "起始状态", beijingTime: "北京时间", to: "至",
      centreWindows: "中心窗口", fullWindows: "完整源窗口", enabledConstraints: "启用约束", allSky: "全天图", green: "绿色", yellow: "黄色", red: "红色", pointingCentre: "指向中心", localFovTitle: "LACT 8.3°局部 FoV", hardBoundary: "硬边界",
      localFovNote: "灰色实线圆表示局部视场图的显示边界，蓝色虚线圆表示望远镜 FoV 硬边界，青色虚线圆表示目标源的名义 extension。名义 extension 很小时，青色圆可能被中央目标标记遮住而看不到。", conditionsOverTime: "条件随时间变化", plotTitle: "几何量与完整源窗口", plotHelp: "绿色背景表示完整源窗口",
      centreConditions: "中心条件", duration: "持续", minimumZenith: "最小天顶角", minimumMoonSeparation: "最小月距", noCentreWindows: "当前条件下没有中心窗口。", fullExtension: "完整 extension", maximumSunAltitude: "最大太阳高度", noFullWindows: "源中心可能满足，但名义 extension 没有完整窗口。",
      sourceDetails: "源详情", catalogueAndEnrichment: "源表数据与待核验补充信息", openDetails: "打开详情", galacticCoordinates: "银河坐标", positionError: "95% 位置误差", astropyWarnings: "Astropy 警告",
      methodAndBoundary: "方法与边界", aboutTitle: "数据、坐标和几何模型。", aboutLead: "记录第一稿采用的固定参数、数据版本和刻意未纳入的观测条件。", lactSite: "LACT 站点", longitude: "经度", latitude: "纬度", timezone: "时区", source: "来源",
      diameter: "直径", radius: "半径", model: "模型", hardCircle: "理想圆形硬边界", notModelled: "未模拟", fovNotModelled: "离轴响应、PSF、遮挡和灵敏度衰减", catalogueTitle: "当前源表", records: "记录数", coordinates: "坐标", extensionMeaning: "度，作为名义圆形半径",
      iersOffline: "IERS 离线数据", currentCoverage: "当前覆盖", autoDownload: "自动下载", disabled: "关闭", file: "文件", statusDefinition: "源状态", gaiaSource: "Gaia 定标星", greenDefinition: "源中心及名义 extension 均满足当前几何约束。", yellowDefinition: "源中心满足，但完整源 footprint 未满足当前几何约束。", redDefinition: "源中心未满足当前几何约束。", greenStatusLabel: "绿色", yellowStatusLabel: "黄色", redStatusLabel: "红色", selectedDefinition: "蓝色空心星星轮廓表示计算时选定的目标源。", trackedDefinition: "紫色空心星星轮廓表示观测窗口计算期间跟踪视场内的源。", gaiaDefinition: "加粗十字符号表示按需查询的 Gaia 候选星；按两张图共享的状态，红/绿色分别表示不可观测/可观测，未评估其定标适用性。", extensionDefinition: "青色虚线圆表示存在已核验半径时的名义源 footprint。", notEvaluated: "未评估条件", implemented: "已实现", notImplemented: "未实现", aboutDisclaimer: "计算结果不是正式观测批准。天气、设备状态、机械限位、跟踪误差和联合观测条件均未纳入。",
      jsonApi: "JSON 接口", apiTitle: "局域网 API 参考。", apiLead: "所有接口均无账号认证，只能在受控局域网中开放。交互式 Swagger 已禁用，避免浏览器加载公网 CDN；机器可读 schema 保留在 <code>/openapi.json</code>。", endpoints: "端点", windowRequestExample: "窗口请求示例", apiDisclaimer: "响应中的", apiDisclaimerEnd: "表示未评估天气、遥测、机械安全或联合观测条件。",
      apiDescription1: "源表、IERS 与补充数据健康状态", apiDescription2: "站点、FoV 与能力边界", apiDescription3: "已安装、临时和结果页 Gaia 源表元数据", apiDescription4: "按已选源表检索普通目录源", apiDescription5: "源详情与指定时刻几何状态", apiDescription6: "全天图 SVG 与已选普通源表状态", apiDescription7: "目标中心局部图 SVG 与共享模式状态", apiDescription8: "按筛选条件查询并着色局部 Gaia 图层", apiDescription9: "中心和完整 footprint 观测窗口", apiDescription10: "单个目标窗口的观测计划备选源：粗筛后精确验证，最多返回 3 个；多窗口计划逐窗口调用", apiDescription11: "含 Zenith-Time 对比曲线的窗口 SVG", apiDescription12: "机器可读 OpenAPI schema",
      loading: "载入中", closeDetails: "关闭详情", loadingDetail: "正在计算当前地平坐标和状态。", failedDetail: "无法载入源详情", noData: "暂无数据，待核验", centrePass: "源中心通过", centreFail: "源中心未通过", footprintPass: "完整 extension 通过", footprintFail: "完整 extension 未通过",
      sexagesimal: "时分秒 / 度分秒", extension: "Extension", positionErrorLabel: "95% 位置误差", altAzZenith: "高度 / 方位 / 天顶角", moonSeparation: "月亮角距", sunAltitude: "太阳高度", statusReasons: "状态原因", enrichment: "待核验扩展信息", verification: "核验状态", associatedSources: "关联源", sourceSearchEmpty: "没有匹配的源", allFieldsRequired: "所有项目必须填写", planningConstraints: "观测规划约束", sunConstraintLimited: "必须为 -15° 或更低", addTargetOption: "添加新目标", targetName: "目标名称", temporaryNamePlaceholder: "留空自动生成 TMP JHHMM±DDMM", temporaryNameHelp: "留空将根据 RA 和 Dec 自动生成 TMP JHHMM±DDMM 名称。", regionRa: "天区 RA（J2000）", regionDec: "天区 Dec（J2000）", regionRadius: "天区半径", skyMode: "全天图模式", liveSky: "实时，每分钟刷新", fixedSky: "指定时间", skyTime: "全天图时间", applySkyTime: "应用", localDateTime: "本地日期和时间", sunHorizonCoordinates: "太阳 高度 / 方位", moonHorizonCoordinates: "月亮 高度 / 方位", useForPlanner: "填入观测规划", replaceAndCalculate: "替换并重新计算", currentFovWindowResult: "当前 LACT 视野", currentFovTitle: "当前 LACT 视野内源的观测窗口。", currentFovLead: "在接入 LACT 实时指向前，指向占位为天顶。仅计算所选开始时刻处于 8.3°视野内的源。", fovSources: "视野内源", pointingMode: "指向", fixedZenith: "固定天顶", currentFovWindows: "当前视野窗口", noFovSources: "所选时刻的固定天顶视野内没有源", planObservation: "加入观测计划", previewObservationPlan: "预览当前观测计划", observationPlan: "观测计划", plannedStart: "计划开始时间", plannedEnd: "计划结束时间", notes: "备注", planRangeHint: "默认填写当前完整源窗口中经逐秒复核有效的计划时间。计划时间必须留在该窗口内。", planRangeError: "计划时间必须位于当前完整源窗口内，且结束时间晚于开始时间。", planSecondUnavailable: "该窗口内没有可表示为完整秒的有效观测计划区间。", downloadPlan: "下载 XLSX 计划表", planAdded: "已加入计划表", constraints: "约束条件",
    },
    en: {
      brandHome: "Skyward home", brandDescriptor: "ASTRONOMICAL OBSERVATION SUPPORT PLATFORM", primaryNavigation: "Primary navigation", displaySettings: "Display settings",
      navPlanner: "Sky map & planner", navData: "Data notes", language: "Language", switchTheme: "Switch theme", themeAuto: "Auto", themeLight: "Light", themeDark: "Dark", timezoneLocal: "Beijing: UTC+8", timezoneUtc: "UTC",
      site: "Site", altitude: "Altitude", geometryOnly: "GEOMETRY ONLY", calculationContext: "Calculation context", footerDisclaimer: "LAN prototype. Weather, device state, mechanical safety and LHAASO joint observation are not evaluated.",
      currentSky: "CURRENT SKY", homeTitle: "Turn a source catalogue into observable geometry.", homeLead: "Select catalogue layers, apply solar, lunar and zenith constraints, then compare centre and full-footprint windows.",
      skySummary: "Sky summary", catalogue: "Catalogue", aboveHorizon: "Above horizon", belowHorizon: "Below horizon", inputValidation: "Input validation", calculationConditions: "CALCULATION CONDITIONS", windowPlanner: "Window planner", blankDisables: "Cannot be blank",
      targetSource: "Target source", sourceSearchPlaceholder: "Filter by source name, e.g. J0534 or Geminga", startTime: "Start time", endTime: "End time", maximum31Days: "Maximum 30 days", optionalConstraints: "Geometric constraints",
      sunMaxAltitude: "Maximum Sun altitude", sunPlaceholder: "e.g. -18", sunConstraintHelp: "Require Sun altitude ≤ value", moonMinSeparation: "Minimum Moon separation", moonPlaceholder: "e.g. 30", moonConstraintHelp: "Between target centre and Moon",
      targetMinZenith: "Minimum target zenith angle", optional: "optional", minZenithHelp: "Avoid pointing too near zenith", targetMaxZenith: "Maximum target zenith angle", maxZenithPlaceholder: "e.g. 50", maxZenithHelp: "Avoid pointing too near horizon",
      minimumWindow: "Minimum continuous window", minimumWindowPlaceholder: "e.g. 1800", minimumWindowHelp: "0 keeps all durations", calculateWindows: "Calculate windows",
      horizonCoordinates: "HORIZON COORDINATES", allSkyTitle: "LACT all-sky view", statusLegend: "Status legend", greenStatus: "Full footprint passes", yellowStatus: "Centre passes, edge fails", redStatus: "Centre fails",
      allSkyNote: "The centre is zenith and the site marker, not LACT's actual mechanical pointing. Select a star for details.", centreWindow: "Centre window", centreWindowDescription: "The source centre passes horizon and enabled constraints.",
      fullWindow: "Full-footprint window", fullWindowDescription: "The nominal extension fits entirely within the 8.3° hard FoV and edge constraints.", secondBoundary: "Second-scale boundaries", secondBoundaryDescription: "Every second is evaluated and boundaries are refined to within one second.",
      backToPlanner: "← Back to planner", windowResult: "WINDOW RESULT", displayTime: "Display time", j2000Coordinates: "J2000 coordinates", nominalExtension: "Nominal extension", startingStatus: "Starting status", beijingTime: "Beijing time", to: "to",
      centreWindows: "Centre windows", fullWindows: "Full-footprint windows", enabledConstraints: "Enabled constraints", allSky: "All-sky map", green: "Green", yellow: "Yellow", red: "Red", pointingCentre: "POINTING CENTRE", localFovTitle: "LACT 8.3° local FoV", hardBoundary: "Hard boundary",
      localFovNote: "The grey solid circle is the local-map display boundary, the blue dashed circle is the telescope hard-FoV boundary, and the cyan dashed circle is the target nominal extension. A very small nominal extension can be hidden beneath the central target marker.", conditionsOverTime: "CONDITIONS OVER TIME", plotTitle: "Geometry and full-footprint windows", plotHelp: "Green shading marks full-footprint windows",
      centreConditions: "CENTRE CONDITIONS", duration: "Duration", minimumZenith: "Minimum zenith", minimumMoonSeparation: "Minimum Moon separation", noCentreWindows: "No centre windows under the current conditions.", fullExtension: "FULL EXTENSION", maximumSunAltitude: "Maximum Sun altitude", noFullWindows: "The centre may pass, but the nominal extension has no full-footprint window.",
      sourceDetails: "SOURCE DETAILS", catalogueAndEnrichment: "Catalogue data and unverified enrichment", openDetails: "Open details", galacticCoordinates: "Galactic coordinates", positionError: "95% position error", astropyWarnings: "Astropy warnings",
      methodAndBoundary: "METHOD & BOUNDARY", aboutTitle: "Data, coordinates and geometry.", aboutLead: "Fixed parameters, catalogue provenance and the conditions intentionally excluded from this first release.", lactSite: "LACT site", longitude: "Longitude", latitude: "Latitude", timezone: "Time zone", source: "Source",
      diameter: "Diameter", radius: "Radius", model: "Model", hardCircle: "Ideal circular hard boundary", notModelled: "Not modelled", fovNotModelled: "Off-axis response, PSF, obstruction or sensitivity falloff", catalogueTitle: "Selected catalogues", records: "Records", coordinates: "Coordinates", extensionMeaning: "Degrees, used as a nominal circular radius",
      iersOffline: "Offline IERS data", currentCoverage: "Current coverage", autoDownload: "Automatic download", disabled: "Disabled", file: "File", statusDefinition: "Source status", gaiaSource: "Gaia calibration star", greenDefinition: "The source centre and nominal extension both pass the active geometric constraints.", yellowDefinition: "The centre passes, but the full source footprint does not.", redDefinition: "The source centre fails the active geometric constraints.", greenStatusLabel: "GREEN", yellowStatusLabel: "YELLOW", redStatusLabel: "RED", selectedDefinition: "A blue hollow star outline marks the source selected for calculation.", trackedDefinition: "A purple hollow star outline marks a source inside the tracked FoV during an observation-window calculation.", gaiaDefinition: "A thicker cross marks an on-demand Gaia candidate; under the shared map mode, red/green indicate unavailable/observable geometry, and calibration suitability is not assessed.", extensionDefinition: "A cyan dashed circle marks the nominal source footprint when a verified radius is available.", notEvaluated: "Not evaluated", implemented: "Implemented", notImplemented: "Not implemented", aboutDisclaimer: "This is not a formal observing approval. Weather, device state, mechanical limits, tracking error and joint-observation conditions are excluded.",
      jsonApi: "JSON API", apiTitle: "LAN API reference.", apiLead: "All endpoints are unauthenticated and must remain inside the controlled LAN. Interactive Swagger is disabled so a browser never tries to load a public CDN. The machine-readable schema remains at <code>/openapi.json</code>.", endpoints: "Endpoints", windowRequestExample: "Window request example", apiDisclaimer: "A response with", apiDisclaimerEnd: "does not evaluate weather, telemetry, mechanical safety or joint-observation conditions.",
      apiDescription1: "Catalogue, IERS and enrichment health", apiDescription2: "Site, FoV and capability boundaries", apiDescription3: "Installed, temporary, and result-local Gaia catalogue metadata", apiDescription4: "Search ordinary sources across selected catalogues", apiDescription5: "Source detail and geometry at a chosen time", apiDescription6: "All-sky SVG and selected ordinary-catalogue states", apiDescription7: "Target-centred local SVG and shared-mode states", apiDescription8: "Query and colour the filtered local Gaia layer", apiDescription9: "Centre and full-footprint observing windows", apiDescription10: "Alternatives for one target window from coarse screening and exact validation (maximum 3); multi-window plans call once per window", apiDescription11: "Window SVG with Zenith-Time comparison curves", apiDescription12: "Machine-readable OpenAPI schema",
      loading: "Loading", closeDetails: "Close details", loadingDetail: "Computing current horizon coordinates and status.", failedDetail: "Unable to load source details", noData: "No data, pending verification", centrePass: "Centre passes", centreFail: "Centre fails", footprintPass: "Full extension passes", footprintFail: "Full extension fails",
      sexagesimal: "Sexagesimal", extension: "Extension", positionErrorLabel: "95% position error", altAzZenith: "Alt / Az / Zenith", moonSeparation: "Moon separation", sunAltitude: "Sun altitude", statusReasons: "Status reasons", enrichment: "Unverified enrichment", verification: "Verification", associatedSources: "Associated sources", sourceSearchEmpty: "No matching sources", allFieldsRequired: "All fields are required", planningConstraints: "Planning constraints", sunConstraintLimited: "Must be -15° or below", addTargetOption: "Add new target", targetName: "Target name", temporaryNamePlaceholder: "Leave blank for TMP JHHMM±DDMM", temporaryNameHelp: "Leave blank to derive a TMP JHHMM±DDMM name from RA and Dec.", regionRa: "Region RA (J2000)", regionDec: "Region Dec (J2000)", regionRadius: "Region radius", skyMode: "Sky mode", liveSky: "Live, refresh each minute", fixedSky: "Specific time", skyTime: "Sky time", applySkyTime: "Apply", localDateTime: "Local date and time", sunHorizonCoordinates: "Sun Alt / Az", moonHorizonCoordinates: "Moon Alt / Az", useForPlanner: "Use for planning", replaceAndCalculate: "Replace and recalculate", currentFovWindowResult: "CURRENT LACT FoV", currentFovTitle: "Windows for sources in the current LACT FoV.", currentFovLead: "The pointing placeholder is zenith until real LACT pointing telemetry is connected. Only sources inside the 8.3° FoV at the selected start time are evaluated.", fovSources: "FoV sources", pointingMode: "Pointing", fixedZenith: "Fixed zenith", currentFovWindows: "Current FoV windows", noFovSources: "No catalogue source lies inside the current fixed zenith FoV at the selected time.", planObservation: "Add to observing plan", previewObservationPlan: "Preview current observing plan", observationPlan: "Observing plan", plannedStart: "Planned start", plannedEnd: "Planned end", notes: "Notes", planRangeHint: "The prefilled plan is checked at whole-second precision inside this full-footprint window. Planned times must stay within the valid interval.", planRangeError: "Planned times must lie inside this full-footprint window, with an end later than its start.", planSecondUnavailable: "No valid whole-second observing-plan interval exists within this window.", downloadPlan: "Download TXT plan", planAdded: "Added to plan", constraints: "Constraints",
    }
  };


  // API contracts keep machine codes; the local UI maps them to readable bilingual labels.
  Object.assign(translations.zh, {
    mapSymbolLegend: '地图符号', nonGaiaSource: '非 Gaia 源', gaiaSource: 'Gaia 定标星', trueExtension: '真实 extension', selectedTarget: '已选目标', calculationInProgress: '正在计算观测窗口', calculationFailed: '计算未能完成', returnToForm: '返回修改条件', coordinateFrame: "坐标系", coordAltAz: "地平坐标", coordJ2000: "赤道坐标（J2000）", coordGalactic: "银道坐标", includeGaia: "Gaia DR3 定标星", iersSourceKind: "当前数据源", iersUpdate: "更新策略", iersLastError: "最近联网错误",
    homeTitle: '从源表到可解释的几何窗口。', homeLead: '选择并确认加载源表后，源会显示在天图和目标源列表中。', localFovTitle: '局部视场', allSkyTitle: '站点全天图',
    allSkyNote: '颜色按地平线和已启用的几何约束判定；当前未接入可信实时指向，不使用“位于当前 FoV”约束。点击源标记查看源详情。',
    telescopeSettings: '望远镜设置', telescope: '望远镜', lactTelescope: 'LACT', customTelescope: '自定义望远镜',
    telescopeFutureHelp: '当前已接入 LACT；后续可扩展其他望远镜。', customTelescopeHelp: '本次计算临时使用 WGS-84 配置，不会保存到服务器。',
    customLongitude: '经度（WGS-84）', customLatitude: '纬度（WGS-84）', customAltitude: '海拔', customTimezone: '本地 UTC 偏移', customFov: '望远镜视场直径',
    skyZoom: '全天图缩放', zoomIn: '放大', zoomOut: '缩小', zoomReset: '重置缩放',
    reasonAllPass: '所有已启用的几何条件均满足', reasonRangeStart: '请求时间范围起点', reasonRangeEnd: '请求时间范围终点', reasonBoundary: '约束边界', reasonBecameValid: '在以下条件恢复有效后', reasonBecameInvalid: '在以下条件失效后', reasonCentre: '源中心', reasonExtension: '源边缘',
    altAz: '高度 / 方位', addZenithOverlay: '添加 Zenith - Time 曲线', removeZenithOverlay: '撤回 Zenith - Time 曲线', savePlot: '保存局部视场和观测窗口图（SVG）', chooseZoomCentre: '指定缩放中心', resultStatusMode: '全天图状态', statusInstant: '实时', statusTrajectory: '观测窗口', instantStatusExplanation: '实时：绿色表示完整源在当前时刻可观测，黄色表示仅源中心可观测，红色表示源中心不可观测。', trajectoryStatusExplanation: '观测窗口：目标源完整源窗口内的可观测性；所有源、太阳和月亮统一显示在目标源第一个完整源窗口的起始时刻（无完整源窗口时使用计算开始时刻）的位置。', trackedFovSource: '跟踪视场内源', refreshRealtime: '更新实时全天图/视场图', localFovMode: '局部视场模式', zenithCurveManagement: 'Zenith-Time 曲线管理', curveColour: '曲线颜色', curveLineStyle: '曲线线形', removeCurve: '删除曲线', confirmAddPlan: '确认添加', savePlanChanges: '保存计划修改', editPlanEntry: '编辑计划', deletePlanEntry: '删除此计划', clearCurrentPlan: '清空当前观测计划', confirmClearPlan: '确认清空当前观测计划？', downloadObservationPlan: '下载观测计划', duplicatePlanPrompt: '该源已存在计划记录。请选择覆盖之前的记录、作为新条目添加，或放弃本次添加。', duplicatePlanKicker: '重复计划', duplicatePlanTitle: '该源已有保存的观测计划', overwritePrevious: '覆盖', addAsNewEntry: '作为新条目添加', cancelAddition: '放弃添加', noSavedPlan: '尚未保存观测计划。', legendGreenMeaning: '完整源可观测', legendYellowMeaning: '仅源中心可观测', legendRedMeaning: '源中心不可观测', uploadCatalogue: '上传源表（CSV）', chooseFile: '选择文件', catalogueUploadHelp: 'UTF-8 CSV：必须包含 name、ra、dec；可选 ext。上传仅临时保存在内存中。', catalogueUploading: '正在上传源表', catalogueUploaded: '源表已加载', catalogueUploadFailed: '源表上传失败',
    target_above_horizon: '目标高于地平线', target_inside_current_fov: '目标在当前视场内', sun_altitude: '太阳高度角', moon_separation: '月亮角距', target_min_zenith: '目标最小天顶角', target_max_zenith: '目标最大天顶角', extension_inside_fov: '源扩展落入视场', extension_inside_current_fov: '源扩展落入当前视场', extension_above_horizon: '源扩展高于地平线', extension_max_zenith: '源扩展不超出地平线限制', minimum_window: '最短连续窗口',
  });
  Object.assign(translations.en, {
    mapSymbolLegend: 'Map symbols', nonGaiaSource: 'Non-Gaia source', gaiaSource: 'Gaia calibration star', trueExtension: 'True extension', selectedTarget: 'Selected target', calculationInProgress: 'Calculating observation windows', calculationFailed: 'Calculation could not be completed', returnToForm: 'Return to edit conditions', coordinateFrame: "Coordinate frame", coordAltAz: "AltAz / Horizon", coordJ2000: "Equatorial (J2000)", coordGalactic: "Galactic", includeGaia: "Gaia DR3 calibration stars", iersSourceKind: "Active source", iersUpdate: "Update policy", iersLastError: "Last online error",
    homeTitle: 'Turn a source catalogue into observable geometry.', homeLead: 'Select and confirm catalogues to load their sources into the maps and target list.', localFovTitle: 'local FoV', allSkyTitle: 'Station all-sky view',
    allSkyNote: 'Colours use the horizon and enabled geometric constraints. Authoritative live pointing is not connected, so no current-FoV constraint is applied. Select a star for details.',
    telescopeSettings: 'Telescope settings', telescope: 'Telescope', lactTelescope: 'LACT', customTelescope: 'Custom telescope',
    telescopeFutureHelp: 'LACT is active now; additional observatories can be connected later.', customTelescopeHelp: 'This temporary WGS-84 configuration is used only by this calculation and is not saved.',
    customLongitude: 'Longitude (WGS-84)', customLatitude: 'Latitude (WGS-84)', customAltitude: 'Altitude', customTimezone: 'Local UTC offset', customFov: 'Telescope FoV diameter',
    skyZoom: 'Sky map zoom', zoomIn: 'Zoom in', zoomOut: 'Zoom out', zoomReset: 'Reset zoom',
    reasonAllPass: 'All enabled geometry conditions pass', reasonRangeStart: 'Requested-range start', reasonRangeEnd: 'Requested-range end', reasonBoundary: 'Constraint boundary', reasonBecameValid: 'Became valid after', reasonBecameInvalid: 'Became invalid after', reasonCentre: 'Target centre', reasonExtension: 'Source edge',
    altAz: 'Alt / Az', addZenithOverlay: 'Add Zenith - Time curve', removeZenithOverlay: 'Remove Zenith - Time curve', savePlot: 'Save local FoV and observing-window plots (SVG)', chooseZoomCentre: 'Choose centre', resultStatusMode: 'Map status', statusInstant: 'Real-time', statusTrajectory: 'Observation window', instantStatusExplanation: 'Real-time: green means the full source is observable now, yellow means only its centre is observable, and red means its centre is unavailable.', trajectoryStatusExplanation: 'Observation window: observability inside the target full-footprint windows; all sources, Sun and Moon are shown at the target first full-footprint-window start, or the calculation start when none exists.', trackedFovSource: 'Tracked-FoV source', refreshRealtime: 'Refresh live all-sky / FoV maps', localFovMode: 'Local FoV mode', zenithCurveManagement: 'Zenith-Time curve management', curveColour: 'Curve colour', curveLineStyle: 'Curve line style', removeCurve: 'Remove curve', confirmAddPlan: 'Confirm addition', savePlanChanges: 'Save plan changes', editPlanEntry: 'Edit plan', deletePlanEntry: 'Delete this plan', clearCurrentPlan: 'Clear current observing plan', confirmClearPlan: 'Clear the current observing plan?', downloadObservationPlan: 'Download observing plan', duplicatePlanPrompt: 'A plan for this source already exists. Choose overwrite, add as a new entry, or cancel this addition.', duplicatePlanKicker: 'Duplicate plan', duplicatePlanTitle: 'This source already has a saved plan', overwritePrevious: 'Overwrite', addAsNewEntry: 'Add as new entry', cancelAddition: 'Cancel addition', noSavedPlan: 'No observing plan has been saved.', legendGreenMeaning: 'Full source observable', legendYellowMeaning: 'Centre only', legendRedMeaning: 'Centre unavailable', uploadCatalogue: 'Upload source catalogue (CSV)', chooseFile: 'Choose file', catalogueUploadHelp: 'UTF-8 CSV: name, ra, dec are required; ext is optional. Uploads are temporary and stored only in memory.', catalogueUploading: 'Uploading catalogue', catalogueUploaded: 'Catalogue loaded', catalogueUploadFailed: 'Catalogue upload failed',
    target_above_horizon: 'target above horizon', target_inside_current_fov: 'target inside current FoV', sun_altitude: 'Sun altitude', moon_separation: 'Moon separation', target_min_zenith: 'minimum target zenith angle', target_max_zenith: 'maximum target zenith angle', extension_inside_fov: 'extension inside FoV', extension_inside_current_fov: 'extension inside current FoV', extension_above_horizon: 'extension above horizon', extension_max_zenith: 'extension within horizon limit', minimum_window: 'minimum continuous window',
  });
  Object.assign(translations.zh, {
    catalogueLayers: '源表', catalogueIcons: '源表图标按钮依次切换：星星、菱形、三角形、方形、圆形和十字；Gaia 十字固定不参与选择。', layerScope: '勾选仅为草稿；确认加载后才更新天图与目标源选择器。', cataloguePicker: '选择源表', catalogueConfirm: '确认加载', catalogueCancel: '取消', catalogueDraftChanged: '选择尚未应用', catalogueCountUnit: '个源表', emptyLayers: '未选择源表', searchCatalogue: '搜索所有已选源表', loadMore: '加载更多', searchFailed: '搜索失败', unavailable: '不可用', catalogueLoadFailed: '源表清单载入失败', gaiaCandidateWarning: '仅为候选星；未评估定标适用性。', gaiaUnselected: '未选择', gaiaLoading: '查询中', gaiaSuccess: '查询成功', gaiaCached: '缓存结果', gaiaZero: '查询成功，无匹配', gaiaError: '查询失败', gaiaFallback: '初始查询超时，已使用原始视场内的有界子锥；结果可能不完整', gaiaReason: '原因', gaiaAttempts: '查询次数', gaiaCount: '返回 / 已绘制', gaiaLimits: '半径 / G 星等上限 / 行数上限', gaiaTruncated: '达到行数上限，结果可能不完整', rawFields: '原始字段、单位与来源', calculationHelp: '请等待计算完成，暂无可信的进度估计。', cancelCalculation: '关闭', calculationFailed: '计算失败，请重试', enrichment: '备注', catalogueAndEnrichment: '目录数据与备注', noData: '未提供', homeLead: '按源表选择显示图层，检索目标并计算几何窗口。'
  });
  Object.assign(translations.en, {
    catalogueLayers: 'Catalogues', catalogueIcons: 'Catalogue buttons cycle through star, diamond, triangle, square, circle and plus; Gaia crosses remain fixed and are not selectable.', layerScope: 'Checks are drafts. Confirm loading to update the sky map and target picker.', cataloguePicker: 'Select catalogues', catalogueConfirm: 'Confirm & load', catalogueCancel: 'Cancel', catalogueDraftChanged: 'Selection not applied', catalogueCountUnit: 'catalogues', emptyLayers: 'No catalogues selected', searchCatalogue: 'Search all selected catalogues', loadMore: 'Load more', searchFailed: 'Search failed', unavailable: 'Unavailable', catalogueLoadFailed: 'Catalogue list failed', gaiaCandidateWarning: 'Candidates only; calibration suitability has not been assessed.', gaiaUnselected: 'Not selected', gaiaLoading: 'Querying', gaiaSuccess: 'Success', gaiaCached: 'Cached result', gaiaZero: 'Success, no matches', gaiaError: 'Query failed', gaiaFallback: 'The initial query timed out; bounded subcones inside the original field were used and the result may be incomplete.', gaiaReason: 'Reason', gaiaAttempts: 'Queries', gaiaCount: 'Returned / drawn', gaiaLimits: 'Radius / G magnitude cutoff / row limit', gaiaTruncated: 'Row limit reached; results may be incomplete', rawFields: 'Raw fields, units and provenance', calculationHelp: 'Please wait. No reliable progress estimate is available.', cancelCalculation: 'Close', calculationFailed: 'Calculation failed; please retry', enrichment: 'Notes', catalogueAndEnrichment: 'Catalogue data and notes', noData: 'Not provided', homeLead: 'Select catalogue layers, search targets and calculate geometric windows.'
  });
  Object.assign(translations.zh, { gaiaUnorderedSubset: '按与目标的角距离由近到远选择最近 N 颗。', operatorNominalAssumption: '用户指定的名义半径假设', unknownFootprint: '未提供；按零半径点源评估，planning radius 仍未知', pointSourceFallback: '未知 footprint：按零半径点源评估；planning radius 仍未知', statusSpecified: '指定时间', statusModeLabel: '状态模式', statusTimeLabel: '状态时间', specifiedTimeKind: '指定时间类型', specifiedPoint: '时间点', specifiedRange: '时间段（最长 24 小时）', specifiedStart: '起始时间 / 时间点', specifiedEnd: '结束时间', applySpecifiedTime: '应用', specifiedTimeInvalid: '请输入有效的指定时间。', specifiedTimeOrder: '结束时间必须晚于开始时间。', specifiedTimeLimit: '指定时间段不能超过 24 小时。', specifiedStatusExplanation: '指定时间：时间点按该时刻分类；时间段按不超过 24 小时的区间分类，并统一在区间起点绘制位置。', localSharedStatus: '局部图与左侧全天图共用同一状态模式和时间。', loadGaiaLocal: '加载 Gaia DR3', gaiaRadiusFilter: '目标周围查询半径', gaiaFaintestMagnitude: '最暗 G 星等', gaiaMaximumSources: '最大源数量', applyGaiaFilters: '加载 Gaia DR3', gaiaFilterInvalid: 'Gaia 筛选条件无效：半径 0.1–5°，最暗 G 星等 5–22，最大源数 1–500。', gaiaQueryStrategy: '查询策略', localFovNote: '灰色实线圆表示以目标为中心、直径 10° 的局部图显示边界；蓝色虚线圆表示望远镜 FoV 硬边界；青色虚线圆表示目标源的名义 extension。名义 extension 很小时，青色圆可能被中央目标标记遮住。' });
  Object.assign(translations.en, { gaiaUnorderedSubset: 'The nearest N eligible sources by angular distance to the target are returned.', operatorNominalAssumption: 'Operator-supplied nominal assumption', unknownFootprint: 'Not provided; evaluated as a zero-radius point source; planning radius remains unknown', pointSourceFallback: 'Unknown footprint: evaluated as a zero-radius point source; planning radius remains unknown', statusSpecified: 'Specified time', statusModeLabel: 'Status mode', statusTimeLabel: 'Status time', specifiedTimeKind: 'Specified time type', specifiedPoint: 'Time point', specifiedRange: 'Time range (maximum 24 h)', specifiedStart: 'Start / time point', specifiedEnd: 'End', applySpecifiedTime: 'Apply', specifiedTimeInvalid: 'Enter a valid specified time.', specifiedTimeOrder: 'End time must be later than start time.', specifiedTimeLimit: 'The specified range cannot exceed 24 hours.', specifiedStatusExplanation: 'Specified time: a point is classified at that instant; a range of up to 24 hours is classified over the interval and positions are drawn at its start.', localSharedStatus: 'The local map uses the same status mode and time as the all-sky map.', loadGaiaLocal: 'Load Gaia DR3', gaiaRadiusFilter: 'Radius around target', gaiaFaintestMagnitude: 'Faintest G magnitude', gaiaMaximumSources: 'Maximum sources', applyGaiaFilters: 'Load Gaia DR3', gaiaFilterInvalid: 'Invalid Gaia filters: radius 0.1–5°, faintest G magnitude 5–22, and maximum sources 1–500.', gaiaQueryStrategy: 'Query strategy', localFovNote: 'The grey solid circle is the target-centred 10° local-map display boundary, the blue dashed circle is the telescope hard-FoV boundary, and the cyan dashed circle is the target nominal extension. A very small nominal extension may be hidden beneath the central target marker.' });
  Object.assign(translations.zh, { curveAdding: '正在计算 Zenith-Time 曲线', curveAdded: '已成功添加 Zenith-Time 曲线', curveAddFailed: 'Zenith-Time 曲线添加失败', alternativeScreening: '正在筛选观测备选源', alternativeCatalogue: '专用备选源目录', alternativeCatalogueHelp: '上传后只从该 CSV 选择备选源；未上传时使用当前已加载源表。', chooseAlternativeCatalogue: '上传备选源目录', alternativeCatalogueUploaded: '专用备选源目录已加载', alternativeCatalogueDefault: '未上传专用目录，将使用当前已加载源表', gaiaStatusCounts: '可观测 / 不可观测', includePlanWindow: '将此窗口加入观测计划', planWindow: '观测窗口', noPlanWindowsSelected: '请至少勾选一个观测窗口。', planRangeHint: '已勾选的完整源窗口会分别预填计划时间；每段计划时间都必须位于对应的有效窗口内。', planRangeError: '每段计划时间都必须位于对应的完整源窗口内，且结束时间晚于开始时间。', apiPlanWindowNote: '备选源端点每次评估一个目标窗口。包含多个已选窗口的浏览器计划会逐窗口发送一次有界请求，并把结果保存在对应窗口下。' });
  Object.assign(translations.zh, { addTrackedCurves: '添加所有跟踪视场内源曲线', sortedObservationWindows: '观测窗口（按起始时间排序）', batchPlanReady: '上传的目标列表已完成计算；有效窗口可加入观测计划。', planSort: '排序', planSortAdded: '添加时间', planSortDuration: '观测窗口总时长', planSortStart: '观测窗口起始时间', chooseCatalogueIcon: '选择源表图标', targetListUpload: '上传目标源列表（CSV）', targetListUploadHelp: '必填：name、ra、dec、ext。可选观测约束未提供时采用左侧设置值。', targetListUploaded: '目标源列表已加载', targetListUploadFailed: '目标源列表上传失败', batchCalculating: '正在逐个计算目标源窗口', batchCalculationReady: '目标源列表已加入观测计划' });
  Object.assign(translations.en, { addTrackedCurves: 'Add all tracked-FoV source curves', sortedObservationWindows: 'Observation windows (sorted by start time)', batchPlanReady: 'The uploaded target list has been calculated; valid windows are ready for the observing plan.', planSort: 'Sort', planSortAdded: 'Added time', planSortDuration: 'Total window duration', planSortStart: 'Observation-window start', chooseCatalogueIcon: 'Choose source-table icon', targetListUpload: 'Upload target list (CSV)', targetListUploadHelp: 'Required: name, ra, dec, ext. Optional planning constraints use the current settings when omitted.', targetListUploaded: 'Target list loaded', targetListUploadFailed: 'Target-list upload failed', batchCalculating: 'Calculating target windows one by one', batchCalculationReady: 'Target list added to observing plan' });
  Object.assign(translations.en, { alternativeCatalogue: 'Dedicated alternative-source catalogue', alternativeCatalogueHelp: 'After upload, alternatives are selected only from this CSV; without one, the selected ordinary catalogues are used.', chooseAlternativeCatalogue: 'Upload alternative catalogue', alternativeCatalogueUploaded: 'Dedicated alternative catalogue loaded', alternativeCatalogueDefault: 'No dedicated catalogue; selected ordinary catalogues will be used', gaiaStatusCounts: 'Observable / unavailable', includePlanWindow: 'Include this window in the observing plan', planWindow: 'Observation window', noPlanWindowsSelected: 'Select at least one observation window.', planRangeHint: 'Each selected full-footprint window is prefilled separately; every planned interval must stay inside its corresponding valid window.', planRangeError: 'Every planned interval must stay inside its corresponding full-footprint window, and its end must be later than its start.', apiPlanWindowNote: 'The alternatives endpoint evaluates one target window per request. A browser plan containing multiple selected windows sends one bounded request for each window and stores each result with that window.' });
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
    if (value === 'point_source_fallback') return translate('pointSourceFallback');
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
  const getCoordinateFrame = () => Object.hasOwn(COORDINATE_FRAMES, localStorage.getItem(STORAGE_KEYS.coordinate)) ? localStorage.getItem(STORAGE_KEYS.coordinate) : "altaz";
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

  const applyCoordinateFrame = (frame, { notify = true } = {}) => {
    const selected = Object.hasOwn(COORDINATE_FRAMES, frame) ? frame : "altaz";
    const previous = getCoordinateFrame();
    localStorage.setItem(STORAGE_KEYS.coordinate, selected);
    const selector = document.getElementById("coordinate-select");
    if (selector) selector.value = selected;
    if (notify && previous !== selected) document.dispatchEvent(new CustomEvent("skyward:coordinate-change", { detail: { previous, frame: selected } }));
  };

  const initialiseDisplaySettings = () => {
    const initialTheme = getThemePreference();
    applyTheme(initialTheme, { persist: false, notify: false });
    applyTimezone(getTimezonePreference(), { notify: false });
    applyCoordinateFrame(getCoordinateFrame(), { notify: false });
    applyLanguage(getLanguage());
    document.getElementById("language-select")?.addEventListener("change", (event) => applyLanguage(event.target.value));
    document.getElementById("timezone-select")?.addEventListener("change", (event) => applyTimezone(event.target.value));
    document.getElementById("coordinate-select")?.addEventListener("change", (event) => applyCoordinateFrame(event.target.value));
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
    if (Array.isArray(value)) return value.length ? JSON.stringify(value) : translate('noData');
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  const appendTelescopeParameters = (params, context = null) => {
    const from = (dataset, input) => context?.dataset?.[dataset] ?? document.getElementById(input)?.value;
    const mode = from('telescopeMode', 'telescope_mode') || 'lact';
    params.set('telescope_mode', mode);
    // Preserve a short-lived upload token with every request that needs the selected catalogue.
    const catalogueToken = context?.dataset?.catalogToken ?? document.getElementById('catalog-token-input')?.value;
    if (catalogueToken) params.set('catalog_token', catalogueToken);
    if (!params.has('catalog_tokens')) {
      const tokens = context?.dataset?.catalogTokens ?? document.getElementById('catalog-tokens-input')?.value;
      if (tokens !== undefined) params.set('catalog_tokens', tokens);
    }
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
      const mapping = { atTime: "at_time", sunMaxAltitudeDeg: "sun_max_altitude_deg", moonMinSeparationDeg: "moon_min_separation_deg", targetMinZenithDeg: "target_min_zenith_deg", targetMaxZenithDeg: "target_max_zenith_deg", minimumWindowSeconds: "minimum_window_seconds", nominalRadiusDeg: "nominal_radius_deg" };
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

  const statusClass = (status) => ['GREEN','YELLOW','RED','UNKNOWN'].includes(status) ? status.toLowerCase() : 'unknown';

  const updateResultStatusCard = (payload, requestMode) => {
    const card = document.getElementById('result-target-status');
    const context = document.getElementById('detail-query-context');
    if (!card || !context) return;
    const key = context.dataset.resultSourceKey;
    const row = (payload?.sources || []).find(item => String(item.source_key || '') === String(key));
    if (!row) return;
    card.className = `status-block status-${statusClass(row.status)}`;
    const value = card.querySelector('[data-status-value]');
    if (value) value.textContent = row.status || 'UNKNOWN';
    const modeLabel = requestMode === 'trajectory' ? translate('statusTrajectory') : requestMode === 'specified' ? translate('statusSpecified') : translate('statusInstant');
    const modeElement = card.querySelector('[data-status-mode]');
    if (modeElement) modeElement.textContent = `${translate('statusModeLabel')}: ${modeLabel}`;
    const timeElement = card.querySelector('[data-status-time]');
    if (timeElement) {
      const start = requestMode === 'trajectory' ? context.dataset.resultStart : activeSkyInstant?.toISOString();
      const end = requestMode === 'trajectory' ? context.dataset.resultEnd : (requestMode === 'specified' ? payload.specified_end : '');
      timeElement.textContent = start ? `${translate('statusTimeLabel')}: ${formatDisplayTime(start)}${end ? ` ${translate('to')} ${formatDisplayTime(end)}` : ''}` : '';
    }
    const reasons = card.querySelector('[data-reason-codes]');
    if (reasons) { reasons.dataset.reasonCodes = (row.reasons || []).join('|'); refreshReasonText(); }
  };

  const tevcatDetailMarkup = (data) => {
    const notes=data.notes || {}, physical=notes.physical_fields || {}, discovery=notes.discovery || {}, state=value => value?.value ?? value ?? translate('noData');
    const aliases=Array.isArray(notes.aliases) && notes.aliases.length ? notes.aliases.join(', ') : translate('noData');
    const source=safeExternalUrl(notes.source_url);
    const reportedExtent=state(physical.reported_extent);
    const reportedExtentLabel=reportedExtent === 0 ? 'No' : reportedExtent === 1 ? 'Yes' : displayValue(reportedExtent);
    return `<section class="detail-section"><h3>TeVCat</h3><dl class="detail-grid">
      <div><dt>Catalogue ID</dt><dd>${escapeHtml(displayValue(notes.catalogue_source_id))}</dd></div>
      <div><dt>Category</dt><dd>${escapeHtml(displayValue(notes.catalogue_group))}</dd></div>
      <div><dt>Aliases</dt><dd>${escapeHtml(aliases)}</dd></div>
      <div><dt>Discovery</dt><dd>${escapeHtml(displayValue(state(discovery.date)))} / ${escapeHtml(displayValue(state(discovery.observatory)))}</dd></div>
      <div><dt>Extended</dt><dd>${escapeHtml(reportedExtentLabel)}</dd></div>
      <div><dt>Flux / spectral index</dt><dd>${escapeHtml(displayValue(state(physical.reported_flux)))} / ${escapeHtml(displayValue(state(physical.spectral_index)))}</dd></div>
      <div><dt>Distance / variability</dt><dd>${escapeHtml(displayValue(state(physical.distance_or_redshift)))} / ${escapeHtml(displayValue(state(physical.variability)))}</dd></div>
      <div><dt>Source</dt><dd>${source ? `<a href="${escapeHtml(source)}" rel="noreferrer">www.tevcat.org</a>` : escapeHtml(translate('noData'))}</dd></div>
    </dl><p>${escapeHtml(notes.public_notes?.summary || (notes.public_notes?.available ? 'Public notes are available at the source site; raw HTML is not redistributed.' : 'No public note was provided for this record.'))}</p></section>`;
  };
  const oneLhaasoDetailMarkup = (data) => {
    const notes = data.notes || {};
    const components = Array.isArray(notes.components) ? notes.components : [];
    const number = (value, unit = '') => value === null || value === undefined || value === '' ? translate('noData') : String(value) + unit;
    const limitOrValue = (row, field, errorField, limitField, unit = '') => row[limitField] !== null && row[limitField] !== undefined
      ? '< ' + number(row[limitField], unit) + (field === 'r39_deg' ? ' (95% CL)' : '')
      : number(row[field], unit) + (row[errorField] !== null && row[errorField] !== undefined ? ' ± ' + number(row[errorField], unit) + (field === 'r39_deg' ? ' (1σ stat.)' : '') : '');
    const rows = components.map((row) => `<tr><td>${escapeHtml(displayValue(row.component))}</td><td>${escapeHtml(number(row.ra_deg, '°'))} / ${escapeHtml(number(row.dec_deg, '°'))}</td><td>${escapeHtml(limitOrValue(row, 'r39_deg', 'r39_error_deg', 'r39_upper_limit_deg', '°'))}</td><td>${escapeHtml(number(row.ts))}</td><td>${escapeHtml(limitOrValue(row, 'n0_value', 'n0_error', 'n0_upper_limit'))}<br><small>${escapeHtml(displayValue(row.n0_units))}; E0=${escapeHtml(number(row.reference_energy_tev, ' TeV'))}</small></td><td>${escapeHtml(number(row.photon_index))}${row.photon_index_error !== null && row.photon_index_error !== undefined ? ' ± ' + escapeHtml(number(row.photon_index_error)) : ''}</td><td>${escapeHtml(number(row.ts100))}</td><td>${escapeHtml(displayValue(row.association))}</td></tr>`).join('');
    return `<section class="detail-section"><h3>1LHAASO Table 2</h3><dl class="detail-grid">
      <div><dt>Published name</dt><dd>${escapeHtml(displayValue(notes.published_name))}</dd></div>
      <div><dt>Representative component</dt><dd>${escapeHtml(displayValue(notes.representative_component))}</dd></div>
    </dl><div class="detail-table-wrap"><table class="detail-component-table"><thead><tr><th>Component</th><th>RA / Dec</th><th>r39</th><th>TS</th><th>N0</th><th>Index</th><th>TS100</th><th>Table 2 preliminary positional counterpart</th></tr></thead><tbody>${rows}</tbody></table></div><p>${escapeHtml(notes.scientific_boundary || '')}</p></section>`;
  };
  const gaiaDetailMarkup = (data) => {
    const fields=data.notes?.query_fields || {}, distance=data.notes?.distance || {}, val=(value, unit='') => value === null || value === undefined ? escapeHtml(translate('noData')) : escapeHtml(String(value)) + unit;
    return `<section class="detail-section"><h3>Gaia DR3</h3><dl class="detail-grid">
      <div><dt>Source ID</dt><dd>${escapeHtml(String(data.source_id || data.original_id || data.name || ''))}</dd></div>
      <div><dt>G / BP / RP</dt><dd>${val(fields.phot_g_mag,' mag')} / ${val(fields.phot_bp_mag,' mag')} / ${val(fields.phot_rp_mag,' mag')}</dd></div>
      <div><dt>BP-RP</dt><dd>${val(fields.bp_rp_mag,' mag')}</dd></div>
      <div><dt>Parallax</dt><dd>${val(fields.parallax_mas,' mas')} ± ${val(fields.parallax_error_mas,' mas')}</dd></div>
      <div><dt>Inverse-parallax distance</dt><dd>${val(distance.inverse_parallax_distance_pc,' pc')}</dd></div>
      <div><dt>PM RA / Dec</dt><dd>${val(fields.pmra_mas_per_year,' mas/yr')} / ${val(fields.pmdec_mas_per_year,' mas/yr')}</dd></div>
      <div><dt>RUWE / visibility periods</dt><dd>${val(fields.ruwe)} / ${val(fields.visibility_periods_used)}</dd></div>
      <div><dt>Reference epoch</dt><dd>${escapeHtml(displayValue(data.notes?.reference_epoch))}</dd></div>
    </dl><p>Inverse-parallax distance is a simple 1/parallax estimate without a prior or uncertainty correction.</p></section>`;
  };

  const detailMarkup = (data) => {
    const status = data.status || {}, geometry = status.geometry || {}, enrichment = data.enrichment || {}, reasons = status.reasons || [];
    const catalogueSpecific = data.catalogue_id === "1lhaaso" ? oneLhaasoDetailMarkup(data) : data.catalogue_id === "tevcat" ? tevcatDetailMarkup(data) : data.source_type === "gaia" ? gaiaDetailMarkup(data) : "";
    const centreLabel = status.center_pass ? translate("centrePass") : translate("centreFail");
    const footprintLabel = status.footprint_pass ? translate("footprintPass") : translate("footprintFail");
    const measured = (value, digits = 3) => (value === null || value === undefined || value === "")
      ? escapeHtml(translate("noData")) : Number(value).toFixed(digits) + "°";
    const extension = measured(data.ext);
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
      ${catalogueSpecific}
      <section class="detail-section" hidden><h3>${escapeHtml(translate("enrichment"))}</h3><dl class="detail-grid">
        <div><dt>Spectral model</dt><dd>${escapeHtml(displayValue(enrichment.spectral_model))}</dd></div>
        <div><dt>Spatial model</dt><dd>${escapeHtml(displayValue(enrichment.spatial_model))}</dd></div>
        <div><dt>Distance</dt><dd>${escapeHtml(displayValue(enrichment.distance))}</dd></div>
        <div><dt>${escapeHtml(translate("associatedSources"))}</dt><dd>${noteValueMarkup(enrichment.associated_sources)}</dd></div>
        <div><dt>TeVCat</dt><dd>${safeExternalUrl(enrichment.tevcat_url) ? `<a href="${escapeHtml(safeExternalUrl(enrichment.tevcat_url))}" rel="noreferrer">${escapeHtml(enrichment.tevcat_name || "TeVCat")}</a>` : escapeHtml(translate("noData"))}</dd></div>
        <div><dt>${escapeHtml(translate("verification"))}</dt><dd>${escapeHtml(displayValue(enrichment.verification_status))}</dd></div>
      </dl></section>`;
  };

  const noteValueMarkup = value => { const text=displayValue(value); return text.length>240 || Array.isArray(value) || (value && typeof value==='object') ? `<details><summary>${escapeHtml(translate('rawFields'))}</summary><pre>${escapeHtml(text)}</pre></details>` : escapeHtml(text); };
  const rawDetailMarkup = (data) => `<details class="raw-fields"><summary>${escapeHtml(translate('rawFields'))}</summary><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></details>`;
  const safeExternalUrl = value => { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : ''; } catch { return ''; } };

  const zenithOverlayIndexes = new Set();
  const overlayPalette = ["#ff8c42", "#8b5cf6", "#00a6a6", "#d14f9b", "#8a9a22", "#7a6ff0"];
  const zenithOverlayStyles = new Map();
  const overlayStyle = (index) => {
    if (!zenithOverlayStyles.has(String(index))) {
      zenithOverlayStyles.set(String(index), { colour: overlayPalette[zenithOverlayStyles.size % overlayPalette.length], lineStyle: "dashdot", label: "Source " + index });
    }
    return zenithOverlayStyles.get(String(index));
  };

  const isResultTargetIdentity = identity => {
    const context = document.getElementById('detail-query-context');
    if (!context) return false;
    const value = String(identity);
    return value === context.dataset.resultSourceKey || value === context.dataset.resultSourceIndex;
  };
  let sourceDetailGeneration=0, sourceDetailController;
  const setMapActionStatus = (mapKind, message = "", state = "") => {
    if (!mapKind) return;
    const element = document.querySelector(`[data-map-action-status="${mapKind}"]`);
    if (!element) return;
    element.textContent = message; element.dataset.state = state; element.hidden = !message;
  };
  const openSource = async (sourceIndex, mapKind = null) => {
    if (!dialog) return;
    const generation=++sourceDetailGeneration; sourceDetailController?.abort(); sourceDetailController=new AbortController();
    dialogTitle.textContent = translate("loading");
    dialogUseSource.hidden = true;
    dialogUseSource.dataset.useSource = "";
    if (dialogAddZenith) dialogAddZenith.hidden = true;
    dialogBody.innerHTML = `<p class="dialog-loading">${escapeHtml(translate("loadingDetail"))}</p>`;
    dialog.showModal();
    try {
      const detailParameters = activeParameters();
      // A nominal footprint assumption belongs to one target, not the catalogue.
      if (!isResultTargetIdentity(sourceIndex)) detailParameters.delete('nominal_radius_deg');
      // No authoritative live pointing is connected; details use the same
      // geometry-only status policy as both result maps in every mode.
      detailParameters.set("enforce_current_pointing", "false");
      const response = await fetch('/api/v1/sources/' + encodeURIComponent(sourceIndex) + '?' + detailParameters.toString(), { signal:sourceDetailController.signal, headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if(generation!==sourceDetailGeneration || !dialog.open)return;
      dialogTitle.textContent = data.display_name;
      dialogUseSource.dataset.useSource = data.source_key || String(data.index);
      replaceSourceOptions([data]);
      // The selected result target is already the active plan target, but any
      // other ordinary source may replace it through the preserved result form.
      dialogBody.innerHTML = detailMarkup(data) + rawDetailMarkup(data);
      const resultTarget = document.getElementById("detail-query-context")?.dataset.resultSourceKey;
      const sourceKey=data.source_key || String(data.index);
      const isResultTarget = isResultTargetIdentity(sourceKey) || isResultTargetIdentity(data.index);
      dialogUseSource.hidden = isResultTarget || !(
        document.getElementById("source_index")
        || document.getElementById("replace-source-form")
      );
      if (dialogAddZenith) {
        const refreshZenithButton = () => {
          const added = zenithOverlayIndexes.has(sourceKey);
          dialogAddZenith.hidden = resultTarget === undefined || isResultTarget;
          dialogAddZenith.textContent = translate(added ? 'removeZenithOverlay' : 'addZenithOverlay');
          dialogAddZenith.dataset.i18n = added ? 'removeZenithOverlay' : 'addZenithOverlay';
          dialogAddZenith.dataset.overlayAdded = String(added);
        };
        refreshZenithButton();
        dialogAddZenith.onclick = async () => {
          if (zenithOverlayIndexes.has(sourceKey)) {
            zenithOverlayGeneration++;
            zenithOverlayController?.abort();
            document.getElementById(overlayStyle(sourceKey).svgId || ('zenith-overlay-' + sourceKey))?.remove();
            zenithOverlayIndexes.delete(sourceKey);
            zenithOverlayStyles.delete(String(sourceKey));
            renderZenithCurveControls();
            refreshZenithButton();
            void refreshZenithOverlays();
            return;
          }
          zenithOverlayIndexes.add(sourceKey);
          overlayStyle(sourceKey).label = data.display_name;
          refreshZenithButton();
          setMapActionStatus(mapKind, `${translate('curveAdding')}: ${data.display_name}…`, 'loading');
          const outcome = await refreshZenithOverlays();
          let settled = outcome;
          if (settled?.cancelled && zenithOverlayIndexes.has(sourceKey)) settled = await refreshZenithOverlays();
          if (settled?.ok) {
            setMapActionStatus(mapKind, `${translate('curveAdded')}: ${data.display_name}`, 'success');
          } else if (!settled?.cancelled) {
            zenithOverlayIndexes.delete(sourceKey);
            zenithOverlayStyles.delete(String(sourceKey));
            refreshZenithButton();
            setMapActionStatus(mapKind, `${translate('curveAddFailed')}: ${settled?.error || translate('noData')}`, 'error');
          }
        };
      }
    } catch (error) {
      if(error.name==='AbortError' || generation!==sourceDetailGeneration)return;
      dialogTitle.textContent = translate("failedDetail");
      dialogBody.innerHTML = `<p class="dialog-error">${escapeHtml(error.message)}</p>`;
    }
  };

  const useSourceForPlanner = (sourceIndex) => {
    const plannerSelect = document.getElementById("source_index");
    if (plannerSelect) {
      const option=[...plannerSelect.options].find(option=>option.dataset.sourceKey===String(sourceIndex) || option.value===String(sourceIndex));
      if(!option)return;plannerSelect.value = option.value;
      plannerSelect.dispatchEvent(new Event("change", { bubbles: true }));
      document.getElementById('source-picker-toggle')?.scrollIntoView({block:'center'});
      document.getElementById('source-picker-toggle')?.focus();
      return;
    }
    const replacementForm = document.getElementById("replace-source-form");
    if (replacementForm) {
      replacementForm.elements.source_index.value = String(sourceIndex);
      if(replacementForm.elements.source_key)replacementForm.elements.source_key.value=String(sourceIndex);
      if(replacementForm.elements.nominal_radius_deg) {
        replacementForm.elements.nominal_radius_deg.value = isResultTargetIdentity(sourceIndex)
          ? document.getElementById('detail-query-context')?.dataset.nominalRadiusDeg || '' : '';
      }
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
      const resultMode = document.getElementById('result-status-mode');
      if (resultMode) {
        sessionStorage.setItem('skyward.pending-result-map-state', JSON.stringify({
          mode: resultMode.value,
          specifiedKind: document.getElementById('specified-time-kind')?.value || 'point',
          specifiedStart: document.getElementById('specified-time-start')?.value || '',
          specifiedEnd: document.getElementById('specified-time-end')?.value || '',
        }));
      }
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

  const openGaiaSource = marker => {
    if(!dialog)return;
    const key=marker.dataset.gaiaSourceId || marker.dataset.sourceKey || marker.dataset.sourceId || marker.dataset.sourceIndex;
    const data=gaiaDetails.get(String(key));
    dialogTitle.textContent=data?.display_name || 'Gaia DR3 '+key;
    dialogUseSource.hidden=true;if(dialogAddZenith)dialogAddZenith.hidden=true;
    dialogBody.innerHTML=`<p>${escapeHtml(translate('gaiaCandidateWarning'))}</p>` + rawDetailMarkup(data || {source_id:key,notes:translate('noData')});
    dialog.showModal();
  };
  const initialiseSourceDialog = () => {
    const markerMapKind = marker => marker?.closest('[data-local-fov-map]') ? 'local-fov' : marker?.closest('[data-result-sky-map]') ? 'all-sky' : null;
    document.addEventListener("click", (event) => {
      const marker = event.target.closest('[data-gaia-source-id], [data-source-index]');
      const explicit = event.target.closest("[data-open-source]");
      const useSource = event.target.closest("[data-use-source]") || (event.target.closest("#dialog-use-source")?.dataset.useSource ? event.target.closest("#dialog-use-source") : null);
      const replaceSource = event.target.closest("[data-replace-source]");
      if (useSource) useSourceForPlanner(useSource.dataset.useSource);
      else if (replaceSource) useSourceForPlanner(replaceSource.dataset.replaceSource);
      else if (explicit) openSource(explicit.dataset.openSource);
      else if (marker?.matches('.source-type-gaia, [data-gaia-source-id]')) openGaiaSource(marker);
      else if (marker) openSource(marker.dataset.sourceKey || marker.dataset.sourceIndex, markerMapKind(marker));
      if (event.target.closest("[data-close-dialog]")) dialog?.close();
    });
    document.addEventListener("keydown", (event) => {
      if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('[data-source-index], [data-gaia-source-id]')) { event.preventDefault(); if(event.target.matches('.source-type-gaia, [data-gaia-source-id]'))openGaiaSource(event.target);else openSource(event.target.dataset.sourceKey || event.target.dataset.sourceIndex, markerMapKind(event.target)); }
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
    const searchInput = document.querySelector("[data-source-search]");
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
      const isRegion = select.value === 'region';
      const sourceKeyInput = document.getElementById('source-key-input');
      if(sourceKeyInput)sourceKeyInput.value=isRegion ? '' : select.selectedOptions[0]?.dataset.sourceKey || '';
      if (regionFields) regionFields.hidden = !isRegion;
      regionFields?.querySelectorAll("input").forEach((input) => { input.required = isRegion && input.id !== "region_name"; });
      if (isRegion) syncTemporaryName();
    };
    nameInput?.addEventListener("input", () => { nameInput.dataset.userEdited = nameInput.value.trim() ? "true" : "false"; if (!nameInput.value.trim()) syncTemporaryName(); });
    raInput?.addEventListener("input", syncTemporaryName);
    decInput?.addEventListener("input", syncTemporaryName);
    select.addEventListener("change", syncTargetMode);
    searchInput?.addEventListener("input", filterSourceOptions);
    syncTargetMode();
    filterSourceOptions();
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

  const catalogueCheckboxes = () => [...document.querySelectorAll('[data-catalogue-id]')];
  let appliedCatalogueTokens = null;
  const draftCatalogueTokens = () => catalogueCheckboxes().filter(input => input.checked).map(input => input.value);
  const iconChoices = ['star', 'diamond', 'triangle', 'square', 'circle', 'plus'];
  const iconLabels = { star: '★', diamond: '◆', triangle: '▲', square: '■', circle: '●', plus: '+' };
  const ICON_STORAGE_KEY = 'skyward.catalogue-icons.v1';
  let catalogueIconMap = {};
  try { catalogueIconMap = JSON.parse(localStorage.getItem(ICON_STORAGE_KEY) || '{}') || {}; } catch (_) { catalogueIconMap = {}; }
  const iconForCatalogue = (identifier) => iconChoices.includes(catalogueIconMap[identifier]) ? catalogueIconMap[identifier] : 'star';
  const saveCatalogueIcons = () => { try { localStorage.setItem(ICON_STORAGE_KEY, JSON.stringify(catalogueIconMap)); } catch (_) {} };
  const syncCatalogueIconButtons = () => document.querySelectorAll('[data-catalogue-icon-button]').forEach((button) => {
    const icon = iconForCatalogue(button.dataset.iconCatalogueId);
    button.dataset.icon = icon; button.textContent = iconLabels[icon]; button.title = translate('chooseCatalogueIcon') + ': ' + icon;
  });
  const catalogueIconQuery = () => JSON.stringify(Object.fromEntries(selectedCatalogueTokens().filter((token) => token !== 'gaia-dr3').map((token) => [token, iconForCatalogue(token)])));
  const iconMapParameters = (params) => { params.set('icon_map', catalogueIconQuery()); return params; };
  const selectedCatalogueTokens = () => [...(appliedCatalogueTokens ?? draftCatalogueTokens())];
  const appendLayerParameters = (params) => {
    // Explicit empty is meaningful. Never fall back to a default catalogue.
    params.set('catalog_tokens', selectedCatalogueTokens().join(','));
    params.set('include_gaia', 'false');
    iconMapParameters(params);
    params.set('display_frame', getCoordinateFrame());
    return params;
  };

  const skyQueryParameters = (date) => {
    const params = new URLSearchParams({ at_time: date.toISOString(), language: getLanguage(), display_frame: getCoordinateFrame() });
    appendLayerParameters(params);
    ['sun_max_altitude_deg', 'moon_min_separation_deg', 'target_min_zenith_deg', 'target_max_zenith_deg', 'minimum_window_seconds'].forEach((id) => {
      const value = document.getElementById(id)?.value;
      if (value !== undefined && value !== '') params.set(id, value);
    });
    return appendTelescopeParameters(params);
  };

  const appendCameraParameters = (params, frame) => {
    params.set('zoom',frame?.dataset.zoom || '1');
    const bounds=frame?.querySelector('svg')?.getAttribute('viewBox');
    if(bounds)params.set('bounds',bounds.trim().split(/[ ,]+/).join(','));
    return params;
  };
  const installZoomControls = (frame, controls, explicitCentreButton = null) => {
    if (!frame || frame.dataset.cameraInstalled) return;
    frame.dataset.cameraInstalled = 'true';
    const root = controls || document.querySelector('.sky-zoom-controls');
    const find = (selector, id) => root?.querySelector(selector) || document.getElementById(id);
    let zoom = Math.max(1, Math.min(1000, Number(frame.dataset.zoom) || 1));
    let cx = Number(frame.dataset.cameraCx) || .5, cy = Number(frame.dataset.cameraCy) || .5, choosing = false, drag = null, dragged = false;
    const reset = find('[data-zoom-reset]', 'sky-zoom-reset');
    const centreButton = find('[data-zoom-centre]', 'sky-zoom-centre') || explicitCentreButton;
    const input = document.createElement('input'); input.type = 'number'; input.min = '1'; input.max = '1000'; input.step = 'any'; input.value = String(Number(zoom.toFixed(4))); input.className = 'zoom-factor'; input.setAttribute('aria-label', 'Zoom factor (1x-1000x)');
    root?.insertBefore(input, reset || null);
    const dimensions = () => {
      const svg = frame.querySelector('svg');
      if (!svg) return null;
      if (!frame.dataset.baseViewBox) frame.dataset.baseViewBox = svg.getAttribute('viewBox');
      const [x,y,w,h] = frame.dataset.baseViewBox.split(/[ ,]+/).map(Number);
      return {svg,x,y,w,h};
    };
    let cameraTimer;
    const apply = (next = zoom, notify = true) => {
      zoom = Math.max(1, Math.min(1000, Number(next) || 1));
      const d = dimensions(); if (!d) return;
      const w = d.w / zoom, h = d.h / zoom;
      cx = Math.max(.5 / zoom, Math.min(1 - .5 / zoom, cx));
      cy = Math.max(.5 / zoom, Math.min(1 - .5 / zoom, cy));
      d.svg.setAttribute('viewBox', `${d.x + cx*d.w-w/2} ${d.y + cy*d.h-h/2} ${w} ${h}`);
      // Server geometry already divides glyph radii and text by its render zoom.
      // Only compensate for camera movement since that render, not zoom twice.
      const serverZoom = Number(d.svg.dataset.zoom) || 1;
      d.svg.style.setProperty('--map-icon-scale', String(serverZoom / zoom));
      d.svg.querySelectorAll('[data-gaia-layer]').forEach(layer => {
        layer.style.setProperty('--map-icon-scale', String((Number(layer.dataset.renderZoom) || serverZoom) / zoom));
      });
      input.value = String(Number(zoom.toFixed(4)));
      frame.dataset.zoom = String(zoom);
      frame.dataset.cameraCx = String(cx);
      frame.dataset.cameraCy = String(cy);
      if (reset) reset.textContent = translate('zoomReset');
      if(notify){clearTimeout(cameraTimer);cameraTimer=setTimeout(()=>frame.dispatchEvent(new Event('skyward:camera-change')),240);}
    };
    input.addEventListener('change', () => apply(input.value));
    find('[data-zoom-out]', 'sky-zoom-out')?.addEventListener('click', () => apply(zoom / 2));
    find('[data-zoom-in]', 'sky-zoom-in')?.addEventListener('click', () => apply(zoom * 2));
    reset?.addEventListener('click', () => { cx = cy = .5; choosing = false; centreButton?.setAttribute('aria-pressed','false'); frame.classList.remove('choose-zoom-centre'); apply(1); });
    centreButton?.addEventListener('click', () => { choosing = !choosing; frame.classList.toggle('choose-zoom-centre', choosing); centreButton.setAttribute('aria-pressed', String(choosing)); });
    frame.addEventListener('pointerdown', event => {
      if (event.button !== 0) return;
      dragged = false; drag = {x:event.clientX,y:event.clientY,cx,cy};
    });
    frame.addEventListener('pointermove', event => {
      if (!drag || !event.buttons || choosing) return;
      const box = frame.getBoundingClientRect();
      const dx = event.clientX-drag.x, dy = event.clientY-drag.y;
      if (Math.hypot(dx,dy) < 4) return;
      dragged = true; frame.setPointerCapture?.(event.pointerId);
      cx = drag.cx-dx/box.width/zoom; cy = drag.cy-dy/box.height/zoom; apply();
    });
    frame.addEventListener('pointerup', () => { drag = null; });
    frame.addEventListener('pointercancel', () => { drag = null; });
    frame.addEventListener('click', event => {
      if (dragged) { event.preventDefault(); event.stopPropagation(); dragged = false; return; }
      if (!choosing) return;
      const d = dimensions(); if (!d) return;
      const point = d.svg.createSVGPoint(); point.x=event.clientX; point.y=event.clientY;
      const transformed = point.matrixTransform(d.svg.getScreenCTM().inverse());
      cx=(transformed.x-d.x)/d.w; cy=(transformed.y-d.y)/d.h;
      choosing=false; frame.classList.remove('choose-zoom-centre'); centreButton?.setAttribute('aria-pressed','false'); apply(zoom === 1 ? 2 : zoom);
      event.preventDefault(); event.stopPropagation();
    }, true);
    frame.addEventListener('skyward:map-replaced', () => apply(zoom,false));
    document.addEventListener('skyward:language-change', () => apply(zoom,false));
    apply(zoom,false);
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

  // The hidden native select is only a form transport; the popup owns search.
  const sourceRows = new Map();
  let renderSourcePicker = () => {};
  const replaceSourceOptions = (sources) => {
    const select = document.querySelector('[data-source-select]'); if (!select) return;
    const previous = select.value;
    sources.forEach(source => {
      const sourceKey = String(source.source_key || source.source_id || source.index); sourceRows.set(sourceKey, source);
      let option = [...select.options].find(item => item.dataset.sourceKey === sourceKey);
      if (!option) { option = new Option('', sourceKey); select.add(option); }
      option.textContent = `${source.display_name || source.name} | RA ${Number(source.ra).toFixed(3)}° | Dec ${Number(source.dec).toFixed(3)}°`;
      option.dataset.sourceId = source.source_key || source.source_id || sourceKey;
      option.dataset.sourceKey = source.source_key || sourceKey;
    });
    select.value = previous;
  };
  const filterSourceOptions = () => renderSourcePicker();

  const initialiseCatalogueControls = () => {
    const panel = document.querySelector('[data-catalogue-panel]'); if (!panel) return;
    const status = document.getElementById('catalogue-status');
    const picker = document.getElementById('catalogue-picker-popup');
    const pickerToggle = document.getElementById('catalogue-picker-toggle');
    const pickerSummary = document.getElementById('catalogue-picker-summary');
    const confirm = document.getElementById('catalogue-confirm');
    const select = document.querySelector('[data-source-select]');
    const input = document.getElementById('source-search');
    const popup = document.getElementById('source-picker-popup');
    const toggle = document.getElementById('source-picker-toggle');
    const list = document.getElementById('source-options');
    const more = document.getElementById('source-load-more');
    const searchStatus = document.getElementById('source-search-status');
    appliedCatalogueTokens = draftCatalogueTokens();
    let rows = [], nextOffset = null, generation = 0, controller, active = -1, debounce;
    const sameTokens = (left, right) => left.length === right.length && left.every((value, index) => value === right[index]);
    const restoreDraft = () => {
      const applied = new Set(selectedCatalogueTokens());
      catalogueCheckboxes().forEach(checkbox => { checkbox.checked = applied.has(checkbox.value); });
      if (status) status.textContent = applied.size ? '' : translate('emptyLayers');
    };
    const syncCatalogueSummary = () => {
      if (!pickerSummary) return;
      const selected = selectedCatalogueTokens();
      if (!selected.length) { pickerSummary.textContent = translate('emptyLayers'); return; }
      if (selected.length === 1) {
        const checkbox = catalogueCheckboxes().find(item => item.value === selected[0]);
        pickerSummary.textContent = checkbox?.parentElement.querySelector('span')?.textContent || selected[0];
        return;
      }
      pickerSummary.textContent = `${selected.length} ${translate('catalogueCountUnit')}`;
    };
    const setCatalogueOpen = open => {
      if (!picker) return;
      if (open) restoreDraft();
      picker.hidden = !open;
      pickerToggle?.setAttribute('aria-expanded', String(open));
      panel.closest('.sky-panel')?.classList.toggle('catalogue-open', open);
      if (open) picker.querySelector('[data-catalogue-id]')?.focus();
      else pickerToggle?.focus();
    };
    const cancelDraft = () => { restoreDraft(); setCatalogueOpen(false); };
    const setOpen = open => { if (!popup) return; popup.hidden = !open; toggle.setAttribute('aria-expanded',String(open)); input.setAttribute('aria-expanded',String(open)); if (open) input.focus(); else input.removeAttribute('aria-activedescendant'); };
    const syncLabel = () => { const label = document.getElementById('source-picker-value'); if (label && select) label.textContent = select.selectedOptions[0]?.textContent || translate('targetSource'); };
    const choose = sourceKey => {
      const option = sourceKey === 'region' ? [...select.options].find(item => item.value === 'region') : [...select.options].find(item => item.dataset.sourceKey === sourceKey);
      if (!option) return;
      select.value=option.value; select.dispatchEvent(new Event('change',{bubbles:true})); syncLabel(); setOpen(false); toggle.focus();
    };
    renderSourcePicker = () => {
      if (!list) return;
      const selectedKey = select.selectedOptions[0]?.dataset.sourceKey || select.value;
      const items = [{index:'region',source_key:'region',display_name:translate('addTargetOption')}, ...rows];
      list.replaceChildren(...items.map((source,index) => {
        const sourceKey=String(source.source_key || source.source_id || source.index);
        const option = document.createElement('div'); option.id='source-option-'+index; option.role='option'; option.tabIndex=-1; option.dataset.value=sourceKey;
        option.setAttribute('aria-selected',String(selectedKey===sourceKey));
        option.textContent = source.display_name || source.name; option.addEventListener('click',()=>choose(sourceKey)); return option;
      }));
      active=-1; input.removeAttribute('aria-activedescendant'); syncLabel();
    };
    const load = async (append = false) => {
      if (!select) return;
      controller?.abort(); controller = new AbortController(); const current=++generation;
      const offset=append ? nextOffset : 0;
      const ids=selectedCatalogueTokens();
      if (!ids.length) { rows=[]; nextOffset=null; more.hidden=true; searchStatus.textContent=translate('emptyLayers'); renderSourcePicker(); return; }
      const query=new URLSearchParams({catalog_tokens:ids.join(','),q:input.value.trim(),limit:'100',offset:String(offset || 0)});
      searchStatus.textContent=translate('loading');
      try {
        const response=await fetch('/api/v1/sources?'+query,{signal:controller.signal});
        const data=await response.json(); if (!response.ok) throw new Error(typeof data.detail==='string' ? data.detail : 'HTTP '+response.status);
        if (current!==generation) return;
        rows=append ? [...rows,...data.sources] : data.sources || []; replaceSourceOptions(rows);
        nextOffset=data.next_offset ?? (data.has_more ? (offset || 0)+(data.sources || []).length : null);
        more.hidden=nextOffset===null; searchStatus.textContent=`${rows.length} / ${data.total ?? data.total_count ?? rows.length}`; renderSourcePicker();
      } catch(error) { if (current===generation && error.name!=='AbortError') searchStatus.textContent=translate('searchFailed')+': '+error.message; }
    };
    toggle?.addEventListener('click',()=>{ setOpen(popup.hidden); if (!popup.hidden) load(); });
    input?.addEventListener('input',()=>{ clearTimeout(debounce); controller?.abort(); generation++; rows=[]; more.hidden=true; renderSourcePicker(); searchStatus.textContent=translate('loading'); debounce=setTimeout(()=>load(),180); });
    input?.addEventListener('keydown',event=>{
      const options=[...list.children];
      if (event.key==='Escape') { setOpen(false); toggle.focus(); }
      if (event.key==='ArrowDown' || event.key==='ArrowUp') {
        event.preventDefault(); active=Math.max(0,Math.min(options.length-1,active+(event.key==='ArrowDown'?1:-1)));
        options.forEach((option,index)=>option.classList.toggle('active',index===active));
        if (options[active]) { input.setAttribute('aria-activedescendant',options[active].id); options[active].scrollIntoView({block:'nearest'}); }
      }
      if (event.key==='Enter') { event.preventDefault(); if (options[active]) choose(options[active].dataset.value); }
    });
    popup?.addEventListener('keydown',event=>{ if(event.key==='Escape'){setOpen(false);toggle.focus();} });
    document.addEventListener('click',event=>{if(popup && !event.target.closest('.source-combobox'))setOpen(false);});
    select?.addEventListener('change',syncLabel); more?.addEventListener('click',()=>load(true));
    const applySelection = () => {
      appliedCatalogueTokens = draftCatalogueTokens();
      const appliedValue=selectedCatalogueTokens().join(',');
      document.querySelectorAll('[name="catalog_tokens"]').forEach(hidden => { hidden.value=appliedValue; });
      const resultContext=document.getElementById('detail-query-context'); if(resultContext)resultContext.dataset.catalogTokens=appliedValue;
      if (status) status.textContent=selectedCatalogueTokens().length ? '' : translate('emptyLayers');
      syncCatalogueSummary(); setCatalogueOpen(false);
      // Calculated context and result target stay stable; only display layers and the homepage picker refresh.
      document.dispatchEvent(new Event('skyward:catalogues-change')); load();
    };
    pickerToggle?.addEventListener('click', () => setCatalogueOpen(picker.hidden));
    confirm?.addEventListener('click', applySelection);
    panel.addEventListener('click', (event) => {
      const button = event.target.closest('[data-catalogue-icon-button]');
      if (!button) return;
      event.preventDefault(); event.stopPropagation();
      const current = iconForCatalogue(button.dataset.iconCatalogueId);
      const next = iconChoices[(iconChoices.indexOf(current) + 1) % iconChoices.length];
      catalogueIconMap[button.dataset.iconCatalogueId] = next;
      saveCatalogueIcons(); syncCatalogueIconButtons();
      document.dispatchEvent(new Event('skyward:catalogue-icons-change'));
    });
    panel.addEventListener('change',event=>{
      if (!event.target.matches('[data-catalogue-id]')) return;
      const draft = draftCatalogueTokens();
      if (status) status.textContent = sameTokens(draft, selectedCatalogueTokens()) ? (draft.length ? '' : translate('emptyLayers')) : translate('catalogueDraftChanged');
    });
    panel.querySelectorAll('[data-catalogue-cancel]').forEach(button => button.addEventListener('click', cancelDraft));
    picker?.addEventListener('keydown', event => { if (event.key === 'Escape') { event.preventDefault(); cancelDraft(); } });
    document.addEventListener('click', event => { if (!picker?.hidden && !event.target.closest('[data-catalogue-panel]')) cancelDraft(); });
    fetch('/api/v1/catalogues').then(response=>response.json()).then(data=>{
      window.skywardCatalogues=data.catalogues || [];
      (window.skywardCatalogues).forEach(item=>{
        const checkbox=catalogueCheckboxes().find(input=>input.value===item.identifier);
        if(checkbox)checkbox.parentElement.querySelector('span').textContent=item.display?.[getLanguage()] || item.label;
        if(checkbox && item.available===false){checkbox.disabled=true;checkbox.title=item.error || translate('unavailable');}
      });
      syncCatalogueSummary();
    }).catch(error=>{if(status)status.textContent=translate('catalogueLoadFailed')+': '+error.message;});
    document.getElementById('target-list-upload-trigger')?.addEventListener('click', () => document.getElementById('target-list-upload')?.click());
    document.getElementById('target-list-upload')?.addEventListener('change', async (event) => {
      const file = event.target.files?.[0]; if (!file) return;
      const status = document.getElementById('target-list-upload-status');
      const name = document.getElementById('target-list-upload-name');
      if (name) name.textContent = file.name;
      if (status) status.textContent = translate('catalogueUploading');
      try {
        const body = new FormData(); body.append('file', file);
        const response = await fetch('/api/v1/target-lists/upload', { method: 'POST', body });
        const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'HTTP ' + response.status);
        const token = document.getElementById('target-list-token'); if (token) token.value = data.token || '';
        if (status) status.textContent = translate('targetListUploaded') + ': ' + (data.count || data.sources?.length || 0);
      } catch (error) { if (status) status.textContent = translate('targetListUploadFailed') + ': ' + error.message; }
    });
    document.getElementById('catalogue-upload')?.addEventListener('change',async event=>{
      const file=event.target.files?.[0]; if(!file)return;
      const uploadName=document.getElementById('catalogue-upload-name'); if(uploadName)uploadName.textContent=file.name;
      const uploadStatus=document.getElementById('catalogue-upload-status'); uploadStatus.textContent=translate('catalogueUploading');
      try {
        const body=new FormData();body.append('file',file);const response=await fetch('/api/v1/catalogues/upload',{method:'POST',body});const data=await response.json();if(!response.ok)throw new Error(data.detail || 'HTTP '+response.status);
        const label=document.createElement('label'); label.className='catalogue-choice'; const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.value=data.token;checkbox.dataset.catalogueId=data.token;checkbox.checked=true;
        const text=document.createElement('span');text.textContent=data.label;
        const iconButton=document.createElement('button'); iconButton.type='button'; iconButton.className='catalogue-icon-button'; iconButton.dataset.catalogueIconButton=''; iconButton.dataset.iconCatalogueId=data.token; iconButton.dataset.icon='star'; iconButton.textContent=iconLabels.star; iconButton.title=translate('chooseCatalogueIcon');
        label.append(checkbox,text,iconButton);document.getElementById('catalogue-checkboxes').append(label);
        uploadStatus.textContent=translate('catalogueUploaded'); setCatalogueOpen(true); checkbox.checked=true; if(status)status.textContent=translate('catalogueDraftChanged');
      } catch(error){uploadStatus.textContent=translate('catalogueUploadFailed')+': '+error.message;}
    });
    document.addEventListener('skyward:language-change',()=>{
      document.querySelectorAll('[data-catalogue-id]').forEach(checkbox=>{
        const item=(window.skywardCatalogues || []).find(row=>row.identifier===checkbox.value);
        if(item)checkbox.parentElement.querySelector('span').textContent=item.display?.[getLanguage()] || item.label;
      });
      renderSourcePicker();syncCatalogueSummary();
    });
    syncCatalogueSummary(); syncLabel(); syncCatalogueIconButtons(); renderSourcePicker(); load();
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

  const gaiaRequests = new Map();
  const gaiaDetails = new Map();
  const gaiaSelected = () => document.getElementById('local-gaia-filter-apply')?.dataset.gaiaEnabled === 'true';
  const gaiaFilterParameters = () => {
    const radius = Number(document.getElementById('local-gaia-radius')?.value ?? 1);
    const maxMag = Number(document.getElementById('local-gaia-max-mag')?.value ?? 10);
    const limit = Number(document.getElementById('local-gaia-limit')?.value ?? 10);
    if (!Number.isFinite(radius) || radius < 0.1 || radius > 5 || !Number.isFinite(maxMag) || maxMag < 5 || maxMag > 22 || !Number.isInteger(limit) || limit < 1 || limit > 500) return null;
    return {radius_deg:String(radius), max_mag:String(maxMag), limit:String(limit)};
  };
  const showGaiaFilterError = (message = '') => {
    const error = document.getElementById('local-gaia-filter-error');
    if (!error) return;
    error.textContent = message; error.hidden = !message;
  };
  const renderGaiaStatus = () => {
    const panel=document.querySelector('[data-gaia-status]');
    const statusPanel=document.getElementById('local-fov-gaia-status-panel');
    const legend=document.getElementById('local-fov-gaia-legend');
    const enabled=gaiaSelected();
    if(statusPanel)statusPanel.hidden=!enabled;
    if(legend)legend.hidden=!enabled;
    if(!panel)return;
    if(!enabled){panel.textContent='';return;}
    panel.replaceChildren(...[...gaiaRequests.values()].map(state=>{
      const row=document.createElement('div');
      const meta=state.meta || {};
      const key=state.state==='loading'?'gaiaLoading':state.state==='error'?'gaiaError':meta.count===0?'gaiaZero':(meta.cached || meta.cache_hit)?'gaiaCached':'gaiaSuccess';
      row.textContent=`${state.kind==='local-fov'?translate('localFovTitle'):translate('allSky')}: ${translate(key)}`;
      if(state.state!=='loading') {
        const info=document.createElement('p');info.textContent=`${translate('gaiaCount')}: ${meta.count ?? '-'} / ${meta.drawn_count ?? '-'}; ${translate('gaiaLimits')}: ${meta.radius_deg ?? 1}° / ${meta.max_mag ?? meta.magnitude_limit ?? 10} mag / ${meta.limit ?? meta.row_limit ?? 10}; ${translate('gaiaAttempts')}: ${meta.attempts ?? 1}`;row.append(info);
        if(meta.status_counts){const note=document.createElement('p');note.textContent=`${translate('gaiaStatusCounts')}: ${meta.status_counts.GREEN ?? 0} / ${meta.status_counts.RED ?? 0}`;row.append(note);}
        if(meta.query_strategy){const note=document.createElement('p');note.textContent=`${translate('gaiaQueryStrategy')}: ${meta.query_strategy}`;row.append(note);}
        if(meta.truncated || meta.limit_reached){const note=document.createElement('p');note.textContent=translate('gaiaTruncated');row.append(note);}
        if(meta.fallback_used){const note=document.createElement('p');note.textContent=translate('gaiaFallback');row.append(note);}
        if(meta.fallback_reason){const note=document.createElement('p');note.textContent=`${translate('gaiaReason')}: ${meta.fallback_reason}`;row.append(note);}
        if(Array.isArray(meta.fallback_errors) && meta.fallback_errors.length){const note=document.createElement('p');note.textContent=`${translate('gaiaReason')}: ${meta.fallback_errors.join('; ')}`;row.append(note);}
        if(meta.selection==='bounded_unordered_subset' || meta.ordering==='unspecified'){const note=document.createElement('p');note.dataset.gaiaSelectionWarning='true';note.textContent=translate('gaiaUnorderedSubset');row.append(note);} else if(meta.selection==='nearest_by_angular_distance'){const note=document.createElement('p');note.dataset.gaiaSelectionInfo='true';note.textContent=translate('gaiaUnorderedSubset');row.append(note);}
      }
      if(state.error){const error=document.createElement('p');error.textContent=state.error;row.append(error);}
      return row;
    }));
  };
  const invalidateGaia = frame => {
    const previous=gaiaRequests.get(frame);previous?.controller?.abort();
    frame.querySelector('[data-gaia-layer]')?.remove();
    if(!gaiaSelected())gaiaDetails.clear();
    gaiaRequests.set(frame,{generation:(previous?.generation || 0)+1,state:gaiaSelected()?'loading':'unselected',kind:'local-fov'});
    renderGaiaStatus();
  };
  const refreshGaiaLayer = async (frame, mapParams, kind) => {
    if(!gaiaSelected() || kind!=='local-fov' || !frame.hasAttribute('data-local-fov-map'))return;
    const state=gaiaRequests.get(frame) || {generation:0}; const generation=state.generation;
    const filters=gaiaFilterParameters();
    if(!filters){Object.assign(state,{state:'error',kind,error:translate('gaiaFilterInvalid'),meta:{count:0,drawn_count:0,radius_deg:null,max_mag:null,limit:null}});gaiaRequests.set(frame,state);showGaiaFilterError(translate('gaiaFilterInvalid'));renderGaiaStatus();return;}
    showGaiaFilterError();
    const controller=new AbortController();Object.assign(state,{controller,state:'loading',kind,error:null});gaiaRequests.set(frame,state);renderGaiaStatus();
    const params=new URLSearchParams(mapParams); params.set('map_kind',kind);params.set('limit',filters.limit);params.set('max_mag',filters.max_mag);
    params.set('radius_deg',filters.radius_deg);
    try {
      const response=await fetch('/api/v1/gaia?'+params,{signal:controller.signal});const data=await response.json();
      if(controller.signal.aborted || gaiaRequests.get(frame)?.generation!==generation || !gaiaSelected())return;
      const meta=data.gaia || data; if(!response.ok || meta.error || meta.status === 'error')throw new Error(meta.error || data.detail || 'HTTP '+response.status); Object.assign(state,{meta:{...meta}});
      const svg=frame.querySelector('svg'); if(!svg)return;
      const parsed=new DOMParser().parseFromString(data.overlay_svg || data.svg || '<svg/>','image/svg+xml');
      const layer=document.createElementNS('http://www.w3.org/2000/svg','g');layer.dataset.gaiaLayer='true';
      layer.dataset.renderZoom=params.get('zoom') || '1';
      layer.style.setProperty('--map-icon-scale', String(Number(layer.dataset.renderZoom) / (Number(frame.dataset.zoom) || 1)));
      parsed.querySelectorAll('.source-type-gaia, [data-gaia-source-id]').forEach(marker=>{ if(!marker.parentElement?.closest('.source-type-gaia, [data-gaia-source-id]'))layer.append(document.importNode(marker,true)); });
      svg.append(layer);
      (data.sources || []).forEach(source=>{gaiaDetails.set(String(source.source_key || source.source_id || source.index),source);gaiaDetails.set(String(source.source_id || source.index),source);});
      Object.assign(state,{state:'success',meta:{...meta,drawn_count:meta.drawn_count ?? layer.children.length}});renderGaiaStatus();
    }catch(error){if(error.name==='AbortError' || gaiaRequests.get(frame)?.generation!==generation)return;Object.assign(state,{state:'error',error:error.message});renderGaiaStatus();}
  };
  document.addEventListener('skyward:language-change',renderGaiaStatus);

  const initialiseSkyControls = () => {
    const mapFrame = document.querySelector('[data-map-frame]');
    const mode = document.getElementById('sky-mode');
    const timeControl = document.getElementById('sky-time-control');
    const timeInput = document.getElementById('sky-at-time');
    const applyButton = document.getElementById('sky-time-apply');
    const sun = document.getElementById('sun-coordinates');
    const moon = document.getElementById('moon-coordinates');
    if (!mapFrame || !mode || !timeInput) return;
    let activeDate = new Date(), requestGeneration = 0, requestController;
    installZoomControls(mapFrame, null, document.getElementById('sky-zoom-centre'));
    const updateHomepageSummary = (data) => {
      const catalogueCount = data?.catalogue?.count ?? (Array.isArray(data?.sources) ? data.sources.length : null);
      const visibleCount = data?.visible_source_count;
      const belowCount = data?.below_horizon_source_count;
      const values = [["home-catalog-count", catalogueCount], ["home-visible-count", visibleCount], ["home-below-count", belowCount]];
      values.forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element && Number.isFinite(Number(value))) element.textContent = String(value);
      });
    };
    const renderReadout = (data, date) => {
      updateHomepageSummary(data);
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
      const generation=++requestGeneration; requestController?.abort(); requestController=new AbortController();
      const params=appendCameraParameters(skyQueryParameters(date),mapFrame);
      iconMapParameters(params);
      try {
        const response = await fetch('/api/v1/sky/current?' + params.toString(), { signal:requestController.signal, headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const data = await response.json();
        if(generation!==requestGeneration)return;
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
    mapFrame.addEventListener('skyward:camera-change',()=>refresh(activeDate));
    mode.addEventListener('change', configure);
    applyButton?.addEventListener('click', () => { if (mode.value === 'fixed' && timeInput.value) refresh(selectedInputDate(timeInput)); });
    document.addEventListener('skyward:catalogues-change', () => refresh(activeDate));
    document.addEventListener('skyward:catalogue-icons-change', () => refresh(activeDate));
    document.addEventListener('skyward:language-change', () => refresh(activeDate));
    document.addEventListener('skyward:coordinate-change', () => refresh(activeDate));
    document.addEventListener('skyward:timezone-change', () => { timeInput.value = localDatetimeValue(activeDate); updateClock(activeDate); if (mode.value === 'fixed') refresh(activeDate); });
    document.addEventListener('skyward:telescope-change', () => { timeInput.value = localDatetimeValue(activeDate); updateTelescopeContext(); refresh(activeDate); });
    document.addEventListener('skyward:refresh-realtime', () => { if (mode.value === 'live') refresh(new Date()); });
    updateClock(activeDate);
    configure();
  };

  let zenithOverlayGeneration = 0, zenithOverlayController, zenithRefreshTail = Promise.resolve();
  const runZenithOverlayRefresh = async () => {
    const context = document.getElementById('detail-query-context');
    const target = document.querySelector('[data-plan-source-name]');
    const plot = document.querySelector('.scientific-plot');
    if (!context || !target || !plot) return { ok: false, cancelled: false, error: 'plot context unavailable' };
    const generation = ++zenithOverlayGeneration;
    const controller = new AbortController();
    zenithOverlayController = controller;
    const requestedSources = [...zenithOverlayIndexes].join('\n');
    const params = activeParameters();
    params.set('catalog_token', context.dataset.catalogToken || '');
    params.set('icon_map', catalogueIconQuery());
    [...zenithOverlayIndexes].forEach((sourceIndex) => {
      const style = overlayStyle(sourceIndex);
      params.append('comparison_source_key', String(sourceIndex));
      params.append('comparison_colour', style.colour);
      params.append('comparison_line_style', style.lineStyle);
    });
    params.set('start_time', context.dataset.resultStart);
    params.set('end_time', context.dataset.resultEnd);
    if (Number(context.dataset.resultSourceIndex) >= 0) params.set('target_source_key', context.dataset.resultSourceKey || context.dataset.resultSourceIndex);
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
    let payload;
    try {
      iconMapParameters(params);
      const response = await fetch('/api/v1/windows/plot-overlay?' + params.toString(), {signal: controller.signal});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      payload = await response.json();
    } catch (error) {
      const changed = generation !== zenithOverlayGeneration || requestedSources !== [...zenithOverlayIndexes].join('\n');
      if (changed || error.name === 'AbortError') return { ok: false, cancelled: true, error: 'request superseded' };
      console.warn('Comparison plot refresh failed', error);
      return { ok: false, cancelled: false, error: String(error.message || error) };
    } finally {
      if (zenithOverlayController === controller) zenithOverlayController = null;
    }
    if (generation !== zenithOverlayGeneration || requestedSources !== [...zenithOverlayIndexes].join('\n')) return { ok: false, cancelled: true, error: 'request superseded' };
    if (requestedTheme !== (document.documentElement.dataset.resolvedTheme || 'light') || requestedTimezone !== getTimezonePreference()) return { ok: false, cancelled: true, error: 'display settings changed' };
    plot.innerHTML = payload.svg;
    const preferences = document.getElementById('result-display-preferences');
    if (preferences) { preferences.dataset.plotTheme = requestedTheme; preferences.dataset.plotTimezoneLabel = requestedTimezone === 'utc' ? 'UTC' : observerTimezoneLabel(); preferences.dataset.plotOffsetHours = String(requestedTimezone === 'utc' ? 0 : observerOffsetHours()); }
    payload.comparison_sources?.forEach((source) => { const style=overlayStyle(source.source_key || String(source.index)); style.label = source.display_name; style.svgId = 'zenith-overlay-' + source.index; });
    renderZenithCurveControls();
    payload.comparison_windows && renderOverlayWindowSummary(payload);
    return { ok: true, cancelled: false };
  };
    const selectedTargetWindows = (payload) => Array.isArray(payload?.comparison_windows) ? payload.comparison_windows.flatMap((item) => (item.windows || []).map((window) => ({ ...window, sourceKey: item.source_key, sourceName: item.display_name }))) : [];
    const renderOverlayWindowSummary = (payload) => {
      const plotPanel = document.querySelector('.plot-panel');
      if (!plotPanel) return;
      let summary = document.getElementById('overlay-window-summary');
      if (!summary) { summary = document.createElement('section'); summary.id = 'overlay-window-summary'; summary.className = 'overlay-window-summary'; plotPanel.insertBefore(summary, plotPanel.querySelector('.scientific-plot')); }
      const target = document.querySelector('[data-plan-source-name]');
      const targetWindows = JSON.parse(document.getElementById('detail-query-context')?.dataset.fullWindowRanges || '[]').map((range) => ({ start: range[0], end: range[1], sourceName: target?.dataset.planSourceName || '' }));
      const allWindows = [...targetWindows, ...selectedTargetWindows(payload)].sort((left, right) => String(left.start || '').localeCompare(String(right.start || '')));
      summary.innerHTML = '<strong>' + translate('sortedObservationWindows') + '</strong>' + (allWindows.length ? '<ol>' + allWindows.map((window) => '<li><span>' + String(window.sourceName || '').replaceAll('&','&amp;').replaceAll('<','&lt;') + '</span> <time>' + formatDisplayTime(new Date(window.start)) + ' ' + translate('to') + ' ' + formatDisplayTime(new Date(window.end)) + '</time></li>').join('') + '</ol>' : '<p>' + translate('noFullWindows') + '</p>');
    };
    const refreshZenithOverlays = () => {
      const operation = zenithRefreshTail.then(() => runZenithOverlayRefresh());
      zenithRefreshTail = operation.catch(() => ({ ok: false, cancelled: true, error: 'request superseded' }));
      return operation;
    };

  const restoreZenithOverlayState = () => {
    document.querySelectorAll('#zenith-curve-list .zenith-curve-row').forEach((row) => {
      const sourceIndex = row.dataset.sourceIndex;
      if (!sourceIndex) return;
      zenithOverlayIndexes.add(sourceIndex);
      const name = row.querySelector('.zenith-legend-source')?.textContent || ('Source ' + sourceIndex);
      const colour = row.querySelector('input[type=color]')?.value || overlayPalette[zenithOverlayIndexes.size % overlayPalette.length];
      const lineStyle = row.querySelector('select')?.value || 'dashdot';
      zenithOverlayStyles.set(sourceIndex, { colour, lineStyle, label: name, svgId: row.dataset.svgId || ('zenith-overlay-' + sourceIndex) });
    });
    renderZenithCurveControls();
  };

  const renderZenithCurveControls = () => {
    const list = document.getElementById('zenith-curve-list');
    if (!panel || !list) return;
    panel.hidden = zenithOverlayIndexes.size === 0;
    list.replaceChildren(...[...zenithOverlayIndexes].map((sourceIndex) => {
      const style = overlayStyle(sourceIndex);
      const row = document.createElement('div'); row.className = 'zenith-curve-row';
      row.dataset.sourceIndex = String(sourceIndex);
      row.dataset.svgId = style.svgId || ('zenith-overlay-' + sourceIndex);
      const name = document.createElement('button'); name.type = 'button'; name.className = 'zenith-legend-source'; name.textContent = style.label;
      const colour = document.createElement('input'); colour.type = 'color'; colour.value = style.colour; colour.setAttribute('aria-label', translate('curveColour'));
      const line = document.createElement('select'); [['solid','—'],['dotted','··'],['dashdot','-·']].forEach(([value,label]) => line.add(new Option(label, value))); line.value = style.lineStyle; line.setAttribute('aria-label', translate('curveLineStyle'));
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'secondary-button'; remove.textContent = translate('removeCurve');
      const curveGroup = () => document.getElementById(style.svgId || ('zenith-overlay-' + sourceIndex));
      const applyVisualStyle = () => {
        const path = curveGroup()?.querySelector('path'); if (!path) return;
        path.style.stroke = style.colour;
        path.style.strokeDasharray = style.lineStyle === 'solid' ? 'none' : style.lineStyle === 'dotted' ? '1.35,2.7' : '8.64,2.16,1.35,2.16';
      };
      const update = () => { style.colour = colour.value; style.lineStyle = line.value; applyVisualStyle(); };
      colour.addEventListener('input', update); colour.addEventListener('change', update); line.addEventListener('change', update);
      remove.addEventListener('click', () => { zenithOverlayGeneration++; zenithOverlayController?.abort(); curveGroup()?.remove(); zenithOverlayIndexes.delete(sourceIndex); zenithOverlayStyles.delete(String(sourceIndex)); renderZenithCurveControls(); void refreshZenithOverlays(); if (dialogAddZenith?.dataset.useSource === String(sourceIndex) || dialogUseSource?.dataset.useSource === String(sourceIndex)) { dialogAddZenith.textContent = translate('addZenithOverlay'); dialogAddZenith.dataset.i18n = 'addZenithOverlay'; dialogAddZenith.dataset.overlayAdded = 'false'; } });
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
    const specifiedControls = document.getElementById('specified-time-controls');
    const specifiedKind = document.getElementById('specified-time-kind');
    const specifiedStart = document.getElementById('specified-time-start');
    const specifiedEnd = document.getElementById('specified-time-end');
    const specifiedEndControl = document.getElementById('specified-time-end-control');
    const specifiedApply = document.getElementById('specified-time-apply');
    const specifiedError = document.getElementById('specified-time-error');
    const restoredFromPageCache = document.documentElement.dataset.skywardResultRestored === 'true';
    let restoredMapState = null;
    try {
      restoredMapState = JSON.parse(sessionStorage.getItem('skyward.pending-result-map-state') || 'null');
    } catch (_) { restoredMapState = null; }
    sessionStorage.removeItem('skyward.pending-result-map-state');
    if (mode && ['instant', 'trajectory', 'specified'].includes(restoredMapState?.mode)) mode.value = restoredMapState.mode;
    if (specifiedKind && ['point', 'range'].includes(restoredMapState?.specifiedKind)) specifiedKind.value = restoredMapState.specifiedKind;
    const restoredStart = restoredMapState?.specifiedStart ? selectedInputDate({ value: restoredMapState.specifiedStart }) : null;
    const restoredEnd = restoredMapState?.specifiedEnd ? selectedInputDate({ value: restoredMapState.specifiedEnd }) : null;
    let specifiedStartInstant = restoredStart && Number.isFinite(restoredStart.getTime()) ? restoredStart : new Date(context.dataset.resultStart || Date.now());
    let specifiedEndInstant = restoredEnd && Number.isFinite(restoredEnd.getTime()) ? restoredEnd : new Date(Math.min(new Date(context.dataset.resultEnd || specifiedStartInstant.getTime() + 3600000).getTime(), specifiedStartInstant.getTime() + 3600000));
    let sharedLiveInstant = new Date();
    let allSkyRequestGeneration = 0, allSkyController;
    const setSpecifiedInputs = () => {
      if (specifiedStart) specifiedStart.value = localDatetimeValue(specifiedStartInstant);
      if (specifiedEnd) specifiedEnd.value = localDatetimeValue(specifiedEndInstant);
    };
    const configureSpecifiedControls = () => {
      const active = mode?.value === 'specified';
      if (specifiedControls) specifiedControls.hidden = !active;
      if (specifiedEndControl) specifiedEndControl.hidden = !active || specifiedKind?.value !== 'range';
      if (active && specifiedStart && !specifiedStart.value) setSpecifiedInputs();
    };
    const mapStatusParameters = (params, requestMode) => {
      if (requestMode === 'trajectory') {
        activeSkyInstant = new Date(context.dataset.windowDisplayTime || context.dataset.resultStart);
        params.set('at_time', context.dataset.resultStart);
        params.set('trajectory_display_time', activeSkyInstant.toISOString());
        params.set('status_mode', 'trajectory');
        params.set('trajectory_end', context.dataset.resultEnd);
        params.set('trajectory_enforce_current_pointing', 'false');
        if (context.dataset.fullWindowRanges) params.set('trajectory_ranges', context.dataset.fullWindowRanges);
      } else if (requestMode === 'specified') {
        activeSkyInstant = new Date(specifiedStartInstant);
        params.set('at_time', activeSkyInstant.toISOString());
        params.set('status_mode', 'specified');
        params.set('specified_kind', specifiedKind?.value || 'point');
        params.delete('trajectory_ranges');
        params.set('trajectory_enforce_current_pointing', 'false');
        params.set('trajectory_display_time', activeSkyInstant.toISOString());
        if (specifiedKind?.value === 'range') params.set('specified_end', specifiedEndInstant.toISOString());
        else params.delete('specified_end');
      } else {
        activeSkyInstant = sharedLiveInstant;
        params.set('at_time', activeSkyInstant.toISOString());
        params.set('status_mode', 'instant');
        params.delete('trajectory_end'); params.delete('trajectory_ranges'); params.delete('specified_end');
      }
      return params;
    };
    const validateSpecified = () => {
      const start = selectedInputDate(specifiedStart), end = selectedInputDate(specifiedEnd);
      if (!Number.isFinite(start.getTime())) return translate('specifiedTimeInvalid');
      specifiedStartInstant = start;
      if ((specifiedKind?.value || 'point') === 'point') return null;
      if (!Number.isFinite(end.getTime()) || end <= start) return translate('specifiedTimeOrder');
      if ((end - start) > 86400000) return translate('specifiedTimeLimit');
      specifiedEndInstant = end;
      return null;
    };
    if (restoredFromPageCache) {
      const cachedStart = specifiedStart ? selectedInputDate(specifiedStart) : null;
      const cachedEnd = specifiedEnd ? selectedInputDate(specifiedEnd) : null;
      if (cachedStart && Number.isFinite(cachedStart.getTime())) specifiedStartInstant = cachedStart;
      if (cachedEnd && Number.isFinite(cachedEnd.getTime())) specifiedEndInstant = cachedEnd;
    } else {
      setSpecifiedInputs();
    }
    const cachedDisplayTime = allSky.dataset.skywardDisplayTime || document.querySelector('[data-local-fov-map]')?.dataset.skywardDisplayTime;
    if (restoredFromPageCache && cachedDisplayTime && Number.isFinite(new Date(cachedDisplayTime).getTime())) {
      activeSkyInstant = new Date(cachedDisplayTime);
      sharedLiveInstant = new Date(cachedDisplayTime);
    }
    configureSpecifiedControls();
    const refresh = async () => {
      const generation = ++allSkyRequestGeneration;
      allSkyController?.abort(); allSkyController=new AbortController();
      const requestMode = mode?.value || 'instant';
      const params = appendCameraParameters(appendLayerParameters(activeParameters()),allSky);
      iconMapParameters(params);
      params.set('language', getLanguage());
      params.set('display_frame', getCoordinateFrame());
      if (requestMode === 'trajectory' && context.dataset.highlightIndexes) {
        params.set('highlight_indexes', context.dataset.highlightIndexes);
      }
      if (Number(context.dataset.resultSourceIndex) >= 0) params.set('selected_source_key', context.dataset.resultSourceKey || context.dataset.resultSourceIndex);
      mapStatusParameters(params, requestMode);
      try {
      const response = await fetch('/api/v1/sky/current?' + params.toString(),{signal:allSkyController.signal});
      const payload=await response.json();
      if(!response.ok)throw new Error('HTTP '+response.status);
      allSky.dataset.skywardDisplayTime = activeSkyInstant.toISOString();
      const timeLabel = document.querySelector('[data-result-map-time]');
      if (timeLabel) { timeLabel.dataset.utc = activeSkyInstant.toISOString(); timeLabel.textContent = formatDisplayTime(activeSkyInstant); }
      if (response.ok && generation === allSkyRequestGeneration && mode?.value === requestMode) {
        allSky.innerHTML = payload.svg;
        updateResultStatusCard(payload, requestMode);
        if (requestMode === 'instant') stampLiveOption(mode?.querySelector('[data-live-option]'), activeSkyInstant);
        allSky.dispatchEvent(new Event('skyward:map-replaced'));
      }
      } catch(error) { if(error.name!=='AbortError')console.warn('All-sky refresh failed',error); }
    };
    let localRequestGeneration = 0, localController;
    const refreshLocal = async () => {
      const generation = ++localRequestGeneration;
      const requestMode = mode?.value || 'instant';
      const local = document.querySelector('[data-local-fov-map]'); if (!local) return;
      localController?.abort(); localController=new AbortController(); invalidateGaia(local);
      const params = appendCameraParameters(appendLayerParameters(activeParameters()),local);
      iconMapParameters(params);
      params.set('language', getLanguage()); params.set('display_frame', getCoordinateFrame());
      if (requestMode === 'trajectory' && context.dataset.highlightIndexes) params.set('highlight_indexes', context.dataset.highlightIndexes);
      mapStatusParameters(params, requestMode);
      if (Number(context.dataset.resultSourceIndex) >= 0) params.set('target_source_key', context.dataset.resultSourceKey || context.dataset.resultSourceIndex);
      else { params.set('target_ra_deg', context.dataset.resultSourceRa); params.set('target_dec_deg', context.dataset.resultSourceDec); params.set('target_radius_deg', context.dataset.resultSourceRadius); }
      try {
        const response = await fetch('/api/v1/sky/local-fov?' + params.toString(),{signal:localController.signal});
        const payload=await response.json(); if(!response.ok)throw new Error('HTTP '+response.status);
        if (generation === localRequestGeneration && mode?.value === requestMode) {
          local.innerHTML = payload.svg;
          local.dataset.skywardDisplayTime = activeSkyInstant.toISOString();
          local.dispatchEvent(new Event('skyward:map-replaced')); refreshGaiaLayer(local,params,'local-fov');
        }
      } catch(error) { if(error.name!=='AbortError')console.warn('Local FoV refresh failed',error); }
    };
    allSky.addEventListener('skyward:camera-change',()=>refresh());
    document.querySelector('[data-local-fov-map]')?.addEventListener('skyward:camera-change',()=>refreshLocal());
    document.getElementById('local-gaia-filter-apply')?.addEventListener('click', () => {
      const filters=gaiaFilterParameters();
      if(!filters){showGaiaFilterError(translate('gaiaFilterInvalid'));return;}
      showGaiaFilterError();
      const button=document.getElementById('local-gaia-filter-apply');
      if(button){button.dataset.gaiaEnabled='true';button.setAttribute('aria-pressed','true');}
      refreshLocal();
    });
    ['local-gaia-radius','local-gaia-max-mag','local-gaia-limit'].forEach(id=>document.getElementById(id)?.addEventListener('input',()=>showGaiaFilterError()));
    const refreshExplanation = () => {
      const note = document.getElementById('result-status-explanation');
      document.getElementById('add-tracked-zenith-curves')?.toggleAttribute('hidden', mode?.value !== 'trajectory');
      document.getElementById('tracked-fov-legend')?.toggleAttribute('hidden', mode?.value !== 'trajectory');
      document.getElementById('local-tracked-fov-legend')?.toggleAttribute('hidden', mode?.value !== 'trajectory');
      configureSpecifiedControls();
      if (!note) return;
      const key = mode?.value === 'trajectory' ? 'trajectoryStatusExplanation' : mode?.value === 'specified' ? 'specifiedStatusExplanation' : 'instantStatusExplanation';
      note.dataset.i18n = key;
      note.textContent = translate(key);
    };
    const addTrackedButton = document.getElementById('add-tracked-zenith-curves');
    mode?.addEventListener('change', () => { if (mode.value === 'instant') sharedLiveInstant = new Date(); refreshExplanation(); refresh(); refreshLocal(); });
    addTrackedButton?.addEventListener('click', async () => {
      if (mode?.value !== 'trajectory' || !context.dataset.highlightIndexes) return;
      const keys = context.dataset.highlightIndexes.split(',').map((value) => value.trim()).filter(Boolean);
      keys.forEach((key) => zenithOverlayIndexes.add(key));
      setMapActionStatus('all-sky', translate('curveAdding'), 'loading');
      const outcome = await refreshZenithOverlays();
      if (outcome?.ok) setMapActionStatus('all-sky', translate('curveAdded'), 'success');
    });
    specifiedKind?.addEventListener('change', () => { configureSpecifiedControls(); });
    specifiedApply?.addEventListener('click', () => { const error = validateSpecified(); if (specifiedError) { specifiedError.textContent = error || ''; specifiedError.hidden = !error; } if (!error) { refreshExplanation(); refresh(); refreshLocal(); } });
    specifiedStart?.addEventListener('change', validateSpecified);
    specifiedEnd?.addEventListener('change', validateSpecified);
    document.addEventListener('skyward:refresh-realtime', () => { if (mode?.value === 'instant') { sharedLiveInstant = new Date(); refresh(); refreshLocal(); } });
    document.addEventListener('skyward:language-change', refreshExplanation);
    refreshExplanation();
    if (restoredFromPageCache) restoreZenithOverlayState();
    if (!restoredFromPageCache) window.queueMicrotask(() => { refresh(); refreshLocal(); });
    document.addEventListener('skyward:language-change', () => { refresh(); refreshLocal(); });
    document.addEventListener('skyward:coordinate-change', () => { refresh(); refreshLocal(); });
    document.addEventListener('skyward:catalogues-change', () => { refresh(); refreshLocal(); });
    document.addEventListener('skyward:catalogue-icons-change', () => { refresh(); refreshLocal(); });
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
    const windowEditor = document.getElementById("plan-window-editor"), notesInput = document.getElementById("plan-notes");
    const sourceElement = document.getElementById("plan-source-name"), constraintsElement = document.getElementById("plan-constraints"), errorElement = document.getElementById("plan-range-error");
    const pagePlanContext = document.querySelector("[data-plan-source-name]") || document.body;
    const savePlot = document.getElementById("plan-save-plot");
    const selectionStatus = document.querySelector('[data-plan-selection-status]');
    const alternativeProgress = document.querySelector('[data-plan-alternative-status]');
    const detailContext = document.getElementById("detail-query-context");
    const alternativeUpload = document.getElementById('alternative-catalogue-upload');
    const alternativeUploadTrigger = document.getElementById('alternative-catalogue-upload-trigger');
    const alternativeUploadName = document.getElementById('alternative-catalogue-name');
    const alternativeUploadStatus = document.getElementById('alternative-catalogue-status');
    let alternativeCatalogueToken = detailContext?.dataset.alternativeCatalogToken || null;
    const syncAlternativeCatalogue = (data = null) => {
      alternativeCatalogueToken = data?.token || null;
      if (detailContext) detailContext.dataset.alternativeCatalogToken = alternativeCatalogueToken || '';
      if (alternativeUploadName && data) alternativeUploadName.textContent = data.label || '';
      if (alternativeUploadStatus) alternativeUploadStatus.textContent = data ? translate('alternativeCatalogueUploaded') : translate('alternativeCatalogueDefault');
    };
    alternativeUploadTrigger?.addEventListener('click', () => alternativeUpload?.click());
    alternativeUpload?.addEventListener('change', async (event) => {
      const file = event.target.files?.[0]; if (!file) return;
      if (alternativeUploadName) alternativeUploadName.textContent = file.name;
      if (alternativeUploadStatus) alternativeUploadStatus.textContent = translate('catalogueUploading');
      try {
        const body = new FormData(); body.append('file', file);
        const response = await fetch('/api/v1/catalogues/upload', { method: 'POST', body });
        const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'HTTP ' + response.status);
        syncAlternativeCatalogue(data);
      } catch (error) {
        if (alternativeUploadStatus) alternativeUploadStatus.textContent = translate('catalogueUploadFailed') + ': ' + error.message;
      }
    });
    if (alternativeCatalogueToken) syncAlternativeCatalogue({token: alternativeCatalogueToken, label: alternativeCatalogueToken});
    const duplicateDialog = document.getElementById("duplicate-plan-dialog");
    const clearPlanDialog = document.getElementById("clear-plan-dialog");
    const previewDialog = document.getElementById("observation-plan-preview-dialog");
    const previewList = document.getElementById("observation-plan-preview-list");
    if (!dialog || !form || !windowEditor) return;
    const storageKey = "skyward.observation-plan.v3";
    let activeWindows = [];
    let planEntries = [];
    const normalisePlanEntry = (entry) => {
      const legacyWindow = entry?.windowStart && entry?.windowEnd ? [{
        windowStart: entry.windowStart, windowEnd: entry.windowEnd,
        planStart: entry.planStart || entry.windowStart, planEnd: entry.planEnd || entry.windowEnd,
        alternatives: entry.alternatives, alternativeSummary: entry.alternativeSummary,
        alternativeStatus: entry.alternativeStatus, alternativeError: entry.alternativeError,
      }] : [];
      const rawWindows = Array.isArray(entry?.windows) && entry.windows.length ? entry.windows : legacyWindow;
      const windows = rawWindows.filter((window) => window?.windowStart && window?.windowEnd).map((window, index) => ({
        windowId: String(window.windowId || (entry.id + "-window-" + (index + 1))),
        windowStart: window.windowStart, windowEnd: window.windowEnd,
        planStart: window.planStart || window.windowStart, planEnd: window.planEnd || window.windowEnd,
        alternatives: Array.isArray(window.alternatives) ? window.alternatives : [],
        alternativeSummary: window.alternativeSummary || null,
        alternativeStatus: window.alternativeStatus || (entry.catalogueTarget ? "pending" : "unavailable"),
        alternativeError: window.alternativeError || null,
      }));
      return { ...entry, windows };
    };
    try { sessionStorage.removeItem("skyward.observation-plan.v2"); } catch (_) {}
    try {
      const stored = JSON.parse(sessionStorage.getItem(storageKey) || "null");
      if (stored?.version === 3 && Array.isArray(stored.entries)) {
        planEntries = stored.entries.filter((entry) => entry && typeof entry.id === "string" && typeof entry.source === "string").map(normalisePlanEntry).filter((entry) => entry.windows.length);
      }
    } catch (_) { planEntries = []; }
    const savePlanEntries = () => {
      try { sessionStorage.setItem(storageKey, JSON.stringify({ version: 3, entries: planEntries })); return true; }
      catch (error) {
        console.warn("Unable to persist observing plan", error);
        window.alert(getLanguage() === "zh" ? "浏览器存储空间不足，当前观测计划未能持久保存。" : "Browser storage is full; the current observing plan could not be persisted.");
        return false;
      }
    };
    const batchNode = document.getElementById('batch-plan-import');
    if (batchNode) {
      try {
        const batchEntries = JSON.parse(batchNode.dataset.batchPlanEntries || '[]');
        const known = new Set(planEntries.map((entry) => entry.sourceKey || entry.source));
        const fresh = batchEntries.filter((entry) => !known.has(entry.sourceKey || entry.source)).map(normalisePlanEntry);
        if (fresh.length) { planEntries = planEntries.concat(fresh); savePlanEntries(); }
        batchNode.dataset.batchImported = 'true';
      } catch (_) {}
    }

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
    const constraintText = () => { const raw = pagePlanContext.dataset.planConstraints || ""; return getLanguage() !== "zh" ? raw : raw.replace("Sun altitude", "太阳高度").replace("Moon separation", "月亮角距").replace("Zenith", "天顶角").replace("minimum", "最短窗口"); };
    const safeName = (value) => String(value || "target").replace(/[^\p{L}\p{N}._+-]+/gu, "_").replace(/^_+|_+$/g, "") || "target";
    const exportLocalFovSvg = () => {
      const live = document.querySelector("[data-local-fov-map] svg");
      if (!live) return null;
      const svg = live.cloneNode(true);
      const namespace = "http://www.w3.org/2000/svg";
      const viewBox = (svg.getAttribute("viewBox") || "0 0 680 620").split(/\s+/).map(Number);
      const [vx, vy, vw, vh] = viewBox.length === 4 && viewBox.every(Number.isFinite) ? viewBox : [0, 0, 680, 620];
      // Saved local maps must be standalone, readable light-background figures.
      // The live map keeps theme variables and interactive hit areas; this copy
      // receives its own presentation layer without mutating the visible map.
      const exportStyle = document.createElementNS(namespace, "style");
      exportStyle.textContent = `.fov-map-svg{--sky:#ffffff;--surface:#ffffff;--line:#8993a7;--muted:#49515d;--text:#151820;background:#ffffff;overflow:visible}.fov-map-svg .export-background{fill:#ffffff}.fov-map-svg .fov-surface{fill:#ffffff!important;stroke:#8993a7!important}.fov-map-svg .map-clipped{opacity:1}.fov-map-svg .source-marker .source-symbol{filter:none}.fov-map-svg .coordinate-grid{stroke:#aab1bb!important}.fov-map-svg text{font-family:Arial,sans-serif}.export-source-id{font:700 11px Arial,sans-serif;fill:#111820;paint-order:stroke;stroke:#ffffff;stroke-width:3px;pointer-events:none}.export-source-legend rect{fill:#ffffff;fill-opacity:.94;stroke:#6b7280;stroke-width:1}.export-source-legend text{font:11px Arial,sans-serif;fill:#111820}`;
      svg.insertBefore(exportStyle, svg.firstChild);
      const background = document.createElementNS(namespace, "rect");
      background.setAttribute("class", "export-background"); background.setAttribute("x", String(vx)); background.setAttribute("y", String(vy)); background.setAttribute("width", String(vw)); background.setAttribute("height", String(vh));
      svg.insertBefore(background, exportStyle.nextSibling);
      const targetKey = svg.dataset.centerSourceKey || "";
      const markers = [...svg.querySelectorAll(".source-marker[data-source-key]")];
      const unique = new Map();
      markers.forEach((marker) => {
        const key = marker.dataset.sourceKey || "";
        if (key && !unique.has(key)) unique.set(key, marker);
      });
      const ordered = [...unique.entries()].sort(([left], [right]) => {
        if (left === targetKey) return -1;
        if (right === targetKey) return 1;
        return left.localeCompare(right);
      });
      const sourceIds = new Map(ordered.map(([key], index) => [key, index + 1]));
      const idLayer = document.createElementNS(namespace, "g");
      idLayer.setAttribute("class", "export-source-ids");
      ordered.forEach(([key, marker]) => {
        const x = Number(marker.dataset.x), y = Number(marker.dataset.y);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return;
        const label = document.createElementNS(namespace, "text");
        label.setAttribute("class", "export-source-id"); label.setAttribute("x", String(x + 7)); label.setAttribute("y", String(y - 7));
        label.textContent = String(sourceIds.get(key)); idLayer.append(label);
      });
      const columns = Math.max(1, Math.min(3, Math.ceil(ordered.length / 15)));
      const rows = Math.max(1, Math.ceil(ordered.length / columns));
      const legend = document.createElementNS(namespace, "g");
      legend.setAttribute("class", "export-source-legend");
      const legendX = vx + 10, legendY = vy + vh + 10, columnWidth = 245;
      const legendWidth = columns * columnWidth + 16, legendHeight = rows * 16 + 27;
      const exportWidth = Math.max(vw, legendX + legendWidth + 10 - vx);
      const exportHeight = Math.max(vh, legendY + legendHeight + 10 - vy);
      svg.setAttribute("viewBox", [vx, vy, exportWidth, exportHeight].join(" "));
      background.setAttribute("width", String(exportWidth)); background.setAttribute("height", String(exportHeight));
      const legendRect = document.createElementNS(namespace, "rect");
      legendRect.setAttribute("x", String(legendX)); legendRect.setAttribute("y", String(legendY));
      legendRect.setAttribute("width", String(legendWidth)); legendRect.setAttribute("height", String(legendHeight)); legend.append(legendRect);
      const heading = document.createElementNS(namespace, "text"); heading.setAttribute("x", String(legendX + 8)); heading.setAttribute("y", String(legendY + 16)); heading.setAttribute("font-weight", "700"); heading.textContent = getLanguage() === "zh" ? "源编号 / 源名" : "Source ID / name"; legend.append(heading);
      ordered.forEach(([key, marker], index) => {
        const title = marker.dataset.sourceName || marker.querySelector("title")?.textContent || key;
        const column = Math.floor(index / rows), row = index % rows;
        const item = document.createElementNS(namespace, "text");
        item.setAttribute("x", String(legendX + 8 + column * columnWidth)); item.setAttribute("y", String(legendY + 32 + row * 16));
        item.textContent = `${sourceIds.get(key)}: ${title}`; legend.append(item);
      });
      svg.append(idLayer, legend);
      return svg.outerHTML;
    };
    const entryId = () => globalThis.crypto?.randomUUID?.() || (Date.now().toString(36) + "-" + Math.random().toString(36).slice(2));
    const numberOrNull = (value) => value === undefined || value === null || String(value).trim() === "" ? null : Number(value);
    const editorInput = (kind, windowId) => [...windowEditor.querySelectorAll("[data-plan-window-" + kind + "-input]")].find((input) => input.dataset["planWindow" + kind[0].toUpperCase() + kind.slice(1) + "Input"] === windowId);
    const renderWindowEditor = () => {
      windowEditor.replaceChildren();
      activeWindows.forEach((window, index) => {
        const row = document.createElement("fieldset"); row.className = "plan-window-edit-row"; row.dataset.planWindowEditorRow = window.windowId;
        const legend = document.createElement("legend"); legend.textContent = translate("planWindow") + " " + (index + 1); row.append(legend);
        const grid = document.createElement("div"); grid.className = "plan-window-edit-grid";
        const startField = document.createElement("div"); startField.className = "form-field";
        const startLabel = document.createElement("label"); startLabel.htmlFor = "plan-start-" + index; startLabel.textContent = translate("plannedStart");
        const start = document.createElement("input"); start.id = "plan-start-" + index; start.type = "datetime-local"; start.step = "1"; start.required = true; start.dataset.planWindowStartInput = window.windowId; start.value = localPlanTime(window.planStart);
        startField.append(startLabel, start);
        const endField = document.createElement("div"); endField.className = "form-field";
        const endLabel = document.createElement("label"); endLabel.htmlFor = "plan-end-" + index; endLabel.textContent = translate("plannedEnd");
        const endInput = document.createElement("input"); endInput.id = "plan-end-" + index; endInput.type = "datetime-local"; endInput.step = "1"; endInput.required = true; endInput.dataset.planWindowEndInput = window.windowId; endInput.value = localPlanTime(window.planEnd);
        endField.append(endLabel, endInput); grid.append(startField, endField); row.append(grid); windowEditor.append(row);
      });
    };
    const readEditedWindows = () => activeWindows.map((window) => ({
      ...window,
      planStart: selectedInputDate(editorInput("start", window.windowId)).toISOString(),
      planEnd: selectedInputDate(editorInput("end", window.windowId)).toISOString(),
    }));
    const withinActiveWindows = (windows) => windows.length > 0 && windows.every((window) => {
      const startTime = new Date(window.planStart), endTime = new Date(window.planEnd);
      return startTime >= new Date(window.windowStart) && endTime <= new Date(window.windowEnd) && endTime > startTime;
    });
    const selectedResultWindows = () => [...document.querySelectorAll("[data-plan-window-select]:checked")].map((choice, index) => ({
      windowId: entryId() + "-window-" + (index + 1),
      windowStart: choice.dataset.windowStart, windowEnd: choice.dataset.windowEnd,
      planStart: choice.dataset.planStart || choice.dataset.windowStart, planEnd: choice.dataset.planEnd || choice.dataset.windowEnd,
      alternatives: [], alternativeSummary: null,
      alternativeStatus: Number(detailContext.dataset.resultSourceIndex) >= 0 ? "pending" : "unavailable", alternativeError: null,
    }));
    const buildEntry = (windows) => {
      const telescopeQuery = Object.fromEntries(appendTelescopeParameters(new URLSearchParams(), detailContext));
      return {
        id: entryId(), addedAt: Date.now(),
        source: pagePlanContext.dataset.planSourceName || "",
        sourceKey: detailContext.dataset.resultSourceKey || "",
        catalogueTarget: Number(detailContext.dataset.resultSourceIndex) >= 0,
        ra: pagePlanContext.dataset.planRa || "", dec: pagePlanContext.dataset.planDec || "",
        radius: pagePlanContext.dataset.planRadius || "", constraints: pagePlanContext.dataset.planConstraints || "",
        constraintValues: {
          sun_max_altitude_deg: numberOrNull(detailContext.dataset.sunMaxAltitudeDeg),
          moon_min_separation_deg: numberOrNull(detailContext.dataset.moonMinSeparationDeg),
          target_min_zenith_deg: numberOrNull(detailContext.dataset.targetMinZenithDeg),
          target_max_zenith_deg: numberOrNull(detailContext.dataset.targetMaxZenithDeg),
          minimum_window_seconds: numberOrNull(detailContext.dataset.minimumWindowSeconds),
        },
        catalogToken: detailContext.dataset.catalogToken || null, catalogTokens: detailContext.dataset.catalogTokens || null,
        alternativeCatalogToken: alternativeCatalogueToken || null,
        nominalRadiusDeg: numberOrNull(detailContext.dataset.nominalRadiusDeg),
        searchStart: detailContext.dataset.resultStart, searchEnd: detailContext.dataset.resultEnd,
        windows,
        notes: notesInput?.value.trim() || "",
        plotSvg: savePlot?.checked ? document.querySelector(".scientific-plot svg")?.outerHTML || null : null,
        localFovSvg: savePlot?.checked ? exportLocalFovSvg() : null,
        telescopeQuery,
      };
    };
    const planCopy = (zh, en) => getLanguage() === "zh" ? zh : en;
    const alternativeLabel = (window) => {
      if (window.alternativeStatus === "pending") return planCopy("正在计算备选源…", "Calculating alternatives…");
      if (window.alternativeStatus === "failed") return planCopy("备选源计算失败：", "Alternative calculation failed: ") + (window.alternativeError || "-");
      if (window.alternativeStatus === "unavailable") return planCopy("自定义目标没有目录备选源。", "No catalogue alternatives are available for a custom target.");
      const count = Array.isArray(window.alternatives) ? window.alternatives.length : 0;
      const shortfall = window.alternativeSummary?.candidate_shortfall;
      return planCopy("已精确验证备选源：", "Exactly validated alternatives: ") + count + (shortfall ? " · " + shortfall : "");
    };
    const updateStoredWindow = (entryIdValue, windowId, patch) => {
      const entryIndex = planEntries.findIndex((item) => item.id === entryIdValue);
      if (entryIndex < 0) return;
      const windows = planEntries[entryIndex].windows.map((window) => window.windowId === windowId ? { ...window, ...patch } : window);
      planEntries[entryIndex] = { ...planEntries[entryIndex], windows };
      savePlanEntries();
      if (previewDialog?.open) renderPreview();
    };
    const alternativesInFlight = new Set();
    const alternativeRequestKey = (entry, window) => entry.id + ":" + window.windowId;
    const renderAlternativeProgress = () => {
      if (!alternativeProgress) return;
      let activeEntry = null;
      let activeWindowIndex = -1;
      for (const entry of planEntries) {
        const index = entry.windows.findIndex((window) => alternativesInFlight.has(alternativeRequestKey(entry, window)));
        if (index >= 0) { activeEntry = entry; activeWindowIndex = index; break; }
      }
      alternativeProgress.textContent = activeEntry ? translate("alternativeScreening") + ": " + activeEntry.source + " · " + translate("planWindow") + " " + (activeWindowIndex + 1) + "…" : "";
      alternativeProgress.hidden = !activeEntry;
    };
    const requestWindowAlternatives = async (entry, window) => {
      if (!entry.catalogueTarget || !entry.sourceKey) {
        updateStoredWindow(entry.id, window.windowId, { alternativeStatus: "unavailable", alternativeError: null });
        return;
      }
      const requestKey = alternativeRequestKey(entry, window);
      if (alternativesInFlight.has(requestKey)) return;
      alternativesInFlight.add(requestKey);
      renderAlternativeProgress();
      const query = new URLSearchParams(entry.telescopeQuery || {});
      try {
        const response = await fetch("/api/v1/windows/alternatives?" + query.toString(), {
          method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({
            source_key: entry.sourceKey, catalog_token: entry.catalogToken, catalog_tokens: entry.catalogTokens,
            alternative_catalog_token: entry.alternativeCatalogToken,
            nominal_radius_deg: entry.nominalRadiusDeg, search_start: entry.searchStart, search_end: entry.searchEnd,
            target_window_start: window.windowStart, target_window_end: window.windowEnd,
            constraints: entry.constraintValues, max_alternatives: 3, coarse_step_seconds: 900, shortlist_limit: 8,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          const detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail || payload);
          throw new Error(detail || ("HTTP " + response.status));
        }
        updateStoredWindow(entry.id, window.windowId, {
          alternatives: Array.isArray(payload.alternatives) ? payload.alternatives : [],
          alternativeSummary: payload.search_summary || null, alternativeStatus: "complete", alternativeError: null,
        });
      } catch (error) {
        updateStoredWindow(entry.id, window.windowId, { alternativeStatus: "failed", alternativeError: String(error.message || error) });
      } finally {
        alternativesInFlight.delete(requestKey);
        renderAlternativeProgress();
      }
    };
    const requestAlternatives = async (entry) => {
      for (const window of entry.windows.filter((candidate) => candidate.alternativeStatus === "pending")) {
        await requestWindowAlternatives(entry, window);
      }
    };
    const editPlanEntry = (entry) => {
      if (!entry || !dialog) return;
      activeWindows = entry.windows.map((window) => ({ ...window }));
      sourceElement.textContent = entry.source || "";
      constraintsElement.textContent = entry.constraints || "";
      renderWindowEditor();
      if (notesInput) notesInput.value = entry.notes || "";
      if (savePlot) savePlot.checked = Boolean(entry.plotSvg || entry.localFovSvg);
      form.dataset.editEntryId = entry.id;
      showError();
      previewDialog?.close();
      dialog.showModal();
    };
    const clearCurrentPlan = () => {
      if (!planEntries.length) return;
      clearPlanDialog?.showModal();
    };
    clearPlanDialog?.addEventListener("click", (event) => {
      const choice = event.target.closest("[data-clear-plan-choice]")?.dataset.clearPlanChoice;
      if (!choice) return;
      if (choice === "confirm") { planEntries = []; savePlanEntries(); renderPreview(); }
      clearPlanDialog.close();
    });
    clearPlanDialog?.addEventListener("cancel", (event) => { event.preventDefault(); clearPlanDialog.close(); });
    let planSort = 'added';
    const planSortSelect = document.getElementById('plan-sort-select');
    const sortedPlanEntries = () => [...planEntries].sort((left, right) => {
      if (planSort === 'duration') return (right.windows.reduce((sum, item) => sum + Math.max(0, new Date(item.windowEnd) - new Date(item.windowStart)), 0) - left.windows.reduce((sum, item) => sum + Math.max(0, new Date(item.windowEnd) - new Date(item.windowStart)), 0)) || 0;
      if (planSort === 'start') return String(left.windows.map(item => item.windowStart).sort()[0] || '').localeCompare(String(right.windows.map(item => item.windowStart).sort()[0] || ''));
      return Number(left.addedAt || 0) - Number(right.addedAt || 0);
    });
    planSortSelect?.addEventListener('change', () => { planSort = planSortSelect.value; renderPreview(); });
    const renderPreview = () => {
      if (!previewList) return;
      previewList.replaceChildren();
      if (!planEntries.length) {
        const empty = document.createElement("p"); empty.textContent = translate("noSavedPlan"); previewList.append(empty); return;
      }
      sortedPlanEntries().forEach((entry, index) => {
        const card = document.createElement("article"); card.className = "plan-preview-entry";
        const title = document.createElement("h3"); title.textContent = (index + 1) + ". " + entry.source; card.append(title);
        const details = document.createElement("p");
        const savedPlots = Number(Boolean(entry.plotSvg)) + Number(Boolean(entry.localFovSvg));
        details.textContent = "J2000 RA/Dec/radius: " + entry.ra + "° / " + entry.dec + "° / " + entry.radius + "° · " + (savedPlots ? planCopy("已保存 SVG：" + savedPlots + " 张", "saved SVGs: " + savedPlots) : planCopy("未保存图像", "plots not saved")); card.append(details);
        if (entry.notes) { const notes = document.createElement("p"); notes.textContent = planCopy("备注：", "Notes: ") + entry.notes; card.append(notes); }
        const windowList = document.createElement("div"); windowList.className = "plan-preview-windows";
        entry.windows.forEach((window, windowIndex) => {
          const windowCard = document.createElement("section"); windowCard.className = "plan-preview-window";
          const heading = document.createElement("h4"); heading.textContent = translate("planWindow") + " " + (windowIndex + 1); windowCard.append(heading);
          const interval = document.createElement("p"); interval.textContent = planCopy("计划时段（UTC）：", "Planned interval (UTC): ") + window.planStart + " — " + window.planEnd; windowCard.append(interval);
          const valid = document.createElement("p"); valid.textContent = planCopy("完整源窗口（UTC）：", "Full-footprint window (UTC): ") + window.windowStart + " — " + window.windowEnd; windowCard.append(valid);
          const status = document.createElement("p"); status.textContent = alternativeLabel(window); windowCard.append(status);
          if (window.alternatives?.length) {
            const list = document.createElement("ol"); list.className = "plan-preview-alternatives";
            window.alternatives.forEach((alternative) => {
              const item = document.createElement("li");
              const metrics = alternative.metrics || {}, windowData = alternative.window || {}, source = alternative.source || {};
              item.textContent = (source.name || source.source_key || "-") + " · " + (windowData.start || "-") + " — " + (windowData.end || "-") + " · " + planCopy("重叠 ", "overlap ") + (metrics.overlap_seconds ?? 0) + " s · " + planCopy("间隔 ", "gap ") + (metrics.gap_seconds ?? 0) + " s";
              list.append(item);
            });
            windowCard.append(list);
          }
          windowList.append(windowCard);
        });
        card.append(windowList);
        const actions = document.createElement("div"); actions.className = "plan-preview-entry-actions";
        const edit = document.createElement("button"); edit.type = "button"; edit.className = "secondary-button"; edit.dataset.planEdit = entry.id; edit.textContent = translate("editPlanEntry"); actions.append(edit);
        const remove = document.createElement("button"); remove.type = "button"; remove.className = "secondary-button"; remove.dataset.planDelete = entry.id; remove.textContent = translate("deletePlanEntry"); actions.append(remove);
        card.append(actions); previewList.append(card);
      });
    };
    const planTable = () => {
      const columns = ["record_type", "plan_entry", "window_number", "target_source", "source_name", "source_key", "ra_deg", "dec_deg", "radius_deg", "full_window_start_utc", "full_window_end_utc", "planned_start_utc", "planned_end_utc", "alternative_rank", "overlap_seconds", "gap_seconds", "target_window_seconds", "candidate_window_seconds", "duration_difference_seconds", "selection_stage", "alternative_status", "warnings", "constraints", "notes", "window_plot_file", "local_fov_file"];
      const rows = [];
      planEntries.forEach((entry, index) => {
        const stem = String(index + 1).padStart(3, "0") + "-" + safeName(entry.source);
        const windowPlotFile = entry.plotSvg ? "plots/" + stem + "-observing-window.svg" : "";
        const localFovFile = entry.localFovSvg ? "plots/" + stem + "-local-fov.svg" : "";
        entry.windows.forEach((window, windowIndex) => {
          rows.push(["target", index + 1, windowIndex + 1, entry.source, entry.source, entry.sourceKey, numberOrNull(entry.ra), numberOrNull(entry.dec), numberOrNull(entry.radius), window.windowStart, window.windowEnd, window.planStart, window.planEnd, "", "", "", "", "", "", "", window.alternativeStatus || "not_requested", [window.alternativeError, window.alternativeSummary?.candidate_shortfall, ...(window.alternativeSummary?.warnings || [])].filter(Boolean).join(" | "), entry.constraints, entry.notes, windowPlotFile, localFovFile]);
          (window.alternatives || []).forEach((alternative) => {
            const source = alternative.source || {}, metrics = alternative.metrics || {}, windowData = alternative.window || {};
            rows.push(["alternative", index + 1, windowIndex + 1, entry.source, source.name || "", source.source_key || "", numberOrNull(source.ra), numberOrNull(source.dec), numberOrNull(source.ext), windowData.start || "", windowData.end || "", "", "", alternative.rank ?? metrics.rank ?? "", metrics.overlap_seconds ?? "", metrics.gap_seconds ?? "", metrics.target_window_seconds ?? "", metrics.candidate_window_seconds ?? "", metrics.duration_difference_seconds ?? "", alternative.selection_stage || "", "complete", (alternative.warnings || []).join(" | "), entry.constraints, "", "", ""]);
          });
        });
      });
      return { columns, rows };
    };
    const xmlText = (value) => String(value ?? "").replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "").replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[character]));
    const spreadsheetColumn = (index) => { let name = ""; for (let value = index + 1; value; value = Math.floor((value - 1) / 26)) name = String.fromCharCode(65 + ((value - 1) % 26)) + name; return name; };
    const buildXlsxFiles = () => {
      const table = planTable(), rows = [table.columns, ...table.rows];
      const widths = table.columns.map((_, columnIndex) => Math.min(55, Math.max(10, rows.reduce((maximum, row) => Math.max(maximum, String(row[columnIndex] ?? "").length), 0) + 2)));
      const rowXml = rows.map((row, rowIndex) => {
        const cells = row.map((value, columnIndex) => {
          const reference = spreadsheetColumn(columnIndex) + (rowIndex + 1), numeric = typeof value === 'number' && Number.isFinite(value);
          const rowStyle = rowIndex === 0 ? 1 : row[0] === 'target' ? 2 : row[0] === 'alternative' ? 3 : 0;
          return `<c r="${reference}" s="${rowStyle}"${numeric ? '' : ' t="inlineStr"'}>${numeric ? `<v>${value}</v>` : `<is><t xml:space="preserve">${xmlText(value)}</t></is>`}</c>`;
        }).join("");
        return `<row r="${rowIndex + 1}">${cells}</row>`;
      }).join("");
      const worksheet = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:${spreadsheetColumn(table.columns.length - 1)}${rows.length}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>${widths.map((width, index) => `<col min="${index + 1}" max="${index + 1}" width="${width}" customWidth="1"/>`).join("")}</cols><sheetData>${rowXml}</sheetData><autoFilter ref="A1:${spreadsheetColumn(table.columns.length - 1)}${rows.length}"/></worksheet>`;
      const created = new Date().toISOString();
      return [
        { name: '[Content_Types].xml', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>' },
        { name: '_rels/.rels', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>' },
        { name: 'docProps/core.xml', content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Skyward Observing Plan</dc:title><dc:creator>Skyward</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${created}</dcterms:created></cp:coreProperties>` },
        { name: 'docProps/app.xml', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Skyward</Application></Properties>' },
        { name: 'xl/workbook.xml', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Observing Plan" sheetId="1" r:id="rId1"/></sheets></workbook>' },
        { name: 'xl/_rels/workbook.xml.rels', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>' },
        { name: 'xl/styles.xml', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF000000"/><bgColor rgb="FF000000"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFFF99"/><bgColor rgb="FFFFFF99"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFC6EFCE"/><bgColor rgb="FFC6EFCE"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>' },
        { name: 'xl/worksheets/sheet1.xml', content: worksheet },
      ];
    };
    const utf8 = new TextEncoder();
    const crcTable = Array.from({ length: 256 }, (_, value) => { let crc = value; for (let bit = 0; bit < 8; bit += 1) crc = (crc & 1) ? (0xedb88320 ^ (crc >>> 1)) : (crc >>> 1); return crc >>> 0; });
    const crc32 = (bytes) => { let crc = 0xffffffff; bytes.forEach((byte) => { crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8); }); return (crc ^ 0xffffffff) >>> 0; };
    const zipBytes = (files) => {
      const chunks = [], central = []; let offset = 0;
      const u16 = (value) => [value & 255, (value >>> 8) & 255];
      const u32 = (value) => [value & 255, (value >>> 8) & 255, (value >>> 16) & 255, (value >>> 24) & 255];
      files.forEach(({ name, content }) => {
        const filename = utf8.encode(name), data = content instanceof Uint8Array ? content : utf8.encode(content), crc = crc32(data);
        const local = new Uint8Array([0x50,0x4b,0x03,0x04,...u16(20),...u16(0x0800),...u16(0),...u16(0),...u16(0),...u32(crc),...u32(data.length),...u32(data.length),...u16(filename.length),...u16(0),...filename]);
        chunks.push(local, data);
        central.push(new Uint8Array([0x50,0x4b,0x01,0x02,...u16(20),...u16(20),...u16(0x0800),...u16(0),...u16(0),...u16(0),...u32(crc),...u32(data.length),...u32(data.length),...u16(filename.length),...u16(0),...u16(0),...u16(0),...u16(0),...u32(0),...u32(offset),...filename]));
        offset += local.length + data.length;
      });
      const centralSize = central.reduce((sum, chunk) => sum + chunk.length, 0);
      const end = new Uint8Array([0x50,0x4b,0x05,0x06,...u16(0),...u16(0),...u16(files.length),...u16(files.length),...u32(centralSize),...u32(offset),...u16(0)]);
      const length = [...chunks, ...central, end].reduce((sum, chunk) => sum + chunk.length, 0);
      const output = new Uint8Array(length); let position = 0;
      [...chunks, ...central, end].forEach((chunk) => { output.set(chunk, position); position += chunk.length; });
      return output;
    };
    const downloadPlan = () => {
      if (!planEntries.length) { window.alert(translate('noSavedPlan')); return; }
      const pending = planEntries.filter((entry) => entry.windows.some((window) => window.alternativeStatus === "pending"));
      if (pending.length) {
        pending.forEach((entry) => { void requestAlternatives(entry); });
        window.alert(planCopy("备选源仍在计算，请稍后再次下载，以免 XLSX 缺少备选源。", "Alternatives are still being calculated. Download again shortly so the XLSX includes them."));
        return;
      }
      const workbook = zipBytes(buildXlsxFiles());
      const files = [{ name: 'skyward-observing-plan.xlsx', content: workbook }];
      planEntries.forEach((entry, index) => {
        const stem = String(index + 1).padStart(3, "0") + "-" + safeName(entry.source);
        if (entry.plotSvg) files.push({ name: "plots/" + stem + "-observing-window.svg", content: entry.plotSvg });
        if (entry.localFovSvg) files.push({ name: "plots/" + stem + "-local-fov.svg", content: entry.localFovSvg });
      });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(new Blob([zipBytes(files)], { type: 'application/zip' })); link.download = 'skyward-observing-plan.zip'; link.click();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    };
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-plan-window]");
      if (button) {
        activeWindows = selectedResultWindows();
        if (!activeWindows.length) {
          if (selectionStatus) { selectionStatus.textContent = translate("noPlanWindowsSelected"); selectionStatus.hidden = false; }
          return;
        }
        if (selectionStatus) { selectionStatus.textContent = ""; selectionStatus.hidden = true; }
        sourceElement.textContent = pagePlanContext.dataset.planSourceName || ""; constraintsElement.textContent = constraintText(); renderWindowEditor();
        if (notesInput) notesInput.value = ""; if (savePlot) savePlot.checked = false; delete form.dataset.editEntryId; showError(); dialog.showModal();
      }
      if (event.target.closest("[data-preview-observation-plan]")) { renderPreview(); previewDialog?.showModal(); }
      const editButton = event.target.closest("[data-plan-edit]");
      if (editButton) editPlanEntry(planEntries.find((entry) => entry.id === editButton.dataset.planEdit));
      const deleteButton = event.target.closest("[data-plan-delete]");
      if (deleteButton) { planEntries = planEntries.filter((entry) => entry.id !== deleteButton.dataset.planDelete); savePlanEntries(); renderPreview(); }
      if (event.target.closest("[data-clear-observation-plan]")) clearCurrentPlan();
      if (event.target.closest("[data-download-observation-plan]")) downloadPlan();
      if (event.target.closest("[data-close-plan-dialog]")) dialog.close();
      if (event.target.closest("[data-close-plan-preview]")) previewDialog?.close();
    });
    document.addEventListener("change", (event) => {
      if (event.target.matches("[data-plan-window-select]") && selectionStatus) { selectionStatus.textContent = ""; selectionStatus.hidden = true; }
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const editedWindows = readEditedWindows();
      if (!withinActiveWindows(editedWindows)) { showError(translate("planRangeError")); return; }
      showError();
      const editingId = form.dataset.editEntryId || "";
      if (editingId) {
        const existing = planEntries.find((item) => item.id === editingId);
        if (existing) {
          existing.windows = editedWindows;
          existing.notes = notesInput?.value.trim() || "";
          if (!savePlot?.checked) {
            existing.plotSvg = null;
            existing.localFovSvg = null;
          } else {
            if (!existing.plotSvg) existing.plotSvg = document.querySelector(".scientific-plot svg")?.outerHTML || null;
            if (!existing.localFovSvg) existing.localFovSvg = exportLocalFovSvg();
          }
          savePlanEntries();
          delete form.dataset.editEntryId;
          renderPreview();
          dialog.close();
          return;
        }
        delete form.dataset.editEntryId;
      }
      const entry = buildEntry(editedWindows); const matches = planEntries.map((item, index) => (item.sourceKey || item.source) === (entry.sourceKey || entry.source) ? index : -1).filter((index) => index >= 0);
      if (matches.length) {
        const choice = await chooseDuplicateAction();
        if (choice === "cancel") return;
        if (choice === "overwrite") planEntries[matches[matches.length - 1]] = entry;
        else if (choice === "append") planEntries.push(entry);
      } else planEntries.push(entry);
      savePlanEntries();
      void requestAlternatives(entry);
      form.querySelector("#plan-confirm").textContent = translate("planAdded"); window.setTimeout(() => { form.querySelector("#plan-confirm").textContent = translate("confirmAddPlan"); }, 1300); dialog.close();
    });
    document.addEventListener("skyward:timezone-will-change", () => { if (activeWindows.length && dialog.open) activeWindows = readEditedWindows(); });
    document.addEventListener("skyward:timezone-change", () => { if (activeWindows.length) { renderWindowEditor(); showError(); } });
    document.addEventListener("skyward:language-change", () => { if (activeWindows.length) { if (dialog.open) activeWindows = readEditedWindows(); constraintsElement.textContent = constraintText(); renderWindowEditor(); } if (previewDialog?.open) renderPreview(); });
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    previewDialog?.addEventListener("click", (event) => { if (event.target === previewDialog) previewDialog.close(); });
    previewDialog?.addEventListener("cancel", (event) => { event.preventDefault(); previewDialog.close(); });
    planEntries.filter((entry) => entry.windows.some((window) => window.alternativeStatus === "pending")).forEach((entry) => { void requestAlternatives(entry); });
  };

    const importBatchPlan = () => {
      const node = document.getElementById('batch-plan-import');
      if (!node) return;
      let entries;
      try { entries = JSON.parse(node.dataset.batchPlanEntries || '[]'); } catch (_) { return; }
      if (!entries.length) return;
      try {
        const key = 'skyward.observation-plan.v3';
        const stored = JSON.parse(sessionStorage.getItem(key) || '{"version":3,"entries":[]}');
        const current = Array.isArray(stored.entries) ? stored.entries : [];
        const known = new Set(current.map((entry) => entry.sourceKey || entry.source));
        const fresh = entries.filter((entry) => !known.has(entry.sourceKey || entry.source));
        if (fresh.length) sessionStorage.setItem(key, JSON.stringify({ version: 3, entries: current.concat(fresh) }));
        node.insertAdjacentHTML('afterend', '<p class="map-note">' + translate('batchCalculationReady') + ': ' + fresh.length + '</p>');
      } catch (_) {}
    };
  importBatchPlan();

  const RESULT_PAGE_CACHE_KEY = 'skyward.result-page-cache.v1';

  const snapshotResultPage = () => {
    if (!document.getElementById('detail-query-context')) return false;
    try {
      const clone = document.documentElement.cloneNode(true);
      clone.dataset.skywardResultRestored = 'true';
      const liveControls = [...document.querySelectorAll('input, textarea, select')];
      const clonedControls = [...clone.querySelectorAll('input, textarea, select')];
      liveControls.forEach((control, index) => {
        const copy = clonedControls[index];
        if (!copy) return;
        if (control instanceof HTMLSelectElement) {
          [...copy.options].forEach((option, optionIndex) => option.toggleAttribute('selected', Boolean(control.options[optionIndex]?.selected)));
        } else if (control instanceof HTMLTextAreaElement) {
          copy.textContent = control.value;
        } else if (control instanceof HTMLInputElement) {
          if (control.type === 'checkbox' || control.type === 'radio') copy.toggleAttribute('checked', control.checked);
          else copy.setAttribute('value', control.value);
        }
      });
      clone.querySelectorAll('dialog[open]').forEach(dialog => dialog.removeAttribute('open'));
      // Runtime listeners and injected zoom inputs are recreated by the
      // restored document. Keep the SVG viewBox plus camera datasets, but do
      // not leave the installed marker that would suppress re-initialisation.
      clone.querySelectorAll('[data-map-zoom-controls]').forEach(controls => controls.querySelectorAll('.zoom-factor').forEach(input => input.remove()));
      clone.querySelectorAll('[data-camera-installed]').forEach(frame => frame.removeAttribute('data-camera-installed'));
      const localFrame = document.querySelector('[data-local-fov-map]');
      const localGaiaState = localFrame ? gaiaRequests.get(localFrame) : null;
      const gaiaSources = [...new Map([...gaiaDetails.values()].map(source => [String(source.source_key || source.source_id || source.index), source])).values()];
      sessionStorage.setItem(RESULT_PAGE_CACHE_KEY, JSON.stringify({
        version: 1,
        url: window.location.href,
        savedAt: Date.now(),
        html: '<!doctype html>\n' + clone.outerHTML,
        gaiaSources,
        gaiaRequest: localGaiaState ? { generation: localGaiaState.generation || 0, state: localGaiaState.state, kind: localGaiaState.kind, error: localGaiaState.error || null, meta: localGaiaState.meta || null } : null,
      }));
      return true;
    } catch (error) {
      // A large SVG or a restricted browser storage quota must never block
      // ordinary navigation. The server-rendered /result URL remains a safe
      // recovery path.
      try { sessionStorage.removeItem(RESULT_PAGE_CACHE_KEY); } catch (_) {}
      console.warn('Result-page snapshot unavailable', error);
      return false;
    }
  };

  const restoreCachedResultPage = (returnUrl) => {
    let record;
    try { record = JSON.parse(sessionStorage.getItem(RESULT_PAGE_CACHE_KEY) || 'null'); } catch (_) { record = null; }
    if (!record || record.version !== 1 || typeof record.html !== 'string' || !record.html) return false;
    let parsed;
    try { parsed = new URL(record.url || returnUrl, window.location.origin); } catch (_) { return false; }
    if (parsed.origin !== window.location.origin || parsed.pathname !== '/result') return false;
    try {
      history.pushState(null, '', parsed.href);
      document.open();
      document.write(record.html);
      document.close();
      return true;
    } catch (error) {
      console.warn('Result-page snapshot restore failed', error);
      return false;
    }
  };

  const restoreCachedDynamicState = () => {
    if (document.documentElement.dataset.skywardResultRestored !== 'true') return;
    let record;
    try { record = JSON.parse(sessionStorage.getItem(RESULT_PAGE_CACHE_KEY) || 'null'); } catch (_) { record = null; }
    (record?.gaiaSources || []).forEach(source => {
      gaiaDetails.set(String(source.source_key || source.source_id || source.index), source);
      gaiaDetails.set(String(source.source_id || source.index), source);
    });
    const localFrame = document.querySelector('[data-local-fov-map]');
    if (localFrame && record?.gaiaRequest) gaiaRequests.set(localFrame, { ...record.gaiaRequest });
  };

  const initialiseNavigationContext = () => {
    const key = 'skyward.result-return-context';
    const resultPage = Boolean(document.getElementById('detail-query-context'));
    if (!resultPage && document.getElementById('planner-form')) {
      // The user explicitly returned to the home planner. Subsequent Data/API
      // navigation must return here rather than resurrecting an older result.
      sessionStorage.removeItem(key);
      sessionStorage.removeItem(RESULT_PAGE_CACHE_KEY);
      return;
    }
    if (resultPage) {
      sessionStorage.setItem(key, window.location.href);
      // Capture live select/input values, Gaia layers, map mode, zoom and
      // comparison curves before any ordinary navigation leaves the page.
      const saveBeforeNavigation = () => { snapshotResultPage(); };
      document.addEventListener('click', event => {
        const link = event.target.closest('a[href]');
        if (!link || link.target === '_blank' || link.hasAttribute('download')) return;
        let href;
        try { href = new URL(link.href, window.location.origin); } catch (_) { return; }
        if (href.origin === window.location.origin && ['/','/about','/api/v1'].includes(href.pathname)) saveBeforeNavigation();
      }, true);
      window.addEventListener('pagehide', saveBeforeNavigation);
      return;
    }
    const plannerLinks = [...document.querySelectorAll('a[data-i18n=\"navPlanner\"], a[data-about-i18n=\"openPlanner\"]')];
    if (!plannerLinks.length) return;
    plannerLinks.forEach(plannerLink => plannerLink.addEventListener('click', event => {
      const returnUrl = sessionStorage.getItem(key);
      if (!returnUrl) return;
      let parsed;
      try { parsed = new URL(returnUrl, window.location.origin); } catch (_) { sessionStorage.removeItem(key); return; }
      if (parsed.origin !== window.location.origin || parsed.pathname !== '/result') { sessionStorage.removeItem(key); return; }
      event.preventDefault();
      if (!restoreCachedResultPage(parsed.href)) window.location.assign(parsed.href);
    }));
  };

  const initialiseCalculationSubmission = () => {
    const modal = document.getElementById('calculation-dialog'); if (!modal) return;
    let busy = false, controller = null, submittingForm = null;
    const restore = () => { busy=false; controller?.abort(); controller=null; submittingForm?.removeAttribute('aria-busy'); submittingForm?.querySelectorAll('[data-calculation-disabled]').forEach(button=>{button.disabled=false;delete button.dataset.calculationDisabled;}); if(modal.open)modal.close(); };
    modal.addEventListener('cancel',event=>{event.preventDefault();if(!busy)restore();});
    document.getElementById('calculation-cancel')?.addEventListener('click',()=>{if(!busy)restore();});
    window.addEventListener('pageshow',restore);
    document.querySelectorAll('#planner-form, #replace-source-form').forEach(form=>form.addEventListener('submit',async event=>{
      event.preventDefault(); if(busy || !form.reportValidity())return;
      busy=true; submittingForm=form; controller=new AbortController(); const requestController=controller;
      syncSubmissionPreferences();
      const body=new FormData(form); // Capture before disabling submit controls.
      form.setAttribute('aria-busy','true');
      form.querySelectorAll('[type="submit"]:not(:disabled)').forEach(button=>{button.dataset.calculationDisabled='true';button.disabled=true;});
      document.getElementById('calculation-error').hidden=true; document.getElementById('calculation-cancel').hidden=true; modal.showModal();
      // Two animation frames give the modal a paint opportunity before work begins.
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      if(requestController.signal.aborted)return;
      try {
        const response=await fetch(form.action,{method:'POST',body,signal:requestController.signal,headers:{Accept:'text/html'}});
        const html=await response.text(); if(requestController.signal.aborted)return;
        if(!response.ok && !response.headers.get('content-type')?.includes('text/html'))throw new Error('HTTP '+response.status);
        // Server validation pages are rendered normally and carry their own errors.
        // Keep the calculated result reconstructible after navigating away. The
        // POST response itself is not a browser-history resource, so encode the
        // form state in a GET /result URL before replacing the document.
        const resultQuery = new URLSearchParams();
        body.forEach((value, key) => {
          if (typeof value !== 'string') return;
          if (value.trim() === '') return;
          resultQuery.append(key, value);
        });
        const resultUrl = form.action + '?' + resultQuery.toString();
        history.pushState(null, '', resultUrl);
        document.open();document.write(html);document.close();
      } catch(error){
        if(error.name==='AbortError')return;
        restore(); const message=document.getElementById('calculation-error');message.textContent=translate('calculationFailed')+': '+error.message;message.hidden=false;document.getElementById('calculation-cancel').hidden=false;modal.showModal();
      }
    }));
    window.addEventListener('popstate',()=>{restore();window.location.reload();});
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
  restoreCachedDynamicState();
  initialiseNavigationContext();
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
  initialiseCalculationSubmission();
  refreshTimeDisplays();
})();
