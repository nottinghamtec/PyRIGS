function setupItemTable(items_json) {
    objectitems = JSON.parse(items_json)
    Object.keys(objectitems).forEach(function (key) {
        objectitems[key] = JSON.parse(objectitems[key]);
    });
    newitem = -1;
}

function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function updatePrices() {
    // individual rows
    var sum = 0;
    for (var pk in objectitems) {
        var fields = objectitems[pk].fields;
        var sub = fields.cost * fields.quantity;
        var subTotal = document.querySelector('#item-' + pk + ' .sub-total');
        if (subTotal) {
            subTotal.textContent = parseFloat(sub).toFixed(2);
            subTotal.dataset.subtotal = sub;
        }

        sum += Number(sub);
    }

    document.getElementById('sumtotal').textContent = parseFloat(sum).toFixed(2);
    var vat = sum * Number(document.getElementById('vat-rate').dataset.rate);
    document.getElementById('vat').textContent = parseFloat(vat).toFixed(2);
    document.getElementById('total').textContent = parseFloat(sum + vat).toFixed(2);
}

function setupMDE(selector) {
    var element = document.querySelector(selector);
    editor = new EasyMDE({
        autoDownloadFontAwesome: false,
        element: element,
        forceSync: true,
        toolbar: ["bold", "italic", "strikethrough", "|", "unordered-list", "ordered-list", "|", "link", "|", "preview", "guide"],
        status: true,
    });
    element.mde_editor = editor;
}

(function () {
    var itemTable = document.getElementById('item-table');
    var itemForm = document.getElementById('item-form');

    function field(id) {
        return document.getElementById(id);
    }

    if (itemTable) {
        on(itemTable, 'click', '.item-delete', function () {
            delete objectitems[this.dataset.pk];
            var row = document.getElementById('item-' + this.dataset.pk);
            if (row) {
                row.remove();
            }
            updatePrices();
        });

        on(itemTable, 'click', '.item-add', function () {
            itemForm.dataset.pk = newitem;

            // Set the form values
            field('item_name').value = '';
            field('item_description').value = '';
            field('item_quantity').value = '';
            field('item_cost').value = '';

            showModal(this.dataset.modalTarget);
        });

        on(itemTable, 'click', '.item-edit', function () {
            // set the pk as we will need this later
            var pk = this.dataset.pk;
            itemForm.dataset.pk = pk;

            // Set the form values
            var fields = objectitems[pk].fields;
            field('item_name').value = fields.name;
            field('item_description').value = fields.description;
            field('item_quantity').value = fields.quantity;
            field('item_cost').value = fields.cost;

            showModal(this.dataset.modalTarget);
        });
    }

    on(document, 'submit', '#item-form', function (e) {
        e.preventDefault();
        var pk = this.dataset.pk;
        hideModal('#itemModal');

        var fields;
        if (pk == newitem--) {
            // Create the new data structure and add it on.
            fields = new Object();
            fields['name'] = field('item_name').value;
            fields['description'] = field('item_description').value;
            fields['cost'] = field('item_cost').value;
            fields['quantity'] = field('item_quantity').value;

            var order = 0;
            for (var item in objectitems) {
                order++;
            }

            fields['order'] = order;

            objectitems[pk] = new Object();
            objectitems[pk]['fields'] = fields;

            // Add the new table row
            var row = field('new-item-row').cloneNode(true);
            row.id = 'item-' + pk;
            row.dataset.pk = pk;
            field('item-table-body').appendChild(row);
            row.querySelectorAll('.item-delete, .item-edit').forEach(function (button) {
                button.dataset.pk = pk;
            });
        } else {
            // Existing item
            // update data structure
            fields = objectitems[pk].fields;
            fields.name = field('item_name').value;
            fields.description = field('item_description').value;
            fields.cost = field('item_cost').value;
            fields.quantity = field('item_quantity').value;
            objectitems[pk].fields = fields;
        }
        // update the table
        var tableRow = field('item-' + pk);
        tableRow.querySelector('.name').innerHTML = escapeHtml(fields.name);
        tableRow.querySelector('.description').innerHTML = fields.description;
        tableRow.querySelector('.cost').innerHTML = parseFloat(fields.cost).toFixed(2);
        tableRow.querySelector('.quantity').innerHTML = fields.quantity;

        updatePrices();
    });

    on(document, 'submit', '.itemised_form', function () {
        field('id_items_json').value = JSON.stringify(objectitems);
    });

    if (itemTable && typeof sortable === 'function') {
        var sortables = sortable("#item-table tbody");
        if (sortables.length) {
            sortables[0].addEventListener('sortupdate', function (e) {
                var items = e.detail.destination.items;
                for (var i in items) {
                    objectitems[items[i].dataset.pk].fields.order = i;
                }
            });
        }
    }
})();
