"""HTML report generator with charts and visualizations """

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

from datetime import datetime
from pathlib import Path

from jinja2 import Template

from synexian.models import AnalysisReport
from synexian.reports.base import BaseReporter
from synexian.utils.file_utils import ensure_dir


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Synexian Analysis Report - {{ report.project_path }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --primary-color: #2563eb;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --info-color: #3b82f6;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 0;
            margin-bottom: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-align: center;
        }

        header .subtitle {
            text-align: center;
            opacity: 0.9;
            font-size: 1.1em;
        }

        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .dashboard-card {
            background: var(--card-bg);
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 4px solid var(--primary-color);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .dashboard-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.1);
        }

        .dashboard-card h3 {
            color: var(--text-secondary);
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .dashboard-card .value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .dashboard-card.grade { border-left-color: var(--success-color); }
        .dashboard-card.score { border-left-color: var(--info-color); }
        .dashboard-card.files { border-left-color: #8b5cf6; }
        .dashboard-card.issues { border-left-color: var(--danger-color); }

        .grade-A, .grade-A-PLUS { color: var(--success-color); }
        .grade-B, .grade-B-PLUS { color: var(--info-color); }
        .grade-C, .grade-C-PLUS { color: var(--warning-color); }
        .grade-D, .grade-F { color: var(--danger-color); }

        .section {
            background: var(--card-bg);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }

        .section h2 {
            color: var(--text-primary);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--border-color);
            font-size: 1.5em;
        }

        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }

        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }

        thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-color);
        }

        tbody tr:hover {
            background: #f8fafc;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .badge-success { background: #d1fae5; color: #065f46; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .badge-danger { background: #fee2e2; color: #991b1b; }
        .badge-info { background: #dbeafe; color: #1e40af; }

        .severity-critical { color: #dc2626; font-weight: bold; }
        .severity-high { color: #ea580c; font-weight: bold; }
        .severity-medium { color: #ca8a04; }
        .severity-low { color: #2563eb; }
        .severity-info { color: #64748b; }

        .metric-row {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            border-bottom: 1px solid var(--border-color);
        }

        .metric-row:last-child {
            border-bottom: none;
        }

        .metric-name {
            font-weight: 500;
            color: var(--text-primary);
        }

        .metric-value {
            font-weight: 600;
            color: var(--primary-color);
        }

        .metric-status {
            margin-left: 10px;
        }

        .metric-pass { color: var(--success-color); }
        .metric-fail { color: var(--danger-color); }

        .insights {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 8px;
        }

        .insights-title {
            font-weight: 600;
            color: #92400e;
            margin-bottom: 10px;
        }

        .insights ul {
            list-style: none;
            padding-left: 0;
        }

        .insights li {
            padding: 5px 0;
            color: #78350f;
        }

        .insights li:before {
            content: "💡 ";
            margin-right: 8px;
        }

        footer {
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            margin-top: 40px;
        }

        @media print {
            .no-print { display: none; }
            .section { page-break-inside: avoid; }
        }

        @media (max-width: 768px) {
            .two-column {
                grid-template-columns: 1fr;
            }

            .dashboard {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Synexian Analysis Report</h1>
            <div class="subtitle">Software Quality Analysis - {{ report.timestamp.strftime("%B %d, %Y %H:%M") }}</div>
        </header>

        <!-- Dashboard -->
        <div class="dashboard">
            <div class="dashboard-card grade">
                <h3>Overall Grade</h3>
                <div class="value grade-{{ report.grade.value.replace('+', '-PLUS').replace(' ', '-') }}">
                    {{ report.grade.value }}
                </div>
            </div>

            <div class="dashboard-card score">
                <h3>Quality Score</h3>
                <div class="value" style="color: {% if report.overall_score >= 80 %}var(--success-color){% elif report.overall_score >= 60 %}var(--warning-color){% else %}var(--danger-color){% endif %}">
                    {{ "%.1f"|format(report.overall_score) }}/100
                </div>
            </div>

            <div class="dashboard-card files">
                <h3>Files Analyzed</h3>
                <div class="value" style="color: #8b5cf6;">
                    {{ "{:,}".format(report.summary_stats.total_files) }}
                </div>
                <div style="color: var(--text-secondary); font-size: 0.9em;">
                    {{ "{:,}".format(report.summary_stats.total_lines) }} lines
                </div>
            </div>

            <div class="dashboard-card issues">
                <h3>Total Issues</h3>
                <div class="value" style="color: {% if report.summary_stats.critical_issues > 0 %}var(--danger-color){% elif report.summary_stats.high_issues > 0 %}var(--warning-color){% else %}var(--success-color){% endif %}">
                    {{ report.summary_stats.total_issues }}
                </div>
                <div style="color: var(--text-secondary); font-size: 0.9em;">
                    {{ "%.2f"|format(report.execution_time_seconds) }}s execution
                </div>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="two-column">
            <div class="section">
                <h2>Issues by Severity</h2>
                <div class="chart-container">
                    <canvas id="severityChart"></canvas>
                </div>
            </div>

            <div class="section">
                <h2>Analyzer Performance</h2>
                <div class="chart-container">
                    <canvas id="analyzerChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Analyzer Results -->
        <div class="section">
            <h2>Detailed Analyzer Results</h2>

            {% for result in report.results %}
            <div style="margin-bottom: 30px; padding: 20px; background: #f8fafc; border-radius: 8px;">
                <h3 style="color: #1e293b; margin-bottom: 15px;">
                    {{ result.analyzer_name.upper() }}
                    <span class="badge badge-{% if result.status.value == 'success' %}success{% else %}danger{% endif %}">
                        {{ result.status.value }}
                    </span>
                </h3>

                {% if result.metrics %}
                <div style="margin-bottom: 15px;">
                    <strong style="color: #64748b;">Metrics:</strong>
                    {% for metric_name, metric in result.metrics.items() %}
                    <div class="metric-row">
                        <span class="metric-name">{{ metric.name.replace('_', ' ').title() }}</span>
                        <span>
                            <span class="metric-value">
                                {% if metric.value is number %}
                                    {{ "%.2f"|format(metric.value) }}
                                {% else %}
                                    {{ metric.value }}
                                {% endif %}
                                {% if metric.unit %}{{ metric.unit }}{% endif %}
                            </span>
                            {% if metric.threshold %}
                                <span style="color: var(--text-secondary); font-size: 0.9em;">
                                    (threshold: {{ metric.threshold }})
                                </span>
                            {% endif %}
                            {% if metric.passed is not none %}
                                <span class="metric-status {% if metric.passed %}metric-pass{% else %}metric-fail{% endif %}">
                                    {{ "✓" if metric.passed else "✗" }}
                                </span>
                            {% endif %}
                        </span>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}

                {% if result.insights %}
                <div class="insights">
                    <div class="insights-title">Insights</div>
                    <ul>
                        {% for insight in result.insights %}
                        <li>{{ insight }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}

                {% if result.issues %}
                <div style="margin-top: 15px;">
                    <strong style="color: #64748b;">Issues Found: {{ result.issues|length }}</strong>
                    <ul style="margin-top: 10px; list-style: none; padding-left: 0;">
                        {% for issue in result.issues[:5] %}
                        <li style="padding: 8px; border-left: 3px solid {% if issue.severity.value == 'CRITICAL' %}#dc2626{% elif issue.severity.value == 'HIGH' %}#ea580c{% elif issue.severity.value == 'MEDIUM' %}#ca8a04{% elif issue.severity.value == 'LOW' %}#2563eb{% else %}#64748b{% endif %}; margin-bottom: 8px; background: white; border-radius: 4px;">
                            <strong class="severity-{{ issue.severity.value.lower() }}">{{ issue.severity.value }}</strong>: {{ issue.title }}
                            {% if issue.file_path %}
                                <br><span style="color: #64748b; font-size: 0.9em;">{{ issue.file_path.name }}{% if issue.line_number %}:{{ issue.line_number }}{% endif %}</span>
                            {% endif %}
                        </li>
                        {% endfor %}
                        {% if result.issues|length > 5 %}
                        <li style="color: #64748b; font-style: italic;">... and {{ result.issues|length - 5 }} more issues</li>
                        {% endif %}
                    </ul>
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <!-- Project Information -->
        <div class="section">
            <h2>Project Information</h2>
            <table>
                <tr>
                    <td><strong>Project Path</strong></td>
                    <td>{{ report.project_path }}</td>
                </tr>
                <tr>
                    <td><strong>Analysis Date</strong></td>
                    <td>{{ report.timestamp.strftime("%Y-%m-%d %H:%M:%S") }}</td>
                </tr>
                <tr>
                    <td><strong>Total Files</strong></td>
                    <td>{{ "{:,}".format(report.summary_stats.total_files) }}</td>
                </tr>
                <tr>
                    <td><strong>Total Lines of Code</strong></td>
                    <td>{{ "{:,}".format(report.summary_stats.total_lines) }}</td>
                </tr>
                <tr>
                    <td><strong>Execution Time</strong></td>
                    <td>{{ "%.2f"|format(report.execution_time_seconds) }} seconds</td>
                </tr>
            </table>
        </div>

        <footer>
            <p>Generated by <strong>Synexian Agent</strong></p>
            <p style="margin-top: 10px; color: #94a3b8;">
                🤖 AI-Powered Software Quality Analysis | v0.1.0
            </p>
        </footer>
    </div>

    <script>
        // Severity Chart
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        new Chart(severityCtx, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low', 'Info'],
                datasets: [{
                    data: [
                        {{ report.summary_stats.critical_issues }},
                        {{ report.summary_stats.high_issues }},
                        {{ report.summary_stats.medium_issues }},
                        {{ report.summary_stats.low_issues }},
                        {{ report.summary_stats.info_issues }}
                    ],
                    backgroundColor: [
                        '#dc2626',
                        '#ea580c',
                        '#ca8a04',
                        '#2563eb',
                        '#64748b'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    title: {
                        display: false
                    }
                }
            }
        });

        // Analyzer Performance Chart
        const analyzerCtx = document.getElementById('analyzerChart').getContext('2d');
        new Chart(analyzerCtx, {
            type: 'bar',
            data: {
                labels: [
                    {% for result in report.results %}'{{ result.analyzer_name }}'{% if not loop.last %},{% endif %}{% endfor %}
                ],
                datasets: [{
                    label: 'Issues Found',
                    data: [
                        {% for result in report.results %}{{ result.issues|length }}{% if not loop.last %},{% endif %}{% endfor %}
                    ],
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""


class HTMLReporter(BaseReporter):
    """Generate enhanced HTML reports with charts and visualizations."""

    def __init__(self, output_dir: Path):
        """Initialize reporter.

        Args:
            output_dir: Output directory for reports
        """
        self.output_dir = output_dir

    def generate(self, report: AnalysisReport) -> Path:
        """Generate HTML report.

        Args:
            report: Analysis report

        Returns:
            Path to HTML file
        """
        ensure_dir(self.output_dir)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synexian_report_{timestamp}.html"
        output_path = self.output_dir / filename

        # Render template
        template = Template(HTML_TEMPLATE)
        html_content = template.render(report=report)

        # Write report
        with open(output_path, "w") as f:
            f.write(html_content)

        # Also save as latest.html
        latest_path = self.output_dir / "latest.html"
        with open(latest_path, "w") as f:
            f.write(html_content)

        return output_path
