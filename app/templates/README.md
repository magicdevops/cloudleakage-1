# CloudLeakage Template Organization Guide

This document explains the organized template structure and how to use the reusable components effectively.

## Directory Structure

```
templates/
├── layouts/                     # Base layouts and common templates
│   ├── base.html               # Main base layout
│   └── dashboard_layout.html   # Dashboard-specific layout
│
├── components/                  # Reusable template components
│   ├── sidebar.html            # Navigation sidebar with active states
│   ├── metrics_card.html       # Reusable metric display cards
│   ├── data_table.html         # Configurable data tables
│   ├── export_dropdown.html    # Export functionality component
│   ├── loading_spinner.html    # Loading indicators
│   ├── alert.html              # Alert/notification component
│   └── modal.html              # Modal dialog component
│
├── pages/                       # Main page templates
│   └── dashboard.html          # Main dashboard
│
├── aws/                         # AWS service-specific templates
│   ├── ec2/
│   │   ├── dashboard.html      # EC2 dashboard
│   │   └── dashboard_new.html  # Modernized EC2 dashboard (example)
│   ├── snapshots/
│   │   └── dashboard.html      # Snapshots dashboard
│   └── terraform/
│       └── analyzer.html       # Terraform analyzer
│
├── integration/                 # Account integration templates
│   ├── accounts.html
│   └── wizard.html
│
├── business_units/              # Business unit management
│   └── index.html
│
└── errors/                      # Error page templates
    ├── 404.html                # Custom 404 page
    └── 500.html                # Custom 500 page
```

## Layout Templates

### Base Layout (`layouts/base.html`)
The main layout template that provides the basic HTML structure, CSS includes, and common elements.

### Dashboard Layout (`layouts/dashboard_layout.html`)
Extends the base layout and adds dashboard-specific features:
- Automatic sidebar inclusion
- Header with title and actions
- Common JavaScript utilities
- Responsive grid system

**Usage:**
```html
{% extends "layouts/dashboard_layout.html" %}

{% block title %}My Dashboard{% endblock %}
{% block header_title %}My Custom Dashboard{% endblock %}
{% block content %}
    <!-- Your dashboard content here -->
{% endblock %}
```

## Reusable Components

### 1. Metrics Card (`components/metrics_card.html`)

Display key metrics with consistent styling.

**Usage:**
```html
{% from 'components/metrics_card.html' import metrics_card %}

{{ metrics_card("Total Instances", "42", "fas fa-server", "primary") }}
{{ metrics_card("Monthly Cost", "$1,234", "fas fa-dollar-sign", "success", "vs last month", 5.2) }}
```

**Parameters:**
- `title`: Card title
- `value`: Main metric value
- `icon`: FontAwesome icon class
- `color`: Color theme (primary, success, warning, danger, info)
- `subtitle`: Optional subtitle text
- `trend`: Optional trend percentage (positive/negative)

### 2. Data Table (`components/data_table.html`)

Configurable data tables with sorting, actions, and styling.

**Usage:**
```html
{% from 'components/data_table.html' import data_table %}

{% set headers = [
    {'field': 'name', 'label': 'Name'},
    {'field': 'status', 'label': 'Status', 'type': 'badge'},
    {'field': 'cost', 'label': 'Monthly Cost', 'type': 'currency'},
    {'field': 'created_at', 'label': 'Created', 'type': 'date'}
] %}

{% set actions = [
    {'function': 'viewDetails', 'icon': 'fas fa-eye', 'label': 'View', 'class': 'primary'},
    {'function': 'editItem', 'icon': 'fas fa-edit', 'label': 'Edit', 'class': 'secondary'}
] %}

{{ data_table('instancesTable', headers, instances, actions, true, 'openInstanceDetails') }}
```

**Column Types:**
- `badge`: Styled status badges
- `currency`: Formatted currency values
- `date`: Formatted dates
- `icon`: FontAwesome icons

### 3. Export Dropdown (`components/export_dropdown.html`)

Standardized export functionality with CSV, JSON, and Excel options.

**Usage:**
```html
{% from 'components/export_dropdown.html' import export_dropdown %}

{{ export_dropdown("mainExportDropdown", "exportData", "Export Data") }}
```

### 4. Loading Spinner (`components/loading_spinner.html`)

Consistent loading indicators in multiple sizes.

**Usage:**
```html
{% from 'components/loading_spinner.html' import loading_spinner %}

{{ loading_spinner() }}
{{ loading_spinner("large", "Syncing data...") }}
{{ loading_spinner("small", "Loading", true) }}
```

### 5. Alert Component (`components/alert.html`)

Styled alert messages for success, warning, error, and info states.

**Usage:**
```html
{% from 'components/alert.html' import alert %}

{{ alert("success", "Success!", "Data synced successfully.", true) }}
{{ alert("warning", "Warning", "Some instances may be idle.") }}
{{ alert("danger", "Error", "Failed to connect to AWS account.") }}
```

### 6. Modal Component (`components/modal.html`)

Reusable modal dialogs with different sizes.

**Usage:**
```html
{% from 'components/modal.html' import modal %}

{% call modal("instanceModal", "Instance Details", "large") %}
    <div class="instance-details">
        <!-- Modal content goes here -->
    </div>
{% endcall %}
```

### 7. Sidebar Component (`components/sidebar.html`)

Navigation sidebar with automatic active state detection.

**Features:**
- Automatic active state based on `request.endpoint`
- Organized navigation sections
- Responsive design
- FontAwesome icons

## Best Practices

### 1. Template Inheritance
- Always extend from appropriate layout templates
- Use `layouts/dashboard_layout.html` for dashboard pages
- Use `layouts/base.html` for simple pages

### 2. Component Usage
- Import components at the top of templates
- Use consistent naming conventions
- Pass all required parameters

### 3. Styling
- Use CSS custom properties (variables) for consistency
- Follow the established color scheme
- Maintain responsive design principles

### 4. JavaScript
- Place page-specific scripts in `{% block scripts %}`
- Use global utility functions from dashboard layout
- Follow consistent naming conventions

## Migration Guide

To migrate existing templates to the new structure:

1. **Update extends statements:**
   ```html
   <!-- Old -->
   {% extends "base.html" %}
   
   <!-- New -->
   {% extends "layouts/dashboard_layout.html" %}
   ```

2. **Replace custom components with reusable ones:**
   ```html
   <!-- Old -->
   <div class="metric-card">...</div>
   
   <!-- New -->
   {% from 'components/metrics_card.html' import metrics_card %}
   {{ metrics_card("Title", "Value", "icon", "color") }}
   ```

3. **Update Flask routes:**
   ```python
   # Old
   return render_template('ec2/dashboard.html')
   
   # New
   return render_template('aws/ec2/dashboard.html')
   ```

## CSS Variables

The template system uses CSS custom properties for consistent theming:

```css
:root {
    --primary-blue: #007bff;
    --success-green: #28a745;
    --warning-yellow: #ffc107;
    --danger-red: #dc3545;
    --text-primary: #333;
    --text-secondary: #666;
    --bg-primary: #ffffff;
    --bg-secondary: #f8f9fa;
    --border-light: #dee2e6;
    --radius-md: 8px;
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

## Performance Considerations

- Components are rendered server-side for optimal performance
- CSS is scoped to prevent conflicts
- JavaScript utilities are shared across pages
- Images and icons are optimized for web delivery

This organized structure provides a scalable, maintainable foundation for CloudLeakage's user interface.
