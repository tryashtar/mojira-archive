"use strict";
function anchorTab() {
    const startAnchor = window.location.hash;
    if (startAnchor.startsWith("#comment-id-")) {
        const input = document.getElementById("issue-tab-comments");
        input.checked = true;
    }
    else if (startAnchor.startsWith("#history-id-")) {
        const input = document.getElementById("issue-tab-history");
        input.checked = true;
    }
}

function easyClickTabs() {
    for (const label of document.getElementsByTagName("label")) {
        const target = label.htmlFor;
        if (target !== "") {
            const button = document.getElementById(target);
            if (button != null && button.nodeName === "INPUT" && button.type === "radio") {
                label.addEventListener("mousedown", (event) => {
                    button.checked = true;
                });
            }
        }
    }
}

function updateDates(root) {
    const times = root.getElementsByTagName("time");
    for (const element of times) {
        const date = new Date(element.getAttribute("datetime"));
        element.textContent = date.toLocaleString();
    }
}

window.addEventListener("DOMContentLoaded", (event) => {
    anchorTab();
    easyClickTabs();
    updateDates(document);
});
