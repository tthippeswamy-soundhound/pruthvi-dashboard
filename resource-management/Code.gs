// ============================================================
// Resource Management Tool - Google Apps Script
// ============================================================
// Setup: Extensions > Apps Script > Paste this > Save > Reload Sheet
// Then: Resource Manager menu > Initialize Sheet
// ============================================================

// --------------- MENU & TRIGGERS ---------------

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Resource Manager')
    .addItem('Initialize Sheet', 'initializeSheet')
    .addSeparator()
    .addItem('Refresh Dashboard', 'refreshDashboard')
    .addItem('Refresh Project Dropdowns', 'updateProjectDropdowns')
    .addToUi();
}

function onEdit(e) {
  var sheet = e.source.getActiveSheet();
  var sheetName = sheet.getName();

  // When a project is added/edited in the Projects tab, update dropdowns
  if (sheetName === 'Projects' && e.range.getColumn() === 1 && e.range.getRow() > 1) {
    updateProjectDropdowns();
  }

  // When resources tab is edited, refresh dashboard
  if (sheetName === 'Resources' && e.range.getRow() > 1) {
    refreshDashboard();
  }
}

// --------------- INITIALIZATION ---------------

function initializeSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // Create or get sheets
  var projectsSheet = getOrCreateSheet(ss, 'Projects');
  var resourcesSheet = getOrCreateSheet(ss, 'Resources');
  var dashboardSheet = getOrCreateSheet(ss, 'Dashboard');

  // Remove default Sheet1 if it exists and is empty
  var defaultSheet = ss.getSheetByName('Sheet1');
  if (defaultSheet && ss.getSheets().length > 1) {
    try { ss.deleteSheet(defaultSheet); } catch (e) { /* ignore */ }
  }

  // Set up each tab
  setupProjectsTab(projectsSheet);
  setupResourcesTab(resourcesSheet);
  setupDashboardTab(dashboardSheet);

  // Set tab colors
  projectsSheet.setTabColor('#4285F4');  // Blue
  resourcesSheet.setTabColor('#34A853'); // Green
  dashboardSheet.setTabColor('#EA4335'); // Red

  // Activate Projects tab
  ss.setActiveSheet(projectsSheet);

  SpreadsheetApp.getUi().alert(
    'Resource Management Tool initialized!\n\n' +
    '1. Add projects in the "Projects" tab\n' +
    '2. Assign resources in the "Resources" tab\n' +
    '3. View charts in the "Dashboard" tab\n\n' +
    'Project dropdowns update automatically!'
  );
}

function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}

// --------------- PROJECTS TAB ---------------

function setupProjectsTab(sheet) {
  sheet.clear();

  // Headers
  var headers = [['Project Name', 'Start Date', 'End Date', 'Status', 'Budget ($)', 'Description']];
  sheet.getRange(1, 1, 1, 6).setValues(headers);

  // Header formatting
  var headerRange = sheet.getRange(1, 1, 1, 6);
  headerRange.setBackground('#4285F4')
    .setFontColor('#FFFFFF')
    .setFontWeight('bold')
    .setFontSize(11)
    .setHorizontalAlignment('center')
    .setBorder(true, true, true, true, true, true, '#FFFFFF', SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  // Column widths
  sheet.setColumnWidth(1, 200); // Project Name
  sheet.setColumnWidth(2, 130); // Start Date
  sheet.setColumnWidth(3, 130); // End Date
  sheet.setColumnWidth(4, 120); // Status
  sheet.setColumnWidth(5, 120); // Budget
  sheet.setColumnWidth(6, 300); // Description

  // Sample data
  var sampleData = [
    ['Website Redesign', '2026-04-01', '2026-06-30', 'Active', 50000, 'Complete website overhaul'],
    ['Mobile App v2', '2026-04-15', '2026-09-15', 'Planning', 120000, 'Next version of mobile app'],
    ['Data Migration', '2026-03-01', '2026-04-30', 'Active', 30000, 'Legacy system data migration'],
    ['API Integration', '2026-05-01', '2026-07-31', 'Planning', 45000, 'Third-party API integrations'],
    ['Security Audit', '2026-03-15', '2026-04-15', 'Active', 20000, 'Annual security review']
  ];
  sheet.getRange(2, 1, sampleData.length, 6).setValues(sampleData);

  // Date format
  sheet.getRange(2, 2, 100, 2).setNumberFormat('yyyy-mm-dd');

  // Budget format
  sheet.getRange(2, 5, 100, 1).setNumberFormat('#,##0');

  // Status dropdown validation
  var statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['Planning', 'Active', 'On Hold', 'Completed', 'Cancelled'])
    .setAllowInvalid(false)
    .build();
  sheet.getRange(2, 4, 200, 1).setDataValidation(statusRule);

  // Alternate row colors for data area
  for (var i = 2; i <= 50; i++) {
    var bgColor = (i % 2 === 0) ? '#F8F9FA' : '#FFFFFF';
    sheet.getRange(i, 1, 1, 6).setBackground(bgColor);
  }

  // Freeze header row
  sheet.setFrozenRows(1);

  // Add a note on the Project Name header
  sheet.getRange(1, 1).setNote('Add project names here. They will automatically appear as dropdown options in the Resources tab.');
}

