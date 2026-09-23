/**
 * Vanilla click-to-sort for <table data-sortable>. Replaces jquery.tablesorter.
 * Sorts by a cell's data-sort-value when present, otherwise its text content;
 * numeric-aware. Click a <th> to sort ascending, click again to reverse.
 */
(function () {
    "use strict";

    function cellValue(row, index) {
        const cell = row.children[index];
        if (!cell) {
            return "";
        }
        return cell.dataset.sortValue !== undefined ? cell.dataset.sortValue : cell.textContent.trim();
    }

    function compareValues(a, b) {
        const numA = parseFloat(a);
        const numB = parseFloat(b);
        if (!isNaN(numA) && !isNaN(numB) && String(numA) === a && String(numB) === b) {
            return numA - numB;
        }
        return a.localeCompare(b, undefined, {numeric: true, sensitivity: "base"});
    }

    function sortTable(table, columnIndex, ascending) {
        const tbody = table.tBodies[0];
        if (!tbody) {
            return;
        }
        const rows = Array.prototype.slice.call(tbody.rows);
        rows.sort(function (rowA, rowB) {
            const result = compareValues(cellValue(rowA, columnIndex), cellValue(rowB, columnIndex));
            return ascending ? result : -result;
        });
        rows.forEach(function (row) {
            tbody.appendChild(row);
        });
    }

    function initTable(table) {
        const headerRow = table.tHead && table.tHead.rows[0];
        if (!headerRow) {
            return;
        }
        Array.prototype.forEach.call(headerRow.cells, function (th, index) {
            if (th.dataset.noSort !== undefined) {
                return;
            }
            th.classList.add("sortable-header");
            th.addEventListener("click", function () {
                const ascending = th.dataset.sortDir !== "asc";
                Array.prototype.forEach.call(headerRow.cells, function (cell) {
                    delete cell.dataset.sortDir;
                });
                th.dataset.sortDir = ascending ? "asc" : "desc";
                sortTable(table, index, ascending);
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("table[data-sortable]").forEach(initTable);
    });
})();
