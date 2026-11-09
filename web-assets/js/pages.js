"use strict";
function setupPagedUserSection(data, contentBatches) {
    const contentDiv = document.getElementById(data.contentId);
    const visibleIndicator = document.getElementById(data.visibleId);
    const pageIndicator = document.getElementById(data.pageId);
    const prev = document.getElementById(data.prevId);
    const next = document.getElementById(data.nextId);
    const lastPageIndex = Math.ceil(data.count / data.pageSize) - 1;
    let currentPage = 0;
    let descending = false;
    let currentPromise = null;
    function batchRanges(page) {
        const results = [];
        let needed = data.pageSize;
        let contentIndex = page * data.pageSize;
        for (const batch of descending ? contentBatches.toReversed() : contentBatches) {
            if (contentIndex < batch.length) {
                const elements = Math.min(needed, batch.length - contentIndex);
                const batchStartIndex = descending ? batch.length - contentIndex - elements : contentIndex;
                const entry = [batch, batchStartIndex, elements];
                if (descending) {
                    results.unshift(entry);
                }
                else {
                    results.push(entry);
                }
                needed -= elements;
                if (needed === 0) {
                    break;
                }
                contentIndex = 0;
            }
            else {
                contentIndex -= batch.length;
            }
        }
        return results;
    }
    function refreshContents(batches) {
        const promise = Promise.all(batches.map(x => x[0].content)).then(ready => {
            if (promise === currentPromise) {
                let elements = [];
                for (let i = 0; i < batches.length; i++) {
                    elements = elements.concat(ready[i].slice(batches[i][1], batches[i][1] + batches[i][2]));
                }
                contentDiv.setHTMLUnsafe(elements.join(""));
                updateDates(contentDiv);
            }
        });
        currentPromise = promise;
    }
    function goToPage(page) {
        if (currentPage === page) {
            return;
        }
        const batches = batchRanges(page);
        prev.disabled = (page <= 0);
        next.disabled = (page >= lastPageIndex);
        const pageStart = (page * data.pageSize) + 1;
        const elements = batches.map(x => x[2]).reduce((x, y) => x + y, 0);
        visibleIndicator.textContent = pageStart.toLocaleString() + " - " + (pageStart + elements - 1).toLocaleString();
        currentPage = page;
        contentDiv.scrollTop = 0;
        refreshContents(batches);
    }
    const order = document.getElementById(data.orderId);
    if (order !== null) {
        descending = order.checked;
        function toggleOrder() {
            descending = order.checked;
            refreshContents(batchRanges(currentPage));
        }
        order.addEventListener("change", (event) => {
            toggleOrder();
        });
    }
    function parsePage() {
        let val = parseInt(pageIndicator.value, 10);
        if (isNaN(val)) {
            return null;
        }
        val = Math.max(0, Math.min(lastPageIndex, val - 1));
        return val;
    }
    const startAnchor = window.location.hash;
    function getStartPage() {
        if (startAnchor.startsWith("#")) {
            const anchor = startAnchor.slice(1);
            const index = data.anchors.indexOf(anchor);
            if (index !== -1) {
                const pageIndex = Math.floor(index / data.pageSize);
                return descending ? lastPageIndex - pageIndex : pageIndex;
            }
        }
        return parsePage() ?? 0;
    }
    const startPage = getStartPage();
    if (startPage === 0) {
        if (descending) {
            refreshContents(batchRanges(0));
        }
    }
    else {
        goToPage(startPage);
    }
    if (startAnchor.startsWith("#") && currentPromise != null) {
        currentPromise.then((x) => {
            window.location.hash = "";
            window.location.hash = startAnchor;
        });
    }
    pageIndicator.value = currentPage + 1;
    prev.addEventListener("click", (event) => {
        if (currentPage > 0) {
            goToPage(currentPage - 1);
            pageIndicator.value = currentPage + 1;
        }
    });
    next.addEventListener("click", (event) => {
        if (currentPage < lastPageIndex) {
            goToPage(currentPage + 1);
            pageIndicator.value = currentPage + 1;
        }
    });
    pageIndicator.addEventListener("input", (event) => {
        let page = parsePage();
        if (page !== null) {
            goToPage(page);
        }
    });
    pageIndicator.addEventListener("change", (event) => {
        let page = parsePage();
        if (page !== null) {
            goToPage(page);
            pageIndicator.value = currentPage + 1;
        }
    });
}

window.addEventListener("DOMContentLoaded", (event) => {
    if (window.pagePromises !== undefined) {
        for (const entry of window.pagePromises) {
            entry.data.then(x => {
                setupPagedUserSection(x, entry.contentBatches);
            })
        }
    }
});