// --------------- RESOURCES TAB ---------------

function setupResourcesTab(sheet) {
  sheet.clear();

  // Headers
  var headers = [['Resource Name', 'Role', 'Email', 'Assigned Project', 'Allocation %', 'Start Date', 'End Date', 'Hourly Rate ($)', 'Status']];
  sheet.getRange(1, 1, 1, 9).setValues(headers);

  // Header formatting
  var headerRange = sheet.getRange(1, 1, 1, 9);
  headerRange.setBackground('#34A853')
    .setFontColor('#FFFFFF')
    .setFontWeight('bold')
    .setFontSize(11)
    .setHorizontalAlignment('center')
    .setBorder(true, true, true, true, true, true, '#FFFFFF', SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  // Column widths
  sheet.setColumnWidth(1, 180); // Resource Name
  sheet.setColumnWidth(2, 150); // Role
  sheet.setColumnWidth(3, 200); // Email
  sheet.setColumnWidth(4, 180); // Assigned Project
  sheet.setColumnWidth(5, 110); // Allocation %
  sheet.setColumnWidth(6, 130); // Start Date
  sheet.setColumnWidth(7, 130); // End Date
  sheet.setColumnWidth(8, 120); // Hourly Rate
  sheet.setColumnWidth(9, 120); // Status

  // Sample data
  var sampleData = [
    ['Alice Johnson', 'Frontend Developer', 'alice@company.com', 'Website Redesign', 80, '2026-04-01', '2026-06-30', 95, 'Active'],
    ['Bob Smith', 'Backend Developer', 'bob@company.com', 'Mobile App v2', 100, '2026-04-15', '2026-09-15', 110, 'Active'],
    ['Carol Williams', 'Data Engineer', 'carol@company.com', 'Data Migration', 60, '2026-03-01', '2026-04-30', 105, 'Active'],
    ['David Brown', 'Full Stack Developer', 'david@company.com', 'Website Redesign', 50, '2026-04-01', '2026-06-30', 100, 'Active'],
    ['Eve Davis', 'Security Analyst', 'eve@company.com', 'Security Audit', 100, '2026-03-15', '2026-04-15', 120, 'Active'],
    ['Frank Miller', 'DevOps Engineer', 'frank@company.com', 'API Integration', 40, '2026-05-01', '2026-07-31', 115, 'Bench'],
    ['Grace Lee', 'UI/UX Designer', 'grace@company.com', 'Website Redesign', 70, '2026-04-01', '2026-06-30', 90, 'Active'],
    ['Henry Wilson', 'QA Engineer', 'henry@company.com', 'Mobile App v2', 50, '2026-04-15', '2026-09-15', 85, 'Active'],
    ['Ivy Chen', 'Project Manager', 'ivy@company.com', 'Data Migration', 30, '2026-03-01', '2026-04-30', 100, 'Active'],
    ['Jack Taylor', 'Backend Developer', 'jack@company.com', 'API Integration', 60, '2026-05-01', '2026-07-31', 105, 'Bench']
  ];
  sheet.getRange(2, 1, sampleData.length, 9).setValues(sampleData);

  // Set up project dropdown (from Projects tab)
  updateProjectDropdowns();

  // Allocation % validation (0-100)
  var allocRule = SpreadsheetApp.newDataValidation()
    .requireNumberBetween(0, 100)
    .setAllowInvalid(false)
    .setHelpText('Enter a value between 0 and 100')
    .build();
  sheet.getRange(2, 5, 200, 1).setDataValidation(allocRule);

  // Resource status dropdown
  var statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['Active', 'Bench', 'On Leave', 'Offboarded'])
    .setAllowInvalid(false)
    .build();
  sheet.getRange(2, 9, 200, 1).setDataValidation(statusRule);

  // Date format
  sheet.getRange(2, 6, 200, 2).setNumberFormat('yyyy-mm-dd');

  // Rate format
  sheet.getRange(2, 8, 200, 1).setNumberFormat('#,##0');

  // Allocation % format
  sheet.getRange(2, 5, 200, 1).setNumberFormat('0"%"');

  // Alternate row colors
  for (var i = 2; i <= 50; i++) {
    var bgColor = (i % 2 === 0) ? '#F0F7F0' : '#FFFFFF';
    sheet.getRange(i, 1, 1, 9).setBackground(bgColor);
  }

  // Conditional formatting for allocation
  var highAllocRule = SpreadsheetApp.newConditionalFormatRule()
    .whenNumberGreaterThanOrEqualTo(90)
    .setBackground('#FDDEDE')
    .setFontColor('#CC0000')
    .setRanges([sheet.getRange(2, 5, 200, 1)])
    .build();

  var midAllocRule = SpreadsheetApp.newConditionalFormatRule()
    .whenNumberBetween(50, 89)
    .setBackground('#FFF3CD')
    .setFontColor('#856404')
    .setRanges([sheet.getRange(2, 5, 200, 1)])
    .build();

  var lowAllocRule = SpreadsheetApp.newConditionalFormatRule()
    .whenNumberLessThan(50)
    .setBackground('#D4EDDA')
    .setFontColor('#155724')
    .setRanges([sheet.getRange(2, 5, 200, 1)])
    .build();

  sheet.setConditionalFormatRules([highAllocRule, midAllocRule, lowAllocRule]);

  // Freeze header row
  sheet.setFrozenRows(1);

  // Add note
  sheet.getRange(1, 4).setNote('This dropdown is auto-populated from the Projects tab. Add new projects there and they will appear here automatically.');
}

