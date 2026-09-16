/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { Component, useState, onWillStart } = owl;

export class EhDiscountDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.state = useState({
            date_from: "",
            date_to: "",
            vendor_id: "",
            kpi: {
                total_discount: 0,
                company_share: 0,
                vendor_share: 0,
                program_count: 0,
            },
            vendors: [],
            customers: [],
            vendors_list: [],
            currency_symbol: "",
            currency_position: "after",
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        const params = {};
        if (this.state.date_from) params.date_from = this.state.date_from;
        if (this.state.date_to) params.date_to = this.state.date_to;
        if (this.state.vendor_id) params.vendor_id = this.state.vendor_id;

        const result = await this.rpc("/eh_discount_manager/dashboard_data", params);
        this.state.kpi = result.kpi;
        this.state.vendors = result.vendors;
        this.state.customers = result.customers;
        this.state.vendors_list = result.vendors_list || [];
        this.state.currency_symbol = result.currency_symbol;
        this.state.currency_position = result.currency_position;
        this.state.loading = false;
    }

    async onApplyFilter() {
        await this.loadData();
    }

    async onClearFilter() {
        this.state.date_from = "";
        this.state.date_to = "";
        this.state.vendor_id = "";
        await this.loadData();
    }

    onVendorChange(ev) {
        this.state.vendor_id = ev.target.value;
    }

    onDateFromChange(ev) {
        this.state.date_from = ev.target.value;
    }

    onDateToChange(ev) {
        this.state.date_to = ev.target.value;
    }

    formatCurrency(amount) {
        const formatted = Number(amount || 0).toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        if (this.state.currency_position === "before") {
            return this.state.currency_symbol + " " + formatted;
        }
        return formatted + " " + this.state.currency_symbol;
    }
}

EhDiscountDashboard.template = "eh_discount_manager.DiscountDashboard";

registry.category("actions").add("eh_discount_dashboard", EhDiscountDashboard);
