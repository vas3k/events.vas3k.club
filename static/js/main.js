// External links styling
function stylizeExternalLinks() {
    let internal = location.host.replace("www.", "");
    internal = new RegExp(internal, "i");

    const links = [...document.getElementsByTagName("a")];

    links.forEach((link) => {
        if (internal.test(link.host) || !link.host) return;

        // open external link in new tab
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener");

        // insert favicon img
        const domain = link.host.split(":")[0];
        const img = document.createElement("img");
        img.src = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
        img.className = "link-favicon";
        link.insertBefore(img, link.firstChild);
    });
}

// Initialize emoji fallback
function initializePoorManEmoji() {
    let isApple = /iPad|iPhone|iPod|OS X/.test(navigator.userAgent) && !window.MSStream;
    if (!isApple && typeof twemoji !== 'undefined') {
        document.body = twemoji.parse(document.body, { base: "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/" });
    }
}

// Initialize countdown timers
function initCountdowns() {
    const timers = document.querySelectorAll('.countdown-timer:not(.initialized)');

    timers.forEach(timer => {
        // Mark as initialized so we don't bind twice if script runs again
        timer.classList.add('initialized');

        let totalSeconds = parseInt(timer.getAttribute('data-seconds')) || 0;

        // Find child elements relatively
        const daysEl = timer.querySelector('[data-unit="days"]');
        const hoursEl = timer.querySelector('[data-unit="hours"]');
        const minutesEl = timer.querySelector('[data-unit="minutes"]');
        const secondsEl = timer.querySelector('[data-unit="seconds"]');

        function update() {
            if (totalSeconds <= 0) {
                clearInterval(interval);
                location.reload();
                return;
            }

            const d = Math.floor(totalSeconds / 86400);
            const h = Math.floor((totalSeconds % 86400) / 3600);
            const m = Math.floor((totalSeconds % 3600) / 60);
            const s = totalSeconds % 60;

            if (daysEl) daysEl.textContent = d;
            if (hoursEl) hoursEl.textContent = h.toString().padStart(2, '0');
            if (minutesEl) minutesEl.textContent = m.toString().padStart(2, '0');
            if (secondsEl) secondsEl.textContent = s.toString().padStart(2, '0');

            totalSeconds--;
        }

        update();
        const interval = setInterval(update, 1000);
    });
}


// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    stylizeExternalLinks();
    initializePoorManEmoji();
    initCountdowns();
});