// --------------- DROPDOWN SYNC ---------------

function updateProjectDropdowns() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var projectsSheet = ss.getSheetByName('Projects');
  var resourcesSheet = ss.getSheetByName('Resources');

  if (!projectsSheet || !resourcesSheet) return;

  // Get project names from column A (skip header)
  var lastRow = projectsSheet.getLastRow();
  if (lastRow < 2) {
    // No projects yet - clear validation
    resourcesSheet.getRange(2, 4, 200, 1).clearDataValidations();
    return;
  }

  var projectNames = projectsSheet.getRange(2, 1, lastRow - 1, 1).getValues()
    .flat()
    .filter(function(name) { return name !== ''; });

  if (projectNames.length === 0) {
    resourcesSheet.getRange(2, 4, 200, 1).clearDataValidations();
    return;
  }

  // Create data validation rule with project names
  var rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(projectNames)
    .setAllowInvalid(false)
    .setHelpText('Select a project from the Projects tab')
    .build();

  // Apply to the Assigned Project column (column 4) in Resources tab
  resourcesSheet.getRange(2, 4, 200, 1).setDataValidation(rule);
}

// --------------- DASHBOARD TAB ---------------

function setupDashboardTab(sheet) {
  sheet.clear();

  // Title
  sheet.getRange(1, 1).setValue('Resource Management Dashboard')
    .setFontSize(18)
    .setFontWeight('bold')
    .setFontColor('#333333');
  sheet.getRange(1, 1, 1, 8).merge().setBackground('#F1F3F4');

  // Subtitle with timestamp
  sheet.getRange(2, 1).setValue('Last updated: ' + new Date().toLocaleString())
    .setFontSize(10)
    .setFontColor('#666666')
    .setFontStyle('italic');
  sheet.getRange(2, 1, 1, 8).merge().setBackground('#F1F3F4');

  // Column width for dashboard
  for (var i = 1; i <= 10; i++) {
    sheet.setColumnWidth(i, 130);
  }

  buildDashboardData(sheet);
  buildCharts(sheet);

  sheet.setFrozenRows(2);
}

