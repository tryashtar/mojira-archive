"use strict";
function setupVirtualTable(data, rowBatches) {
    const rowCount = data.rows;
    const rowHeight = data.rowHeight;
    const tableBody = document.getElementById(data.tableBodyId);
    const tableScroll = document.getElementById(data.scrollId);
    let visibleRows = 0;
    let desiredVirtualRows = 0;
    const allIndices = Array.from(data.sort[0].keys());
    let sortedIndices = allIndices;
    let currentIndices = allIndices;
    function updateScroll() {
        const totalHeight = rowHeight * currentIndices.length;
        tableScroll.style.height = totalHeight + "px";
        visibleRows = Math.min(currentIndices.length, Math.ceil(tableBody.clientHeight / rowHeight));
        desiredVirtualRows = Math.min(currentIndices.length, visibleRows * 3);
        const addRows = desiredVirtualRows - (tableBody.children.length - 1);
        for (let i = 0; i < addRows; i += 1) {
            const row = document.createElement("div");
            row.className = "issue-table-virtual-row";
            tableBody.appendChild(row);
        }
    }
    updateScroll();
    let topVirtualIndex = 0;
    let bottomVirtualIndex = 0;
    function checkRows() {
        const topIndexVisible = Math.floor(tableBody.scrollTop / rowHeight);
        const bottomIndexVisible = Math.ceil((tableBody.scrollTop + tableBody.clientHeight) / rowHeight);
        if (topIndexVisible < topVirtualIndex || bottomIndexVisible > bottomVirtualIndex) {
            updateRows();
        }
    }
    const updatePromises = [];
    function getBatchPos(rowIndex) {
        for (const batch of rowBatches) {
            if (rowIndex < batch.length) {
                return [batch, rowIndex];
            }
            rowIndex -= batch.length;
        }
    }
    function updateRows() {
        updatePromises.length = 0;
        const topIndexVisible = Math.floor(tableBody.scrollTop / rowHeight);
        topVirtualIndex = Math.max(0, topIndexVisible - visibleRows);
        bottomVirtualIndex = topVirtualIndex + desiredVirtualRows;
        for (let i = 0; i < tableBody.children.length - 1; i += 1) {
            const vRow = tableBody.children[i + 1];
            if (topVirtualIndex + i < currentIndices.length) {
                vRow.style.top = ((topVirtualIndex + i) * rowHeight) + "px";
                const rowIndex = currentIndices[topVirtualIndex + i];
                const [batch, index] = getBatchPos(rowIndex);
                let promise;
                promise = batch.data.then(rows => {
                    if (updatePromises.includes(promise)) {
                        vRow.innerHTML = rows[index];
                        updateDates(vRow);
                    }
                });
                updatePromises.push(promise);
            }
            else {
                vRow.style.top = -rowHeight + "px";
                vRow.textContent = "";
            }
        }
    }
    updateRows();
    tableBody.addEventListener("scroll", (event) => {
        checkRows();
    });
    const searches = {};
    const filters = {};
    function filterIncluded(index) {
        for (const [key, value] of Object.entries(searches)) {
            if (value !== "" && !data.search[key][index].includes(value)) {
                return false;
            }
        }
        for (const [key, value] of Object.entries(filters)) {
            if (value !== "" && data.filter[key][index] !== value) {
                return false;
            }
        }
        return true;
    }
    const labelCount = document.getElementById(data.countId);
    function filterResults() {
        currentIndices = sortedIndices.filter(i => filterIncluded(i));
        if (currentIndices.length === allIndices.length) {
            labelCount.textContent = allIndices.length.toLocaleString() + " " + data.labelText;
        }
        else {
            labelCount.textContent = currentIndices.length.toLocaleString() + " / " + allIndices.length.toLocaleString() + " " + data.labelText;
        }
        updateScroll();
        updateRows();
    }
    for (const key of Object.keys(data.search)) {
        const element = document.getElementById(key);
        searches[key] = element.value.toLowerCase();
        element.addEventListener("input", (event) => {
            searches[key] = element.value.toLowerCase();
            filterResults();
        });
    }
    for (const key of Object.keys(data.filter)) {
        const element = document.getElementById(key);
        let value = element.options[element.selectedIndex].value;
        if (value === "null") {
            value = null;
        }
        filters[key] = value;
        element.addEventListener("change", (event) => {
            let value = element.options[element.selectedIndex].value;
            if (value === "null") {
                value = null;
            }
            filters[key] = value;
            filterResults();
        });
    }
    filterResults();
    const tableHeader = document.getElementById(data.tableHeaderId);
    let sortIndex = -1;
    let sortDir = 0;
    function sortColumn(columnIndex) {
        if (columnIndex === sortIndex) {
            sortDir += 1;
            if (sortDir > 2) {
                sortDir = 0;
            }
        }
        else {
            if (sortIndex != -1) {
                tableHeader.children[sortIndex].classList.remove("table-sort-ascending");
                tableHeader.children[sortIndex].classList.remove("table-sort-descending");
            }
            sortIndex = columnIndex;
            sortDir = 0;
        }
        const header = tableHeader.children[columnIndex];
        if (sortDir === 0) {
            header.classList.add("table-sort-ascending");
            header.classList.remove("table-sort-descending");
            sortedIndices = data.sort[columnIndex];
        }
        else if (sortDir === 1) {
            header.classList.add("table-sort-descending");
            header.classList.remove("table-sort-ascending");
            sortedIndices = data.sort[columnIndex].toReversed();
        }
        else {
            header.classList.remove("table-sort-descending");
            header.classList.remove("table-sort-ascending");
            sortedIndices = allIndices;
        }
        filterResults();
    }
    for (let i = 0; i < tableHeader.children.length; i += 1) {
        tableHeader.children[i].addEventListener("click", (event) => {
            sortColumn(i);
        });
    }
}

window.addEventListener("DOMContentLoaded", (event) => {
    if (window.tablePromises !== undefined) {
        for (const entry of window.tablePromises) {
            entry.data.then(x => {
                setupVirtualTable(x, entry.rowBatches);
            })
        }
    }
});
