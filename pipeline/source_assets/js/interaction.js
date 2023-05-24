function setupItemTable(items_json) {
    objectitems = JSON.parse(items_json)
    $.each(objectitems, function (key, val) {
        objectitems[key] = JSON.parse(val);
    })
    newitem = -1;
}

function escapeHtml(str) {
    return $('<div/>').text(str).html();
}

function updatePrices() {
    // individual rows
    var sum = 0;
    for (var pk in objectitems) {
        var fields = objectitems[pk].fields;
        var sub = fields.cost * fields.quantity;
        $('#item-' + pk + ' .sub-total').html(parseFloat(sub).toFixed(2)).data('subtotal', sub);

        sum += Number(sub);
    }

    $('#sumtotal').text(parseFloat(sum).toFixed(2));
    var vat = sum * Number($('#vat-rate').data('rate'));
    $('#vat').text(parseFloat(vat).toFixed(2));
    $('#total').text(parseFloat(sum + vat).toFixed(2));
}

function setupMDE(selector) {
    editor = new EasyMDE({
        autoDownloadFontAwesome: false,
        element: $(selector)[0],
        forceSync: true,
        toolbar: ["bold", "italic", "strikethrough", "|", "unordered-list", "ordered-list", "|", "link", "|", "preview", "guide"],
        status: true,
    });
    $(selector).data('mde_editor',editor);
}

$('#item-table').on('click', '.item-delete', function () {
    delete objectitems[$(this).data('pk')]
    $('#item-' + $(this).data('pk')).remove();
    updatePrices();
});

$('#item-table').on('click', '.item-add', function () {
    $('#item-form').data('pk', newitem);

    // Set the form values
    $('#item_name').val('');
    $('#item_description').val('');
    $('#item_quantity').val('');
    $('#item_cost').val('');

    $($(this).data('target')).modal('show');
});

$('#item-table').on('click', '.item-edit', function () {
    // set the pk as we will need this later
    var pk = $(this).data('pk');
    $('#item-form').data('pk', pk);

    // Set the form values
    var fields = objectitems[pk].fields;
    $('#item_name').val(fields.name);
    $('#item_description').val(fields.description);
    $('#item_quantity').val(fields.quantity);
    $('#item_cost').val(fields.cost);

    $($(this).data('target')).modal('show');
});

$('body').on('submit', '#item-form', function (e) {
    e.preventDefault();
    var pk = $(this).data('pk');
    $('#itemModal').modal('hide');

    var fields;
    if (pk == newitem--) {
        // Create the new data structure and add it on.
        fields = new Object();
        fields['name'] = $('#item_name').val()
        fields['description'] = $('#item_description').val();
        fields['cost'] = $('#item_cost').val();
        fields['quantity'] = $('#item_quantity').val();

        var order = 0;
        for (item in objectitems) {
            order++;
        }

        fields['order'] = order;

        objectitems[pk] = new Object();
        objectitems[pk]['fields'] = fields;

        // Add the new table
        $('#new-item-row').clone().attr('id', 'item-' + pk).data('pk', pk).appendTo('#item-table-body');
        $('#item-'+pk+' .item-delete, #item-'+pk+' .item-edit').data('pk', pk)
    } else {
        // Existing item
        // update data structure
        fields = objectitems[pk].fields;
        fields.name = $('#item_name').val()
        fields.description = $('#item_description').val();
        fields.cost = $('#item_cost').val();
        fields.quantity = $('#item_quantity').val();
        objectitems[pk].fields = fields;

    }
    // update the table
    $row = $('#item-' + pk);
    $row.find('.name').html(escapeHtml(fields.name));
    $row.find('.description').html(fields.description);
    $row.find('.cost').html(parseFloat(fields.cost).toFixed(2));
    $row.find('.quantity').html(fields.quantity);

    updatePrices();
});

$('body').on('submit', '.itemised_form', function (e) {
    $('#id_items_json').val(JSON.stringify(objectitems));
});

sortable("#item-table tbody")[0].addEventListener('sortupdate', function (e) {
    var items = e.detail.destination.items;
    for(var i in items) {
        objectitems[items[i].dataset.pk].fields.order = i;
    }
});
