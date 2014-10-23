function updatePrices() {
	var sum = 0;
	$('.sub-total').each(function() {
		sum += Number($(this).data('subtotal'));
	});
	$('#sumtotal').text(parseFloat(sum).toFixed(2));
	var vat = sum * Number($('#vat-rate').data('rate'));
	$('#vat').text(parseFloat(vat).toFixed(2));
	$('#total').text(parseFloat(sum+vat).toFixed(2));
}

function updateItemRow(pk) {
	$row = $('#item-'+pk)
	url = $row.data('url');
	$.ajax({
		url:url,
		success:function(r) {
			$row.replaceWith(r);
			updatePrices();
		}
	})
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
	var row = $('#item-'+$(this).data('pk'));
	$.ajax({
		type:"POST",
		url:$(this).data('url'),
		success:function(r) {
			row.remove();
			updatePrices();
		}
	});
});

$('#item-table').on('click', '.item-add', function() {
	$.ajax({
		url:$(this).data('url'),
		success:function(r) {
			$('#itemModal .modal-content').html(r);
			$('#item-table tbody').sortable('refresh');
		}
	});
});

$('#item-table').on('click', '.item-edit', function() {
	var url = $(this).data('url');
	$('#itemModal').data('pk', $(this).data('pk'));
	$.ajax({
		url:url,
		success:function(r) {
			$('#itemModal .modal-content').html(r);
		}
	})
});

$('#itemModal').on('hidden.bs.modal', function() {
	pk = $(this).data('pk');
	updateItemRow(pk);
	$('#itemModal .modal-content').html('');
})

$('body').on('submit','.item-form', function(e) {
	e.preventDefault();
	url = $(this).data('url');
	data = $(this).serialize();
	$.ajax({
		type:'POST',
		url:url,
		data:data,
		success: function(r) {
			$('#itemModal .modal-content').html(r)
		}
	})
})

function addItem(url) {
	$.get(url, function(r) {
		$('#item-table tbody').append(r);
	});
}

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
			itemorder[key] = pk;
		});
		data = JSON.stringify(itemorder);
		$.post($('#item-table').data('orderurl'), data);
	}
});