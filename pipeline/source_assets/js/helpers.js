// Helpers used by inline template scripts, so this is loaded in <head> (bundled with Bootstrap as jpop.js)
// Run fn once the DOM is ready
function ready(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

// Delegated event handler: on(document, 'click', '.selector', function (e) { this === matched element })
function on(root, type, selector, handler) {
    root.addEventListener(type, function (e) {
        var target = e.target instanceof Element ? e.target.closest(selector) : null;
        if (target && root.contains(target)) {
            handler.call(target, e);
        }
    });
}

// fetch() for endpoints that return HTML fragments: the X-Requested-With header makes the server
// render the ajax (modal) variant of a page, as jQuery's .load()/.post() used to
function ajaxFetch(url, options) {
    options = Object.assign({credentials: 'same-origin'}, options);
    options.headers = Object.assign({'X-Requested-With': 'XMLHttpRequest'}, options.headers);
    return fetch(url, options);
}

// Replace the contents of an element with an HTML string, executing any <script>s it contains
function setHtml(element, html) {
    element.innerHTML = html;
    element.querySelectorAll('script').forEach(function (old) {
        var script = document.createElement('script');
        Array.from(old.attributes).forEach(function (attr) { script.setAttribute(attr.name, attr.value); });
        script.text = old.text;
        old.replaceWith(script);
    });
    initTooltips(element);
    initPopovers(element);
    if (typeof initSelects === 'function') {
        initSelects(element);
    }
}

function initTooltips(root) {
    (root || document).querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        bootstrap.Tooltip.getOrCreateInstance(el);
    });
}

// Popovers may contain <ins>/<del> (used by the activity feed's diffs)
function popoverOptions() {
    var allowList = bootstrap.Tooltip.Default.allowList;
    allowList.ins = [];
    allowList.del = [];
    return {allowList: allowList};
}

function initPopovers(root) {
    (root || document).querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
        bootstrap.Popover.getOrCreateInstance(el, popoverOptions());
    });
}

// Load a URL into the shared modal and show it
function loadModal(url) {
    var modal = document.getElementById('modal');
    return ajaxFetch(url)
        .then(function (response) { return response.text(); })
        .then(function (html) {
            setHtml(modal, html);
            showModal(modal);
        });
}

function showModal(selectorOrElement) {
    var el = typeof selectorOrElement === 'string' ? document.querySelector(selectorOrElement) : selectorOrElement;
    bootstrap.Modal.getOrCreateInstance(el).show();
}

function hideModal(selectorOrElement) {
    var el = typeof selectorOrElement === 'string' ? document.querySelector(selectorOrElement) : selectorOrElement;
    var modal = bootstrap.Modal.getInstance(el);
    if (modal) {
        modal.hide();
    }
}

// Animated show/hide for form sections (replacing jQuery's slideDown/slideUp)
function resetSlide(el) {
    window.clearTimeout(el._slideTimer);
    ['height', 'overflow', 'transition', 'opacity'].forEach(function (p) { el.style.removeProperty(p); });
}

function slideUp(el, duration) {
    resetSlide(el);
    if (duration === 0 || isHidden(el)) {
        el.style.display = 'none';
        return;
    }
    el.style.overflow = 'hidden';
    el.style.height = el.offsetHeight + 'px';
    el.offsetHeight; // force reflow
    el.style.transition = 'height ' + duration + 'ms ease, opacity ' + duration + 'ms ease';
    el.style.height = '0';
    el.style.opacity = '0';
    el._slideTimer = window.setTimeout(function () {
        resetSlide(el);
        el.style.display = 'none';
    }, duration);
}

function slideDown(el, duration) {
    resetSlide(el);
    el.hidden = false;
    el.style.removeProperty('display');
    if (isHidden(el)) {
        el.style.display = 'block'; // not hidden by an inline style, so fall back to a block element
    }
    if (duration === 0) {
        return;
    }
    var height = el.scrollHeight;
    el.style.overflow = 'hidden';
    el.style.height = '0';
    el.style.opacity = '0';
    el.offsetHeight; // force reflow
    el.style.transition = 'height ' + duration + 'ms ease, opacity ' + duration + 'ms ease';
    el.style.height = height + 'px';
    el.style.opacity = '1';
    el._slideTimer = window.setTimeout(function () {
        resetSlide(el);
    }, duration);
}

function isHidden(el) {
    return getComputedStyle(el).display === 'none';
}
