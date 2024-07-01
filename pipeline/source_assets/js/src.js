Date.prototype.getISOString = function () {
        var yyyy = this.getFullYear().toString();
        var mm = (this.getMonth() + 1).toString(); // getMonth() is zero-based
        var dd = this.getDate().toString();
        return yyyy + '-' + (mm[1] ? mm : "0" + mm[0]) + '-' + (dd[1] ? dd : "0" + dd[0]); // padding
};
jQuery(document).ready(function () {
    jQuery(document).on('click', '.modal-href', function (e) {
        $link = jQuery(this);
        // Anti modal inception
        if ($link.parents('#modal').length == 0) {
            e.preventDefault();
            modaltarget = $link.data('target');
            modalobject = "";
            jQuery('#modal').load($link.attr('href'), function (e) {
                jQuery('#modal').modal();
            });
        }
    });
    var easter_egg = new Konami(function () {
        var s = document.createElement('script');
        s.type = 'text/javascript';
        document.body.appendChild(s);
        s.src = '/static/js/asteroids.min.js';
    });
    easter_egg.load();
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
$('.navbar-collapse').addClass('collapse');
