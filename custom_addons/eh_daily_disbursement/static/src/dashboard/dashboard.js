/** @odoo-module **/
// ============================================================================
// ERP Heritage
// Copyright (C) 2026 (https://www.erpheritage.com.au/)
// ============================================================================
//
// Daily Disbursement dashboard (client action).
//
// All figures come from one ORM call, eh.daily.disbursement.dashboard.
// get_dashboard_data(), so access rights and company rules apply server
// side. Every number is a drill-down: it opens the exact lines (or sheets)
// behind it, reusing the domain the server computed the figure from.

import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { download } from "@web/core/network/download";
import { formatCurrency } from "@web/core/currency";
import { loadJS } from "@web/core/assets";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";

const { DateTime } = luxon;

const DASHBOARD_MODEL = "eh.daily.disbursement.dashboard";
const LINE_MODEL = "eh.daily.disbursement.line";
const SHEET_MODEL = "eh.daily.disbursement";
// Remembered per browser so returning from a drill-down restores the view.
const STORAGE_KEY = "eh_daily_disbursement.dashboard.filters";
const DEFAULT_FILTERS = {
    period: "this_month",
    dateFrom: "",
    dateTo: "",
    tagId: false,
    includeDraft: true,
};

export class DailyDisbursementDashboard extends Component {
    static template = "eh_daily_disbursement.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.periods = [
            { key: "today", label: _t("Today") },
            { key: "yesterday", label: _t("Yesterday") },
            { key: "this_week", label: _t("This Week") },
            { key: "this_month", label: _t("This Month") },
            { key: "last_30_days", label: _t("Last 30 Days") },
            { key: "custom", label: _t("Custom") },
        ];
        this.state = useState({
            filters: this.restoreFilters(),
            data: null,
            loading: true,
            error: null,
            exporting: false,
        });
        this.rootRef = useRef("root");
        this.trendRef = useRef("trendChart");
        this.productsRef = useRef("productsChart");
        this.charts = [];
        this.requestId = 0;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.load();
        });
        useEffect(
            () => this.renderCharts(),
            () => [this.state.data]
        );
        onWillUnmount(() => this.destroyCharts());
    }

    // ------------------------------------------------------------------
    // Filters
    // ------------------------------------------------------------------

    restoreFilters() {
        try {
            const saved = JSON.parse(browser.localStorage.getItem(STORAGE_KEY) || "{}");
            return { ...DEFAULT_FILTERS, ...saved };
        } catch {
            return { ...DEFAULT_FILTERS };
        }
    }

    saveFilters() {
        try {
            browser.localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state.filters));
        } catch {
            // Private mode / blocked storage: the dashboard still works.
        }
    }

    get customIncomplete() {
        const f = this.state.filters;
        return f.period === "custom" && (!f.dateFrom || !f.dateTo);
    }

    setPeriod(period) {
        const f = this.state.filters;
        if (period === "custom" && !f.dateFrom && this.state.data) {
            // Start the custom range from what is on screen.
            f.dateFrom = this.state.data.period.date_from;
            f.dateTo = this.state.data.period.date_to;
        }
        f.period = period;
        this.load();
    }

    onDateChange(field, ev) {
        this.state.filters[field] = ev.target.value;
        this.load();
    }

    onTagChange(ev) {
        this.state.filters.tagId = ev.target.value ? parseInt(ev.target.value) : false;
        this.load();
    }

    onDraftToggle(ev) {
        this.state.filters.includeDraft = ev.target.checked;
        this.load();
    }

    // ------------------------------------------------------------------
    // Data
    // ------------------------------------------------------------------

    async load() {
        if (this.customIncomplete) {
            this.state.loading = false;
            return;
        }
        const requestId = ++this.requestId;
        const f = this.state.filters;
        this.state.loading = true;
        try {
            const data = await this.orm.call(DASHBOARD_MODEL, "get_dashboard_data", [], {
                period: f.period,
                date_from: f.period === "custom" ? f.dateFrom : false,
                date_to: f.period === "custom" ? f.dateTo : false,
                tag_id: f.tagId || false,
                include_draft: f.includeDraft,
            });
            if (requestId !== this.requestId) {
                return; // a newer filter change already superseded this answer
            }
            if (f.tagId && !data.tags.some((tag) => tag.id === f.tagId)) {
                f.tagId = false; // remembered tag was archived or deleted
            }
            this.state.data = data;
            this.state.error = null;
            this.saveFilters();
        } catch (error) {
            if (requestId === this.requestId) {
                this.state.error =
                    error.data?.message || error.message || _t("The dashboard could not be loaded.");
            }
        } finally {
            if (requestId === this.requestId) {
                this.state.loading = false;
            }
        }
    }

    get isEmpty() {
        return !this.state.data.kpi.sheet_count.value;
    }

    get showTrend() {
        return this.state.data.trend.points.length > 1;
    }

    // ------------------------------------------------------------------
    // Formatting
    // ------------------------------------------------------------------

    money(value, options = {}) {
        return formatCurrency(value || 0, this.state.data.currency.id, options);
    }

    qty(value) {
        const digits = Number.isInteger(value) ? 0 : 2;
        return formatFloat(value || 0, { digits: [false, digits] });
    }

    date(iso, format = "dd LLL yyyy") {
        return iso ? DateTime.fromISO(iso).toFormat(format) : "";
    }

    get periodLabel() {
        const { date_from, date_to } = this.state.data.period;
        return date_from === date_to
            ? this.date(date_from)
            : `${this.date(date_from, "dd LLL")} – ${this.date(date_to)}`;
    }

    get previousLabel() {
        const { prev_from, prev_to } = this.state.data.period;
        return prev_from === prev_to
            ? this.date(prev_from)
            : `${this.date(prev_from, "dd LLL")} – ${this.date(prev_to)}`;
    }

    delta(key) {
        // pct is rendered in its own LTR-isolated element so "+12.5%" never
        // reorders to "12.5%+" inside Arabic text.
        const kpi = this.state.data.kpi[key];
        if (kpi.delta_pct === null) {
            return {
                icon: "fa-minus",
                pct: "",
                text: kpi.value ? _t("Nothing in the previous period") : _t("No change"),
            };
        }
        const sign = kpi.delta_pct > 0 ? "+" : "";
        return {
            icon: kpi.delta_pct > 0 ? "fa-arrow-up" : kpi.delta_pct < 0 ? "fa-arrow-down" : "fa-minus",
            pct: `${sign}${kpi.delta_pct}%`,
            text: _t("vs previous period"),
        };
    }

    get stateCounts() {
        const counts = this.state.data.sheets.by_state;
        return [
            { key: "draft", count: counts.draft, label: _t("draft") },
            { key: "confirmed", count: counts.confirmed, label: _t("confirmed") },
            { key: "closed", count: counts.closed, label: _t("closed") },
        ];
    }

    previousTitle(key) {
        return _t("Previous period: %s", this.money(this.state.data.kpi[key].previous));
    }

    tagTitle(row) {
        return _t("Disbursed %(disbursed)s · Returned %(returned)s", {
            disbursed: this.money(row.disbursed_cost),
            returned: this.money(row.returned_cost),
        });
    }

    get tableSpecs() {
        return [
            { key: "disbursed", moveType: "out", totalKey: "disbursed_cost", title: _t("Disbursed products") },
            { key: "returned", moveType: "return", totalKey: "returned_cost", title: _t("Returned products") },
        ];
    }

    tagShare(row) {
        const max = Math.max(...this.state.data.by_tag.map((r) => r.disbursed_cost), 0);
        return max ? Math.round((row.disbursed_cost / max) * 100) : 0;
    }

    // ------------------------------------------------------------------
    // Exports (same filters as the screen)
    // ------------------------------------------------------------------

    get exportFilters() {
        const f = this.state.filters;
        const custom = f.period === "custom";
        return {
            period: f.period,
            date_from: custom ? f.dateFrom : "",
            date_to: custom ? f.dateTo : "",
            tag_id: f.tagId || "",
            include_draft: f.includeDraft ? "1" : "0",
        };
    }

    exportPdf() {
        const filters = this.exportFilters;
        this.action.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "eh_daily_disbursement.report_period_summary",
            report_file: "eh_daily_disbursement.report_period_summary",
            name: _t("Disbursement Summary"),
            data: { ...filters, tag_id: filters.tag_id || false, include_draft: filters.include_draft === "1" },
        });
    }

    async exportXlsx() {
        this.state.exporting = true;
        try {
            await download({ url: "/eh_daily_disbursement/export/xlsx", data: this.exportFilters });
        } finally {
            this.state.exporting = false;
        }
    }

    // ------------------------------------------------------------------
    // Drill-downs
    // ------------------------------------------------------------------

    openLines(extraDomain = [], name = _t("Disbursement Lines")) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: LINE_MODEL,
            views: [
                [false, "list"],
                [false, "pivot"],
                [false, "graph"],
            ],
            domain: [...this.state.data.line_domain, ...extraDomain],
            context: { create: false },
        });
    }

    openKpi(kind) {
        if (kind === "net") {
            this.openLines([], _t("All Lines"));
        } else if (kind === "out") {
            this.openLines([["move_type", "=", "out"]], _t("Disbursed Lines"));
        } else {
            this.openLines([["move_type", "=", "return"]], _t("Returned Lines"));
        }
    }

    openProduct(row) {
        this.openLines([["product_id", "=", row.product_id]], row.name);
    }

    openTag(row) {
        this.openLines([["tag_id", "=", row.tag_id]], row.name);
    }

    openBucket(point) {
        if (this.state.data.trend.granularity === "day") {
            this.openLines([["date", "=", point.date]], this.date(point.date));
            return;
        }
        const end = DateTime.fromISO(point.date).plus({ months: 1 }).toISODate();
        this.openLines(
            [
                ["date", ">=", point.date],
                ["date", "<", end],
            ],
            this.date(point.date, "LLLL yyyy")
        );
    }

    openSheets(kind) {
        const tag = this.state.filters.tagId ? [["tag_id", "=", this.state.filters.tagId]] : [];
        const domain =
            kind === "overdue"
                ? [["state", "=", "draft"], ["date", "<", DateTime.local().toISODate()]]
                : [["state", "=", "confirmed"]];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: kind === "overdue" ? _t("Overdue Draft Sheets") : _t("Sheets to Close"),
            res_model: SHEET_MODEL,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [...domain, ...tag],
        });
    }

    openSheet(sheetId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: SHEET_MODEL,
            res_id: sheetId,
            views: [[false, "form"]],
        });
    }

    // ------------------------------------------------------------------
    // Charts
    // ------------------------------------------------------------------

    destroyCharts() {
        for (const chart of this.charts) {
            chart.destroy();
        }
        this.charts = [];
    }

    renderCharts() {
        this.destroyCharts();
        if (!this.state.data || !window.Chart || !this.rootRef.el) {
            return;
        }
        const css = getComputedStyle(this.rootRef.el);
        const token = (name, fallback) => css.getPropertyValue(name).trim() || fallback;
        const theme = {
            out: token("--eh-dd-series-out", "#3987e5"),
            ret: token("--eh-dd-series-return", "#d95926"),
            ink: token("--eh-text-muted", "#7E9089"),
            grid: token("--eh-border", "#1E2A24"),
            surface: token("--eh-surface", "#0F1512"),
            font: token("--eh-font", "system-ui, sans-serif"),
        };
        const rtl = localization.direction === "rtl";
        const moneyTick = (value) => this.money(value, { humanReadable: true });
        const tooltip = {
            rtl,
            backgroundColor: token("--eh-surface-2", "#151D19"),
            borderColor: token("--eh-border-strong", "#2A3B32"),
            borderWidth: 1,
            titleColor: token("--eh-text", "#E8EDE9"),
            bodyColor: token("--eh-text-dim", "#A6BAAF"),
            footerColor: token("--eh-text", "#E8EDE9"),
            padding: 10,
            usePointStyle: true,
        };
        const legend = {
            position: "top",
            align: "end",
            rtl,
            labels: { color: theme.ink, usePointStyle: true, pointStyle: "rectRounded", boxWidth: 8 },
        };
        Chart.defaults.font.family = theme.font;

        if (this.trendRef.el) {
            this.charts.push(this.trendChart(theme, tooltip, legend, moneyTick, rtl));
        }
        if (this.productsRef.el && this.state.data.top_products.length) {
            this.charts.push(this.productsChart(theme, tooltip, legend, moneyTick, rtl));
        }
    }

    trendChart(theme, tooltip, legend, moneyTick, rtl) {
        const { granularity } = this.state.data.trend;
        // RTL reads time right-to-left. Reverse the data rather than the axis:
        // a reversed axis mis-measures edge padding and clips the end labels.
        const points = rtl ? [...this.state.data.trend.points].reverse() : this.state.data.trend.points;
        const series = (label, key, color) => ({
            label,
            data: points.map((p) => p[key]),
            borderColor: color,
            backgroundColor: color,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBorderWidth: 2,
            pointHoverBorderColor: theme.surface,
            tension: 0.25,
            cubicInterpolationMode: "monotone", // smoothing never dips below zero
        });
        return new Chart(this.trendRef.el, {
            type: "line",
            data: {
                labels: points.map((p) => this.date(p.date, granularity === "day" ? "dd LLL" : "LLL yyyy")),
                datasets: [
                    series(_t("Disbursed"), "disbursed", theme.out),
                    series(_t("Returned"), "returned", theme.ret),
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                onClick: (_event, elements) => {
                    const point = elements.length && points[elements[0].index];
                    if (point && (point.disbursed || point.returned)) {
                        this.openBucket(point); // an empty day has nothing to open
                    }
                },
                onHover: (event, elements) => {
                    const point = elements.length && points[elements[0].index];
                    event.native.target.style.cursor =
                        point && (point.disbursed || point.returned) ? "pointer" : "default";
                },
                plugins: {
                    legend,
                    tooltip: {
                        ...tooltip,
                        callbacks: {
                            label: (ctx) => ` ${ctx.dataset.label}: ${this.money(ctx.parsed.y)}`,
                            footer: (items) =>
                                _t("Net: %s", this.money(points[items[0].dataIndex].net)),
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        border: { color: theme.grid },
                        // Half-step inset at both ends so edge date labels are never clipped.
                        offset: true,
                        ticks: { color: theme.ink, maxRotation: 0, autoSkipPadding: 12 },
                    },
                    y: {
                        position: rtl ? "right" : "left",
                        beginAtZero: true,
                        grid: { color: theme.grid },
                        border: { display: false },
                        ticks: { color: theme.ink, callback: moneyTick, maxTicksLimit: 6 },
                    },
                },
            },
        });
    }

    productsChart(theme, tooltip, legend, moneyTick, rtl) {
        const rows = this.state.data.top_products;
        const shorten = (name) => (name.length > 26 ? name.slice(0, 25) + "…" : name);
        const series = (label, key, color) => ({
            label,
            data: rows.map((r) => r[key]),
            backgroundColor: color,
            borderRadius: 4,
            borderSkipped: "start",
            barPercentage: 0.9,
            categoryPercentage: 0.7,
        });
        return new Chart(this.productsRef.el, {
            type: "bar",
            data: {
                labels: rows.map((r) => shorten(r.name)),
                datasets: [
                    series(_t("Disbursed"), "out_cost", theme.out),
                    series(_t("Returned"), "return_cost", theme.ret),
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                onClick: (_event, elements) => {
                    if (elements.length) {
                        this.openProduct(rows[elements[0].index]);
                    }
                },
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length ? "pointer" : "default";
                },
                plugins: {
                    legend,
                    tooltip: {
                        ...tooltip,
                        callbacks: {
                            title: (items) => rows[items[0].dataIndex].name,
                            label: (ctx) => {
                                const row = rows[ctx.dataIndex];
                                const qty = ctx.datasetIndex === 0 ? row.out_qty : row.return_qty;
                                return ` ${ctx.dataset.label}: ${this.money(ctx.parsed.x)} (${this.qty(qty)} ${row.uom})`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        reverse: rtl,
                        beginAtZero: true,
                        grid: { color: theme.grid },
                        border: { display: false },
                        ticks: { color: theme.ink, callback: moneyTick, maxTicksLimit: 5 },
                    },
                    y: {
                        position: rtl ? "right" : "left",
                        grid: { display: false },
                        border: { color: theme.grid },
                        ticks: { color: theme.ink },
                    },
                },
            },
        });
    }
}

registry.category("actions").add("eh_daily_disbursement_dashboard", DailyDisbursementDashboard);
