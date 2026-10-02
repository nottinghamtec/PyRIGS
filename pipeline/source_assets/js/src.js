Date.prototype.getISOString = function () {
        var yyyy = this.getFullYear().toString();
        var mm = (this.getMonth() + 1).toString(); // getMonth() is zero-based
        var dd = this.getDate().toString();
        return yyyy + '-' + (mm[1] ? mm : "0" + mm[0]) + '-' + (dd[1] ? dd : "0" + dd[0]); // padding
};

ready(function () {
    // Links that load their target into the shared modal
    on(document, 'click', '.modal-href', function (e) {
        // Anti modal inception
        if (!this.closest('#modal')) {
            e.preventDefault();
            modaltarget = this.dataset.selectTarget;
            modalobject = "";
            loadModal(this.getAttribute('href'));
        }
    });

    // Forms inside the modal are submitted over AJAX and the response replaces the modal contents
    on(document, 'submit', '#modal form', function (e) {
        e.preventDefault();
        var form = this;
        ajaxFetch(form.getAttribute('action') || window.location.href, {
            method: 'POST',
            body: new FormData(form)
        }).then(function (response) { return response.text(); })
          .then(function (html) { setHtml(document.getElementById('modal'), html); });
    });

    var easter_egg = new Konami(function () {
        var s = document.createElement('script');
        s.type = 'text/javascript';
        document.body.appendChild(s);
        s.src = '/static/js/asteroids.min.js';
    });
    easter_egg.load();

    initTooltips();
    initPopovers();
    document.querySelectorAll('.navbar-collapse').forEach(function (el) { el.classList.add('collapse'); });
});

//CTRL-Enter form submission
document.body.addEventListener('keydown', function(e) {
    if(e.keyCode == 13 && (e.metaKey || e.ctrlKey)) {
        var target = e.target;
        if(target.form) {
            target.form.submit();
        }
    }
});
