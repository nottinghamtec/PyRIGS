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
    var sectionTotal = 0;
    var sectionSubTotal = null;
    var inSection = false;
    var sectionCount = 0;
    var sectionHue = null;
    var setSubTotal = function (element, value) {
        if (element) {
            element.textContent = parseFloat(value).toFixed(2);
            element.dataset.subtotal = value;
        }
    };
    // Walk the rows in display order so sections total the items beneath them
    document.querySelectorAll('#item-table-body tr.item_row').forEach(function (row) {
        var item = objectitems[row.dataset.pk];
        if (!item) {
            return;
        }
        var fields = item.fields;
        var subTotal = row.querySelector('.sub-total');
        row.classList.toggle('in-section', inSection && !fields.is_section);
        if (fields.is_section) {
            // Each section gets its own hue; keep in step with Event.items_with_section_totals
            sectionHue = Math.round(sectionCount++ * 137.5) % 360;
            inSection = true;
            row.style.setProperty('--section-hue', sectionHue);
            setSubTotal(sectionSubTotal, sectionTotal);
            sectionSubTotal = subTotal;
            sectionTotal = 0;
            return;
        }
        if (inSection) {
            row.style.setProperty('--section-hue', sectionHue);
        } else {
            row.style.removeProperty('--section-hue');
        }
        var sub = fields.cost * fields.quantity;
        setSubTotal(subTotal, sub);
        sectionTotal += Number(sub);
        sum += Number(sub);
    });
    setSubTotal(sectionSubTotal, sectionTotal);

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
    // interaction.js is also loaded by forms without an item table
    if (!itemTable || !itemForm) {
        return;
    }
    var tableBody = document.getElementById('item-table-body');
    var itemModal = document.getElementById('itemModal');
    var editable = itemTable.hasAttribute('data-orderurl');
    var dirty = false;

    function field(id) {
        return document.getElementById(id);
    }

    function markDirty() {
        dirty = true;
    }

    // Whether the modal is editing a section header, which has no price or quantity
    var modalIsSection = false;

    function setSectionMode(isSection) {
        modalIsSection = isSection;
        field('item_name_label').textContent = isSection ? 'Section Name' : 'Item Name';
        field('item_name').placeholder = field('item_name_label').textContent;
        field('item_price_fields').hidden = isSection;
        field('item_quantity').required = !isSection;
        field('item_cost').required = !isSection;
    }

    // The table is the source of truth for ordering, so derive each item's order from it
    function renumber() {
        tableBody.querySelectorAll('tr.item_row').forEach(function (row, index) {
            if (objectitems[row.dataset.pk]) {
                objectitems[row.dataset.pk].fields.order = index;
            }
        });
    }

    // Render a description as markdown, as the server does, without running anything it contains
    function renderDescription(text) {
        var mde = field('item_description').mde_editor;
        var html = mde && mde.markdown ? mde.markdown(text) : escapeHtml(text).replace(/\n/g, '<br>');
        var body = new DOMParser().parseFromString(html, 'text/html').body;
        body.querySelectorAll('script').forEach(function (script) { script.remove(); });
        body.querySelectorAll('*').forEach(function (el) {
            Array.from(el.attributes).forEach(function (attr) {
                if (attr.name.indexOf('on') === 0) {
                    el.removeAttribute(attr.name);
                }
            });
        });
        return '<div class="markdown">' + body.innerHTML + '</div>';
    }

    // Copy an item's data into its table row. The description is only redrawn when asked, as it's rendered markdown.
    function renderRow(pk, includeDescription) {
        var fields = objectitems[pk].fields;
        var row = field('item-' + pk);
        row.querySelector('.name').textContent = fields.name;
        if (includeDescription) {
            // Rebuilt rather than updated in place, as editing a description inline replaces what's inside the box
            var box = row.querySelector('.item-description');
            var description = document.createElement('em');
            description.className = 'description';
            description.innerHTML = renderDescription(fields.description);
            box.replaceChildren(description);
        }
        row.querySelector('.cost').textContent = parseFloat(fields.cost).toFixed(2);
        row.querySelector('.quantity').textContent = fields.quantity;
        row.classList.toggle('section-row', !!fields.is_section);
    }

    // Add an empty row for pk, directly after afterRow (or at the end)
    function addRow(pk, afterRow) {
        var row = field('new-item-row').cloneNode(true);
        row.id = 'item-' + pk;
        row.dataset.pk = pk;
        row.querySelectorAll('.item-delete, .item-edit, .item-duplicate').forEach(function (button) {
            button.dataset.pk = pk;
        });
        if (afterRow) {
            afterRow.after(row);
        } else {
            tableBody.appendChild(row);
        }
        return row;
    }

    function openAddModal(isSection) {
        itemForm.dataset.pk = newitem;
        field('item_name').value = '';
        field('item_description').value = '';
        field('item_quantity').value = '';
        field('item_cost').value = '';
        setSectionMode(isSection === true);
        field('item-save-add').hidden = false;
        showModal(itemModal);
    }

    function openEditModal(pk) {
        itemForm.dataset.pk = pk;
        var fields = objectitems[pk].fields;
        field('item_name').value = fields.name;
        field('item_description').value = fields.description;
        field('item_quantity').value = fields.quantity;
        field('item_cost').value = fields.cost;
        setSectionMode(!!fields.is_section);
        field('item-save-add').hidden = true;
        showModal(itemModal);
    }

    function showUndo(message, undo) {
        var container = field('item-undo-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'item-undo-container';
            container.className = 'position-fixed bottom-0 start-50 translate-middle-x mb-3 d-flex flex-column gap-2';
            container.style.zIndex = 1080;
            document.body.appendChild(container);
        }
        var bar = document.createElement('div');
        bar.className = 'alert alert-dark d-flex align-items-center mb-0 shadow';
        bar.setAttribute('role', 'status');
        var text = document.createElement('span');
        text.textContent = message;
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-sm btn-link ms-3 p-0';
        button.textContent = 'Undo';
        bar.append(text, button);
        container.appendChild(bar);
        var timer = window.setTimeout(function () { bar.remove(); }, 8000);
        button.addEventListener('click', function () {
            window.clearTimeout(timer);
            bar.remove();
            undo();
        });
    }

    function deleteItem(pk) {
        var row = field('item-' + pk);
        var item = objectitems[pk];
        var next = row ? row.nextElementSibling : null;
        delete objectitems[pk];
        if (row) {
            row.remove();
        }
        updatePrices();
        markDirty();
        showUndo('Deleted "' + item.fields.name + '"', function () {
            objectitems[pk] = item;
            if (next && next.parentNode === tableBody) {
                tableBody.insertBefore(row, next);
            } else {
                tableBody.appendChild(row);
            }
                updatePrices();
        });
    }

    function duplicateItem(pk) {
        var newPk = newitem--;
        objectitems[newPk] = {fields: Object.assign({}, objectitems[pk].fields)};
        addRow(newPk, field('item-' + pk));
        renderRow(newPk, true);
        renumber();
        updatePrices();
        markDirty();
    }

    // Commits the inline edit that's currently open, if any, so submitting the form never misses it
    var activeInlineEdit = null;

    var pointerIsDown = false;
    window.addEventListener('pointerdown', function () { pointerIsDown = true; }, true);
    window.addEventListener('pointerup', function () { pointerIsDown = false; }, true);
    window.addEventListener('pointercancel', function () { pointerIsDown = false; }, true);

    // Run fn now, or once the current mouse press / tap has been released and its click dispatched
    function afterPointerRelease(fn) {
        if (!pointerIsDown) {
            fn();
            return;
        }
        window.addEventListener('pointerup', function () {
            window.setTimeout(fn, 0);
        }, {once: true});
    }

    // Click a name, price, quantity or description to edit it in place
    function startInlineEdit(target) {
        if (!editable || target.querySelector('input, textarea')) {
            return;
        }
        var pk = target.closest('tr.item_row').dataset.pk;
        var key = target.dataset.field;
        var fields = objectitems[pk].fields;
        // Match the size of what's being replaced so the table doesn't shift
        var width = target.offsetWidth;
        var height = target.offsetHeight;
        var isDescription = key === 'description';
        var input = document.createElement(isDescription ? 'textarea' : 'input');
        input.required = !isDescription;
        input.className = 'form-control form-control-sm inline-input';
        if (isDescription) {
            // Markdown source, which can run to several lines
            input.style.width = '100%';
            input.style.height = Math.max(height, 60) + 'px';
            input.placeholder = 'Description (markdown). Ctrl+Enter to save';
            input.addEventListener('input', function () {
                // Reset first, otherwise scrollHeight never drops below the current height and it only ever grows
                input.style.height = 'auto';
                input.style.height = Math.max(input.scrollHeight + 2, 60) + 'px';
            });
        } else {
            input.style.width = Math.max(width, 80) + 'px';
            input.style.height = height + 'px';
        }
        if (key === 'name') {
            input.type = 'text';
            input.maxLength = 255;
        } else if (key === 'quantity') {
            input.type = 'number';
            input.min = 1;
            input.step = 1;
        } else if (key === 'cost') {
            input.type = 'number';
            input.min = -99999999.99;
            input.max = 99999999.99;
            input.step = 0.01;
        }
        input.value = fields[key];
        target.textContent = '';
        target.appendChild(input);
        input.focus();
        if (isDescription) {
            input.setSelectionRange(input.value.length, input.value.length);
            input.dispatchEvent(new Event('input'));
        } else {
            input.select();
        }

        // Copy the input's value into the item. Safe to repeat, and the input may be left open for a moment
        // before the row is redrawn, so anything typed in that time must still count.
        function apply() {
            if (input.isConnected && input.checkValidity() && input.value !== String(fields[key])) {
                fields[key] = input.value;
                markDirty();
            }
        }
        var redrawQueued = false;
        function finish(save) {
            if (!input.isConnected) {
                return;
            }
            if (save) {
                if (!input.checkValidity()) {
                    input.reportValidity();
                    return;
                }
                apply();
            }
            if (redrawQueued) {
                return;
            }
            redrawQueued = true;
            // The edit is already in objectitems. Redrawing the row changes the page layout, which would move a
            // button (such as Save) out from under a click that caused this blur, so wait for the click to finish.
            afterPointerRelease(function () {
                // Take anything typed since, if the input was still open
                if (save) {
                    apply();
                }
                redrawQueued = false;
                if (input.isConnected) {
                    renderRow(pk, isDescription);
                    updatePrices();
                }
            });
        }
        activeInlineEdit = apply;
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && isDescription && !(e.ctrlKey || e.metaKey)) {
                // A new line
                return;
            }
            if (e.key === 'Enter') {
                // Don't submit the whole event form
                e.preventDefault();
                finish(true);
            } else if (e.key === 'Escape') {
                finish(false);
            }
        });
        input.addEventListener('blur', function () {
            finish(input.checkValidity());
        });
    }

    // Drag a row by its handle. The row itself moves as the pointer passes the middle of its neighbours,
    // so it always ends up where it was last shown, with no drop target to miss.
    function startRowDrag(row, startEvent) {
        var originalNext = row.nextElementSibling;
        var pointerY = startEvent.clientY;
        var frame = null;
        row.classList.add('dragging');
        document.body.classList.add('item-sorting');

        function reposition() {
            var before = null;
            var others = tableBody.querySelectorAll('tr.item_row');
            for (var i = 0; i < others.length; i++) {
                if (others[i] === row) {
                    continue;
                }
                var box = others[i].getBoundingClientRect();
                if (pointerY < box.top + box.height / 2) {
                    before = others[i];
                    break;
                }
            }
            if (before) {
                if (row.nextElementSibling !== before) {
                    tableBody.insertBefore(row, before);
                }
            } else if (tableBody.lastElementChild !== row) {
                tableBody.appendChild(row);
            }
        }

        // Keep scrolling while the pointer is held near the top or bottom of the window
        function autoScroll() {
            var edge = 60;
            if (pointerY < edge) {
                window.scrollBy(0, -Math.ceil((edge - pointerY) / 4));
            } else if (pointerY > window.innerHeight - edge) {
                window.scrollBy(0, Math.ceil((pointerY - (window.innerHeight - edge)) / 4));
            }
            reposition();
            frame = window.requestAnimationFrame(autoScroll);
        }

        function stop(commit) {
            window.cancelAnimationFrame(frame);
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', onUp);
            window.removeEventListener('pointercancel', onCancel);
            window.removeEventListener('keydown', onKey);
            row.classList.remove('dragging');
            document.body.classList.remove('item-sorting');
            if (commit) {
                renumber();
                updatePrices();
                markDirty();
            } else {
                tableBody.insertBefore(row, originalNext);
            }
        }

        function onMove(e) {
            pointerY = e.clientY;
            reposition();
        }
        function onUp() { stop(true); }
        function onCancel() { stop(false); }
        function onKey(e) {
            if (e.key === 'Escape') {
                stop(false);
            }
        }

        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
        window.addEventListener('pointercancel', onCancel);
        window.addEventListener('keydown', onKey);
        frame = window.requestAnimationFrame(autoScroll);
    }

    on(itemTable, 'pointerdown', '.drag-handle', function (e) {
        if (editable && e.button === 0) {
            e.preventDefault();
            startRowDrag(this.closest('tr.item_row'), e);
        }
    });

    itemModal.addEventListener('shown.bs.modal', function () {
        field('item_name').focus();
    });

    on(itemTable, 'click', '.item-delete', function () {
        deleteItem(this.dataset.pk);
    });

    on(itemTable, 'click', '.item-duplicate', function () {
        duplicateItem(this.dataset.pk);
    });

    on(itemTable, 'click', '.item-add', function () {
        openAddModal(false);
    });

    on(itemTable, 'click', '.item-add-section', function () {
        openAddModal(true);
    });

    on(itemTable, 'click', '.item-edit', function () {
        openEditModal(this.dataset.pk);
    });

    on(itemTable, 'click', '.inline-editable', function () {
        startInlineEdit(this);
    });

    on(document, 'submit', '#item-form', function (e) {
        e.preventDefault();
        var pk = this.dataset.pk;
        var addAnother = e.submitter && e.submitter.id === 'item-save-add';
        if (addAnother) {
            // Listen before hiding, as the event can fire immediately without transitions
            var addAnotherSection = modalIsSection;
            itemModal.addEventListener('hidden.bs.modal', function () {
                openAddModal(addAnotherSection);
            }, {once: true});
        }
        hideModal(itemModal);

        var fields;
        if (pk == newitem) {
            newitem--;
            // Create the new data structure and add it on.
            fields = {};
            objectitems[pk] = {fields: fields};
            addRow(pk);
        } else {
            fields = objectitems[pk].fields;
        }
        fields.name = field('item_name').value;
        fields.description = field('item_description').value;
        fields.is_section = modalIsSection;
        fields.cost = fields.is_section ? 0 : field('item_cost').value;
        fields.quantity = fields.is_section ? 0 : field('item_quantity').value;

        renumber();
        renderRow(pk, true);
        updatePrices();
        markDirty();
    });

    on(document, 'submit', '.itemised_form', function () {
        if (activeInlineEdit) {
            activeInlineEdit();
        }
        renumber();
        field('id_items_json').value = JSON.stringify(objectitems);
        dirty = false;
    });

    // Coming back to the page with the browser's back button can restore it exactly as it was left, including
    // item data from before it was saved, so load it fresh instead.
    window.addEventListener('pageshow', function (e) {
        if (e.persisted) {
            window.location.reload();
        }
    });

    // Warn before losing unsaved changes
    on(document, 'input', '.itemised_form', function (e) { if (e.isTrusted) { markDirty(); } });
    on(document, 'change', '.itemised_form', function (e) { if (e.isTrusted) { markDirty(); } });
    window.addEventListener('beforeunload', function (e) {
        if (dirty) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

})();
