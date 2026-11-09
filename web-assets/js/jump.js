"use strict";
function setupJump() {
    function encodeUser(string) {
        return string.replaceAll("/", "⁄");
    }
    async function tryResolve(url) {
        try {
            const response = await fetch(url, { mode: "no-cors" });
            if (response.ok || response.type === "opaque") {
                return true;
            }
        }
        catch { }
        return false;
    }
    async function getJumpPath(input) {
        if (input === "") {
            return null;
        }
        if (/^[a-z]+-[0-9]+$/i.test(input)) {
            const issueLink = window.jumpStart + "/issues/" + encodeURIComponent(input.toUpperCase()) + ".html";
            if (await (tryResolve(issueLink))) {
                return issueLink;
            }
        }
        const userLink = window.jumpStart + "/users/" + encodeURIComponent(encodeUser(input.toLowerCase()).slice(0, 100)) + ".html";
        if (await (tryResolve(userLink))) {
            return userLink;
        }
        return null;
    }
    function soggy() {
        const images = document.getElementsByTagName("img");
        for (const image of images) {
            image.src = window.jumpStart + "/soggy.webp";
        }
    }
    const form = document.getElementById("jump");
    const inputBox = document.getElementById("jump-input");
    const button = document.getElementById("jump-submit");
    function updateEnabled() {
        const val = inputBox.value.trim();
        if (val === "soggy") {
            button.disabled = false;
            return;
        }
        const path = getJumpPath(val);
        path.then((result) => {
            button.disabled = (result === null);
        });
    }
    function jump() {
        const val = inputBox.value.trim();
        if (val === "soggy") {
            soggy();
            return;
        }
        const path = getJumpPath(val);
        path.then((result) => {
            if (result !== null) {
                location.href = result;
            }
        });
    }
    updateEnabled();
    inputBox.addEventListener("input", (e) => {
        updateEnabled();
    })
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        jump();
        inputBox.value = "";
    });
}

window.addEventListener("DOMContentLoaded", (e) => {
    if (window.jumpStart !== undefined) {
        setupJump();
    }
});