function refreshDashboard() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var dashboardSheet = ss.getSheetByName('Dashboard');
  if (!dashboardSheet) return;

  // Clear old content below row 2 but preserve title
  var lastRow = dashboardSheet.getMaxRows();
  if (lastRow > 2) {
    dashboardSheet.getRange(3, 1, lastRow - 2, dashboardSheet.getMaxColumns()).clear();
  }

  // Remove old charts
  var charts = dashboardSheet.getCharts();
  for (var i = 0; i < charts.length; i++) {
    dashboardSheet.removeChart(charts[i]);
  }

  // Update timestamp
  dashboardSheet.getRange(2, 1).setValue('Last updated: ' + new Date().toLocaleString());

  buildDashboardData(dashboardSheet);
  buildCharts(dashboardSheet);
}

function buildDashboardData(sheet) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var projectsSheet = ss.getSheetByName('Projects');
  var resourcesSheet = ss.getSheetByName('Resources');

  if (!projectsSheet || !resourcesSheet) return;

  // Gather data
  var projectData = getSheetData(projectsSheet);
  var resourceData = getSheetData(resourcesSheet);

  // ----- KPI SUMMARY (Row 4) -----
  sheet.getRange(4, 1).setValue('KEY METRICS')
    .setFontSize(13)
    .setFontWeight('bold')
    .setFontColor('#4285F4');
  sheet.getRange(4, 1, 1, 8).merge();

  // KPI Cards
  var totalProjects = projectData.length;
  var activeProjects = projectData.filter(function(p) { return p[3] === 'Active'; }).length;
  var totalResources = resourceData.length;
  var activeResources = resourceData.filter(function(r) { return r[8] === 'Active'; }).length;
  var avgAllocation = 0;
  if (resourceData.length > 0) {
    var totalAlloc = resourceData.reduce(function(sum, r) { return sum + (Number(r[4]) || 0); }, 0);
    avgAllocation = Math.round(totalAlloc / resourceData.length);
  }
  var totalBudget = projectData.reduce(function(sum, p) { return sum + (Number(p[4]) || 0); }, 0);

  // KPI Headers
  var kpiHeaders = [['Total Projects', 'Active Projects', 'Total Resources', 'Active Resources', 'Avg Allocation', 'Total Budget']];
  sheet.getRange(5, 1, 1, 6).setValues(kpiHeaders)
    .setFontWeight('bold')
    .setFontSize(10)
    .setFontColor('#555555')
    .setHorizontalAlignment('center')
    .setBackground('#E8F0FE');

  // KPI Values
  var kpiValues = [[totalProjects, activeProjects, totalResources, activeResources, avgAllocation + '%', '$' + totalBudget.toLocaleString()]];
  sheet.getRange(6, 1, 1, 6).setValues(kpiValues)
    .setFontWeight('bold')
    .setFontSize(16)
    .setHorizontalAlignment('center')
    .setBackground('#FFFFFF');

  // Add borders to KPI cards
  sheet.getRange(5, 1, 2, 6).setBorder(true, true, true, true, true, true, '#DADCE0', SpreadsheetApp.BorderStyle.SOLID);

  // ----- ALLOCATION BY PROJECT (Row 9) -----
  sheet.getRange(9, 1).setValue('ALLOCATION BY PROJECT')
    .setFontSize(12)
    .setFontWeight('bold')
    .setFontColor('#34A853');
  sheet.getRange(9, 1, 1, 3).merge();

  // Headers
  sheet.getRange(10, 1, 1, 3).setValues([['Project', 'Resources Assigned', 'Avg Allocation %']])
    .setFontWeight('bold')
    .setBackground('#E6F4EA')
    .setHorizontalAlignment('center');

  // Calculate per-project stats
  var projectStats = {};
  projectData.forEach(function(p) {
    var name = p[0];
    if (name) {
      projectStats[name] = { count: 0, totalAlloc: 0 };
    }
  });

  resourceData.forEach(function(r) {
    var project = r[3];
    var alloc = Number(r[4]) || 0;
    if (projectStats[project]) {
      projectStats[project].count++;
      projectStats[project].totalAlloc += alloc;
    }
  });

  var projectStatsArray = [];
  Object.keys(projectStats).forEach(function(name) {
    var stats = projectStats[name];
    var avgAlloc = stats.count > 0 ? Math.round(stats.totalAlloc / stats.count) : 0;
    projectStatsArray.push([name, stats.count, avgAlloc]);
  });

  if (projectStatsArray.length > 0) {
    sheet.getRange(11, 1, projectStatsArray.length, 3).setValues(projectStatsArray);
    sheet.getRange(11, 2, projectStatsArray.length, 2).setHorizontalAlignment('center');

    // Alternate row colors
    for (var i = 0; i < projectStatsArray.length; i++) {
      var bgColor = (i % 2 === 0) ? '#FFFFFF' : '#F0F7F0';
      sheet.getRange(11 + i, 1, 1, 3).setBackground(bgColor);
    }
  }

  // ----- RESOURCE UTILIZATION (Row 9, Column 5) -----
  var utilStartRow = 9;
  sheet.getRange(utilStartRow, 5).setValue('RESOURCE UTILIZATION')
    .setFontSize(12)
    .setFontWeight('bold')
    .setFontColor('#EA4335');
  sheet.getRange(utilStartRow, 5, 1, 3).merge();

  sheet.getRange(utilStartRow + 1, 5, 1, 3).setValues([['Resource', 'Project', 'Allocation %']])
    .setFontWeight('bold')
    .setBackground('#FDDEDE')
    .setHorizontalAlignment('center');

  var utilData = resourceData.map(function(r) {
    return [r[0], r[3], Number(r[4]) || 0];
  }).sort(function(a, b) { return b[2] - a[2]; }); // Sort by allocation desc

  if (utilData.length > 0) {
    sheet.getRange(utilStartRow + 2, 5, utilData.length, 3).setValues(utilData);
    sheet.getRange(utilStartRow + 2, 7, utilData.length, 1).setHorizontalAlignment('center');
  }

  // ----- PROJECT STATUS SUMMARY (below allocation table) -----
  var statusStartRow = 11 + Math.max(projectStatsArray.length, 0) + 2;
  sheet.getRange(statusStartRow, 1).setValue('PROJECT STATUS BREAKDOWN')
    .setFontSize(12)
    .setFontWeight('bold')
    .setFontColor('#FBBC04');
  sheet.getRange(statusStartRow, 1, 1, 3).merge();

  sheet.getRange(statusStartRow + 1, 1, 1, 2).setValues([['Status', 'Count']])
    .setFontWeight('bold')
    .setBackground('#FEF7E0')
    .setHorizontalAlignment('center');

  var statusCounts = {};
  projectData.forEach(function(p) {
    var status = p[3] || 'Unknown';
    statusCounts[status] = (statusCounts[status] || 0) + 1;
  });

  var statusArray = [];
  Object.keys(statusCounts).forEach(function(status) {
    statusArray.push([status, statusCounts[status]]);
  });

  if (statusArray.length > 0) {
    sheet.getRange(statusStartRow + 2, 1, statusArray.length, 2).setValues(statusArray);
    sheet.getRange(statusStartRow + 2, 2, statusArray.length, 1).setHorizontalAlignment('center');
  }

  // ----- RESOURCE STATUS SUMMARY -----
  sheet.getRange(statusStartRow, 5).setValue('RESOURCE STATUS BREAKDOWN')
    .setFontSize(12)
    .setFontWeight('bold')
    .setFontColor('#9334E6');
  sheet.getRange(statusStartRow, 5, 1, 3).merge();

  sheet.getRange(statusStartRow + 1, 5, 1, 2).setValues([['Status', 'Count']])
    .setFontWeight('bold')
    .setBackground('#F3E8FD')
    .setHorizontalAlignment('center');

  var resStatusCounts = {};
  resourceData.forEach(function(r) {
    var status = r[8] || 'Unknown';
    resStatusCounts[status] = (resStatusCounts[status] || 0) + 1;
  });

  var resStatusArray = [];
  Object.keys(resStatusCounts).forEach(function(status) {
    resStatusArray.push([status, resStatusCounts[status]]);
  });

  if (resStatusArray.length > 0) {
    sheet.getRange(statusStartRow + 2, 5, resStatusArray.length, 2).setValues(resStatusArray);
    sheet.getRange(statusStartRow + 2, 6, resStatusArray.length, 1).setHorizontalAlignment('center');
  }
}

