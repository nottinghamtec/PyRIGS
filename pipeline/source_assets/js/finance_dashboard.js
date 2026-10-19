// Charts for the finance dashboard. Each one also gets a data table beneath it, so no figure is only in a tooltip.
(function () {
    "use strict";

    const filter = document.getElementById("time_filter");
    if (filter) {
        filter.addEventListener("change", function () {
            this.closest("form").submit();
        });
    }

    // Each chart can be swapped for its data table
    document.querySelectorAll("[data-finance-view]").forEach((button) => {
        button.addEventListener("click", () => {
            const target = button.dataset.financeTarget;
            const showTable = button.dataset.financeView === "table";
            document.querySelector(`[data-chart-for="${target}"]`).hidden = showTable;
            document.querySelector(`[data-table-for="${target}"]`).hidden = !showTable;
            document.querySelectorAll(`[data-finance-target="${target}"]`).forEach((other) => {
                const pressed = other === button;
                other.classList.toggle("active", pressed);
                other.setAttribute("aria-pressed", pressed);
            });
        });
    });

    // Narrow the aged debt table to one age band
    const agedButtons = document.querySelectorAll("[data-aged-band]");
    function showAgedBand(band) {
        agedButtons.forEach((button) => {
            const pressed = button.dataset.agedBand === band;
            button.classList.toggle("active", pressed);
            button.setAttribute("aria-pressed", pressed);
        });
        document.querySelectorAll("#aged-debt-invoices tbody tr[data-band]").forEach((row) => {
            row.hidden = band !== "" && row.dataset.band !== band;
        });
    }
    agedButtons.forEach((button) => button.addEventListener("click", () => showAgedBand(button.dataset.agedBand)));

    document.querySelectorAll("[data-quality-more]").forEach((button) => {
        button.addEventListener("click", () => {
            button.previousElementSibling.querySelectorAll("li[hidden]").forEach((item) => {
                item.hidden = false;
            });
            button.remove();
        });
    });

    const source = document.getElementById("finance-charts");
    if (!source || typeof Chart === "undefined") {
        return;
    }
    const data = JSON.parse(source.textContent);
    const style = getComputedStyle(document.querySelector(".finance-viz"));
    const token = (name) => style.getPropertyValue(name).trim();
    const series = (slot) => token(`--viz-series-${slot}`);
    const ordinal = (count) => Array.from({ length: count }, (_, i) => token(`--viz-ordinal-${i + 1}`));
    const surface = token("--viz-surface");
    const ink = token("--viz-ink");

    const pounds = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" });
    const compactPounds = new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: "GBP",
        notation: "compact",
        maximumFractionDigits: 1,
    });
    const whole = new Intl.NumberFormat("en-GB");
    const days = (value) => `${whole.format(value)} day${Math.abs(value) === 1 ? "" : "s"}`;

    function wash(hex, opacity) {
        const value = parseInt(hex.replace("#", ""), 16);
        return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${opacity})`;
    }

    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.color = token("--viz-muted");
    Chart.defaults.borderColor = token("--viz-grid");
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.animation = false;
    Chart.defaults.plugins.legend.labels.color = ink;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.pointStyle = "rectRounded";
    Chart.defaults.plugins.legend.labels.boxHeight = 8;
    Chart.defaults.plugins.legend.align = "start";

    const moneyAxis = { beginAtZero: true, ticks: { callback: (value) => compactPounds.format(value) } };
    const countAxis = { beginAtZero: true, ticks: { precision: 0 } };
    const noGrid = { grid: { display: false } };
    // Bars stay thin, with a rounded end away from the baseline
    const bar = { maxBarThickness: 24, borderRadius: 4, borderSkipped: "start" };

    function table(id, headings, rows) {
        const holder = document.querySelector(`[data-table-for="${id}"]`);
        if (!holder) {
            return;
        }
        const element = document.createElement("table");
        element.className = "table table-sm finance-table mb-0";
        const head = element.createTHead().insertRow();
        headings.forEach((heading, index) => {
            const cell = document.createElement("th");
            cell.textContent = heading;
            if (index > 0) {
                cell.className = "text-end";
            }
            head.appendChild(cell);
        });
        const body = element.createTBody();
        rows.forEach((row) => {
            const line = body.insertRow();
            row.forEach((value, index) => {
                const cell = line.insertCell();
                cell.textContent = value;
                if (index > 0) {
                    cell.className = "text-end";
                }
            });
        });
        holder.appendChild(element);
    }

    function chart(id, config) {
        const canvas = document.getElementById(`chart-${id}`);
        if (canvas) {
            new Chart(canvas, config);
        }
    }

    // Income over the period, stacked by payment method
    const income = data.income;
    if (income.datasets.length) {
        chart("income", {
            type: "bar",
            data: {
                labels: income.labels,
                datasets: income.datasets.map((set) => ({
                    ...set,
                    backgroundColor: series(set.series),
                    // A thin gap in the card's colour separates the stacked segments
                    borderColor: surface,
                    borderWidth: { top: 2 },
                    maxBarThickness: 24,
                })),
            },
            options: {
                interaction: { mode: "index", intersect: false },
                scales: { x: { stacked: true, ...noGrid }, y: { stacked: true, ...moneyAxis } },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (item) => `${item.dataset.label}: ${pounds.format(item.raw)}`,
                            footer: (items) => `Total: ${pounds.format(items.reduce((sum, item) => sum + item.raw, 0))}`,
                        },
                    },
                },
            },
        });
        table(
            "income",
            ["", ...income.datasets.map((set) => set.label), "Total"],
            income.labels.map((label, i) => {
                const values = income.datasets.map((set) => set.data[i]);
                return [label, ...values.map((v) => pounds.format(v)), pounds.format(values.reduce((a, b) => a + b, 0))];
            }),
        );
    }

    // Income built up through the year, against the year before
    const cumulative = data.cumulative;
    chart("cumulative", {
        type: "line",
        data: {
            labels: cumulative.labels,
            datasets: cumulative.datasets.map((set) => ({
                ...set,
                borderColor: series(set.series),
                backgroundColor: series(set.series),
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBorderColor: surface,
                pointHoverBorderWidth: 2,
                tension: 0.2,
            })),
        },
        options: {
            interaction: { mode: "index", intersect: false },
            scales: { x: { ...noGrid, ticks: { maxTicksLimit: 12 } }, y: moneyAxis },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: (items) => `Week starting ${items[0].label}`,
                        label: (item) => `${item.dataset.label}: ${pounds.format(item.raw)}`,
                    },
                },
            },
        },
    });
    table(
        "cumulative",
        ["Week starting", ...cumulative.datasets.map((set) => set.label)],
        cumulative.labels.map((label, i) => [
            label,
            ...cumulative.datasets.map((set) => (set.data[i] === null ? "-" : pounds.format(set.data[i]))),
        ]),
    );

    // From work done, to invoiced, to paid
    const funnel = data.funnel;
    chart("funnel", {
        type: "bar",
        data: {
            labels: funnel.labels,
            datasets: [{ label: "Events", data: funnel.counts, backgroundColor: ordinal(3), ...bar }],
        },
        options: {
            indexAxis: "y",
            scales: { x: countAxis, y: noGrid },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (item) =>
                            `${whole.format(item.raw)} events, worth ${pounds.format(funnel.values[item.dataIndex])}`,
                    },
                },
            },
        },
    });
    table(
        "funnel",
        ["Stage", "Events", "Value (ex. VAT)"],
        funnel.labels.map((label, i) => [label, whole.format(funnel.counts[i]), pounds.format(funnel.values[i])]),
    );

    function histogram(id, spec, label) {
        chart(id, {
            type: "bar",
            data: {
                labels: spec.labels,
                datasets: [{ label: label, data: spec.counts, backgroundColor: series(1), ...bar }],
            },
            options: {
                scales: { x: noGrid, y: countAxis },
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (item) => `${whole.format(item.raw)} ${label.toLowerCase()}` } },
                },
            },
        });
        table(id, ["", label], spec.labels.map((band, i) => [band, whole.format(spec.counts[i])]));
    }

    histogram("days-to-pay", data.daysToPay, "Payments");
    histogram("invoicing-delay", data.invoicingDelay, "Invoices");

    // The middle half of payment times each year, around the median. Years of backdated invoices run to hundreds of
    // days and would flatten the rest, so the axis stops at a year and those are named instead.
    const byYear = data.daysToPayByYear;
    const [floor, ceiling] = [-60, 365];
    const offScale = byYear.labels.filter((_, i) => byYear.upper[i] > ceiling || byYear.lower[i] < floor);
    const byYearSubtitle = document.getElementById("days-to-pay-by-year-subtitle");
    if (offScale.length && byYearSubtitle) {
        byYearSubtitle.textContent += ` Off the scale, but in the table: ${offScale.join(", ")}.`;
    }
    chart("days-to-pay-by-year", {
        type: "line",
        data: {
            labels: byYear.labels,
            datasets: [
                { label: "lower", data: byYear.lower, borderWidth: 0, pointRadius: 0, pointHitRadius: 0 },
                {
                    label: "Middle half of payments",
                    data: byYear.upper,
                    borderWidth: 0,
                    pointRadius: 0,
                    pointHitRadius: 0,
                    backgroundColor: wash(series(1), 0.12),
                    fill: "-1",
                },
                {
                    label: "Median",
                    data: byYear.median,
                    borderColor: series(1),
                    backgroundColor: series(1),
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBorderColor: surface,
                    pointBorderWidth: 2,
                },
            ],
        },
        options: {
            interaction: { mode: "index", intersect: false },
            scales: {
                x: noGrid,
                y: {
                    min: Math.max(floor, Math.min(0, ...byYear.lower)),
                    max: Math.min(ceiling, Math.max(...byYear.upper)),
                    ticks: { callback: (value) => whole.format(value) },
                },
            },
            plugins: {
                legend: { labels: { filter: (item) => item.text !== "lower" } },
                tooltip: {
                    filter: (item) => item.dataset.label === "Median",
                    callbacks: {
                        label: (item) =>
                            `Median ${days(item.raw)} (middle half ${whole.format(byYear.lower[item.dataIndex])} to ${days(byYear.upper[item.dataIndex])})`,
                    },
                },
            },
        },
    });
    table(
        "days-to-pay-by-year",
        ["Academic year", "25th percentile", "Median", "75th percentile"],
        byYear.labels.map((label, i) => [label, days(byYear.lower[i]), days(byYear.median[i]), days(byYear.upper[i])]),
    );

    // How much is owed, by how long it has been owed
    const aged = data.agedDebt;
    chart("aged-debt", {
        type: "bar",
        data: {
            labels: aged.labels,
            datasets: [{ label: "Owed", data: aged.totals, backgroundColor: ordinal(aged.labels.length), ...bar }],
        },
        options: {
            onClick: (event, elements) => {
                if (elements.length) {
                    showAgedBand(String(elements[0].index));
                }
            },
            onHover: (event, elements) => {
                event.native.target.style.cursor = elements.length ? "pointer" : "default";
            },
            indexAxis: "y",
            scales: { x: moneyAxis, y: noGrid },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (item) =>
                            `${pounds.format(item.raw)} across ${whole.format(aged.counts[item.dataIndex])} invoices`,
                    },
                },
            },
        },
    });
    table(
        "aged-debt",
        ["Age", "Invoices", "Owed"],
        aged.labels.map((label, i) => [label, whole.format(aged.counts[i]), pounds.format(aged.totals[i])]),
    );
})();
