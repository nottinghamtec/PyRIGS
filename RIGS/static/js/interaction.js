function setupItemTable(items_json) {
    objectitems = JSON.parse(items_json)
    $.each(objectitems, function(key, val) {
        objectitems[key] = JSON.parse(val);
    })
    newitem = -1
}

function updatePrices() {
    // individual rows
    $('.item_row').each(function() {
        var pk = $(this).data('pk');
        var fields = objectitems[pk].fields;
        var sub = fields.cost * fields.quantity;
        $('#item-'+pk+' .sub-total').html(parseFloat(sub).toFixed(2)).data('subtotal', sub);
    })

	var sum = 0;

	$('.sub-total').each(function() {
		sum += Number($(this).data('subtotal'));
	});
	$('#sumtotal').text(parseFloat(sum).toFixed(2));
	var vat = sum * Number($('#vat-rate').data('rate'));
	$('#vat').text(parseFloat(vat).toFixed(2));
	$('#total').text(parseFloat(sum+vat).toFixed(2));
}

function addItemRow(url) {
	$tbody = $('#item-table tbody');
	$.ajax({
		url:url,
		success:function(r) {
			$tbody.append(r);
			updatePrices();
		}
	});
}

var csrftoken = $.cookie('csrftoken');
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

$('#item-table').on('click', '.item-delete', function() {
	delete objectitems[$(this).data('pk')]
    $('#item-'+$(this).data('pk')).remove();
    updatePrices();
});

$('#item-table').on('click', '.item-add', function() {
	$('#item-form').data('pk', newitem--);

    // Set the form values
    var fields = objectitems[pk].fields;
    $('#item_name').val('');
    $('#item_description').val('');
    $('#item_quantity').val('');
    $('#item_cost').val('');
});

$('#item-table').on('click', '.item-edit', function() {
    // set the pk as we will need this later
    var pk = $(this).data('pk');
	$('#item-form').data('pk', pk);

    // Set the form values
    var fields = objectitems[pk].fields;
    $('#item_name').val(fields.name);
    $('#item_description').val(fields.description);
    $('#item_quantity').val(fields.quantity);
    $('#item_cost').val(fields.cost);
});

$('body').on('submit','#item-form', function(e) {
	e.preventDefault();
    var pk = $(this).data('pk');
    $('#itemModal').modal('hide');

    if(pk < 0) {
        // @todo: Add new item
    } else {
        // update data structure
        var fields = objectitems[pk].fields;
        fields.name = $('#item_name').val()
        fields.description = $('#item_description').val();
        fields.cost = $('#item_cost').val();
        fields.quantity = $('#item_quantity').val();
        objectitems[pk].fields = fields;

        // update the table
        $row = $('#item-'+pk);
        $row.find('.name').html(fields.name);
        $row.find('.description').html(fields.description);
        $row.find('.cost').html(parseFloat(fields.cost).toFixed(2));
        $row.find('.quantity').html(fields.quantity);

        updatePrices();
    }
});

$('body').on('submit', '.itemised_form', function(e) {
    $('#id_items_json').val(JSON.stringify(objectitems));
});

// Return a helper with preserved width of cells
var fixHelper = function(e, ui) {
	ui.children().each(function() {
		$(this).width($(this).width());
	});
	return ui;
};

$("#item-table tbody").sortable({
	helper: fixHelper,
	update: function(e, ui) {
		info = $(this).sortable("toArray");
		itemorder = new Array();
		$.each(info, function(key, value) {
			pk = $('#'+value).data('pk');
			objectitems[pk].fields.order = key;
		});

	}
});