function buildCharts(sheet) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var projectsSheet = ss.getSheetByName('Projects');
  var resourcesSheet = ss.getSheetByName('Resources');

  if (!projectsSheet || !resourcesSheet) return;

  var projectData = getSheetData(projectsSheet);
  var resourceData = getSheetData(resourcesSheet);

  // Calculate chart data positions
  var projectStatsLength = projectData.length;
  var chartRow = 11 + projectStatsLength + 2 + 6; // Below status tables

  // ---- CHART 1: Allocation by Project (Pie Chart) ----
  // Data is in rows 10-10+N, columns 1-3 (project name + resources + avg alloc)
  if (projectStatsLength > 0) {
    var pieDataRange = sheet.getRange(10, 1, projectStatsLength + 1, 2); // Header + data
    var pieChart = sheet.newChart()
      .setChartType(Charts.ChartType.PIE)
      .addRange(pieDataRange)
      .setPosition(chartRow, 1, 0, 0)
      .setOption('title', 'Resources per Project')
      .setOption('pieHole', 0.4)
      .setOption('width', 520)
      .setOption('height', 340)
      .setOption('legend', { position: 'right' })
      .setOption('colors', ['#4285F4', '#34A853', '#FBBC04', '#EA4335', '#9334E6', '#FF6D01', '#46BDC6', '#7BAAF7'])
      .setOption('backgroundColor', '#FAFAFA')
      .setOption('pieSliceText', 'percentage')
      .build();
    sheet.insertChart(pieChart);
  }

  // ---- CHART 2: Resource Utilization (Bar Chart) ----
  if (resourceData.length > 0) {
    var utilHeaderRow = 10;
    var barDataRange = sheet.getRange(utilHeaderRow, 5, resourceData.length + 1, 1); // Resource names
    var barValueRange = sheet.getRange(utilHeaderRow, 7, resourceData.length + 1, 1); // Allocation %

    var barChart = sheet.newChart()
      .setChartType(Charts.ChartType.BAR)
      .addRange(barDataRange)
      .addRange(barValueRange)
      .setPosition(chartRow, 5, 0, 0)
      .setOption('title', 'Resource Allocation %')
      .setOption('width', 520)
      .setOption('height', 340)
      .setOption('legend', { position: 'none' })
      .setOption('hAxis', { title: 'Allocation %', minValue: 0, maxValue: 100 })
      .setOption('colors', ['#34A853'])
      .setOption('backgroundColor', '#FAFAFA')
      .build();
    sheet.insertChart(barChart);
  }

  // ---- CHART 3: Project Status Distribution (Pie Chart) ----
  var statusStartRow = 11 + projectStatsLength + 2;
  var statusCounts = {};
  projectData.forEach(function(p) {
    var status = p[3] || 'Unknown';
    statusCounts[status] = (statusCounts[status] || 0) + 1;
  });
  var statusCount = Object.keys(statusCounts).length;

  if (statusCount > 0) {
    var statusDataRange = sheet.getRange(statusStartRow + 1, 1, statusCount + 1, 2);
    var statusChart = sheet.newChart()
      .setChartType(Charts.ChartType.PIE)
      .addRange(statusDataRange)
      .setPosition(chartRow + 18, 1, 0, 0)
      .setOption('title', 'Project Status Distribution')
      .setOption('width', 520)
      .setOption('height', 340)
      .setOption('legend', { position: 'right' })
      .setOption('colors', ['#34A853', '#4285F4', '#FBBC04', '#EA4335', '#9E9E9E'])
      .setOption('backgroundColor', '#FAFAFA')
      .build();
    sheet.insertChart(statusChart);
  }

  // ---- CHART 4: Resource Status Distribution (Pie Chart) ----
  var resStatusCounts = {};
  resourceData.forEach(function(r) {
    var status = r[8] || 'Unknown';
    resStatusCounts[status] = (resStatusCounts[status] || 0) + 1;
  });
  var resStatusCount = Object.keys(resStatusCounts).length;

  if (resStatusCount > 0) {
    var resStatusDataRange = sheet.getRange(statusStartRow + 1, 5, resStatusCount + 1, 2);
    var resStatusChart = sheet.newChart()
      .setChartType(Charts.ChartType.PIE)
      .addRange(resStatusDataRange)
      .setPosition(chartRow + 18, 5, 0, 0)
      .setOption('title', 'Resource Status Distribution')
      .setOption('width', 520)
      .setOption('height', 340)
      .setOption('legend', { position: 'right' })
      .setOption('colors', ['#4285F4', '#FBBC04', '#EA4335', '#9E9E9E'])
      .setOption('backgroundColor', '#FAFAFA')
      .build();
    sheet.insertChart(resStatusChart);
  }
}

// --------------- HELPERS ---------------

function getSheetData(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  var lastCol = sheet.getLastColumn();
  return sheet.getRange(2, 1, lastRow - 1, lastCol).getValues()
    .filter(function(row) { return row[0] !== ''; });
}
