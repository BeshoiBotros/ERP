/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, useRef, useEffect } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

class DisbursementDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        
        this.state = useState({
            kpi: {},
            charts: {},
            recent_activity: [],
            month: new Date().getMonth() + 1,
            year: new Date().getFullYear(),
            category_tag_id: "",
            categories: [],
            loading: true
        });

        this.productChartRef = useRef("productChart");
        this.categoryChartRef = useRef("categoryChart");
        this.productChartInstance = null;
        this.categoryChartInstance = null;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.loadCategories();
            await this.loadData();
        });

        useEffect(() => {
            if (!this.state.loading) {
                this.renderCharts();
            }
        });
    }

    async loadCategories() {
        this.state.categories = await this.orm.searchRead(
            "eh.product.category.tag",
            [],
            ["id", "name"]
        );
    }

    async loadData() {
        this.state.loading = true;
        
        try {
            const data = await this.rpc("/eh_monthly_disbursement/dashboard_data", {
                month: this.state.month,
                year: this.state.year,
                category_tag_id: this.state.category_tag_id
            });
            
            this.state.labels = data.labels;
            this.state.kpi = data.kpi;
            this.state.charts = data.charts;
            this.state.tables = data.tables;
            this.state.recent_activity = data.recent_activity;
        } catch (error) {
            console.error("Failed to load dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    renderCharts() {
        if (!this.productChartRef.el || !this.categoryChartRef.el) return;

        if (this.productChartInstance) {
            this.productChartInstance.destroy();
        }
        if (this.categoryChartInstance) {
            this.categoryChartInstance.destroy();
        }

        // Top Products Chart (Bar)
        this.productChartInstance = new Chart(this.productChartRef.el, {
            type: 'bar',
            data: {
                labels: this.state.charts.products.labels,
                datasets: [
                    {
                        label: _t('Disbursed'),
                        data: this.state.charts.products.out_data,
                        backgroundColor: 'rgba(220, 53, 69, 0.7)',
                        borderColor: 'rgb(220, 53, 69)',
                        borderWidth: 1
                    },
                    {
                        label: _t('Returned'),
                        data: this.state.charts.products.return_data,
                        backgroundColor: 'rgba(40, 167, 69, 0.7)',
                        borderColor: 'rgb(40, 167, 69)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Category Cost Distribution (Pie)
        this.categoryChartInstance = new Chart(this.categoryChartRef.el, {
            type: 'pie',
            data: {
                labels: this.state.charts.categories.labels,
                datasets: [{
                    data: this.state.charts.categories.data,
                    backgroundColor: [
                        'rgba(113, 99, 158, 0.7)',
                        'rgba(23, 162, 184, 0.7)',
                        'rgba(255, 193, 7, 0.7)',
                        'rgba(253, 126, 20, 0.7)',
                        'rgba(32, 201, 151, 0.7)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    formatAmount(amount) {
        if (amount === undefined || amount === null) return "";
        return Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " LE";
    }

    async onFilterChange(ev) {
        const target = ev.currentTarget;
        this.state[target.name] = target.value;
        await this.loadData();
    }
}

DisbursementDashboard.template = "eh_monthly_disbursement.Dashboard";

registry.category("actions").add("eh_disbursement_dashboard", DisbursementDashboard);
