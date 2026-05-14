# Resource Management Tool - Google Sheet

A complete resource management tool built with Google Apps Script that runs inside a single Google Sheet with 3 tabs:

1. **Projects** - Manage project names, dates, status, and budgets
2. **Resources** - Assign resources to projects via auto-updating dropdowns
3. **Dashboard** - Visual charts showing allocation and utilization

## Setup Instructions

1. Create a new Google Sheet at [sheets.google.com](https://sheets.google.com)
2. Go to **Extensions > Apps Script**
3. Delete any existing code in `Code.gs`
4. Copy the entire contents of `Code.gs` from this folder and paste it
5. Click **Save** (Ctrl+S)
6. Close the Apps Script editor
7. Reload the Google Sheet
8. You'll see a new menu: **Resource Manager**
9. Click **Resource Manager > Initialize Sheet** to set up all tabs
10. Grant the required permissions when prompted

## Features

- **Auto-updating dropdowns**: When you add a new project in Tab 1, it automatically appears in the project dropdown in Tab 2
- **Dashboard charts**: Pie chart for allocation by project, bar chart for resource utilization, and status summary
- **Color-coded headers** and formatted cells for easy reading
- **Data validation** to keep data clean
- **Auto-refresh**: Dashboard updates automatically when resources are edited, or manually via menu

## Usage

### Adding Projects
- Go to the **Projects** tab
- Fill in: Project Name, Start Date, End Date, Status (dropdown), Budget

### Assigning Resources
- Go to the **Resources** tab
- Fill in: Resource Name, Role, select a Project from the dropdown, Allocation %, Start Date, End Date

### Viewing Dashboard
- Go to the **Dashboard** tab to see:
  - Summary statistics (total projects, resources, avg allocation)
  - Allocation breakdown by project (pie chart)
  - Resource utilization levels (bar chart)
  - Project status distribution (pie chart)
- Click **Resource Manager > Refresh Dashboard** to update charts
