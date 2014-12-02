$(document).ready(function() {
	$(".autocomplete-json").each(function() {
		var field = $(this)
		$.getJSON($(this).data('valueurl'), function(json) {
			field.val(json[0]['fields']['name']);
		});
		var source = $(this).data('sourceurl');
		$(this).autocomplete({
			source: source,
			minLength: 3,
            delay: 500,
			focus: function(e, ui) {
				e.preventDefault();
				$(this).val(ui.item.label);
				
			},
			select: function(e, ui) {
				e.preventDefault();
				$(this).val(ui.item.label);
				$("#"+$(this).data('target')).val(ui.item.value)
            }
		});
        $(this).on('blur', function () {
            if ($(this).val() == "") {
                $("#" + $(this).data('target')).val('');
            }
        })
	});
});