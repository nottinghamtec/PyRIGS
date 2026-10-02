// Select widgets, built on Tom Select.
//  * <select class="ts-select" data-sourceurl="..."> loads its options remotely as the user types
//  * <select class="ts-select"> without a source URL is a plain (optionally multiple) select

var clearSelectionLabel = '(no selection)';

function changeSelectedValue(select, pk, text, update_url) { // Pass in the <select> and the new option's parameters
    var ts = select.tomselect;
    if (!ts) {
        return;
    }
    ts.clear(true);
    ts.clearOptions();
    ts.addOption({value: pk, text: text, update_url: update_url || ''});
    ts.setValue(pk, true);
    select.dispatchEvent(new Event('change', {bubbles: true})); // Trigger the change function manually
}

function selectedUpdateUrl(select) {
    var ts = select.tomselect;
    var value = ts.getValue();
    if (!value) {
        return '';
    }
    var option = ts.options[value];
    if (option && option.update_url !== undefined) {
        return option.update_url;
    }
    var domOption = select.querySelector('option[value="' + CSS.escape(value) + '"]');
    return domOption && domOption.dataset.update_url ? domOption.dataset.update_url : null;
}

function refreshUpdateHref(select) {
    var target = document.getElementById(select.id + '-update');
    if (!target) {
        return;
    }
    var update_url = selectedUpdateUrl(select);

    if (update_url === '') { // Nothing is selected
        target.removeAttribute('href');
        target.classList.add('disabled');
    } else if (update_url !== null) {
        target.setAttribute('href', update_url);
        target.classList.remove('disabled');
    }
}

function initPicker(select) {
    var noClear = 'noclear' in select.dataset;
    var multiple = select.multiple;
    var url = select.dataset.sourceurl;
    var plugins = [];
    if (multiple) {
        plugins.push('remove_button');
    } else if (!noClear) {
        plugins.push('clear_button');
    }

    var settings = {
        plugins: plugins,
        valueField: 'value',
        labelField: 'text',
        searchField: ['text'],
        allowEmptyOption: false,
        placeholder: select.dataset.noneSelectedText || '',
        maxOptions: null,
        hideSelected: false,
        closeAfterSelect: !multiple
    };

    if (url) {
        Object.assign(settings, {
            // Results come from the server so don't filter them locally
            score: function () { return function () { return 1; }; },
            shouldLoad: function (query) { return query.length > 0; },
            load: function (query, callback) {
                var separator = url.indexOf('?') === -1 ? '?' : '&';
                fetch(url + separator + 'q=' + encodeURIComponent(query), {credentials: 'same-origin'})
                    .then(function (response) { return response.json(); })
                    .then(function (data) {
                        callback(data.map(function (item) {
                            return {value: item.pk, text: item.text, update_url: item.update};
                        }));
                    })
                    .catch(function () { callback(); });
            }
        });
    }

    var update_urls = {};
    select.querySelectorAll('option[data-update_url]').forEach(function (option) {
        update_urls[option.value] = option.dataset.update_url;
    });

    var ts = new TomSelect(select, settings);
    Object.keys(update_urls).forEach(function (value) {
        if (ts.options[value]) {
            ts.options[value].update_url = update_urls[value];
        }
    });

    if (select.id && document.getElementById(select.id + '-update')) {
        select.addEventListener('change', function () { // on change, update the edit button href
            refreshUpdateHref(select);
        });
        refreshUpdateHref(select); // Ensure href is correct at the beginning
    }
}

function initSelects(root) {
    if (typeof TomSelect === 'undefined') {
        return;
    }
    (root || document).querySelectorAll('select.ts-select').forEach(function (select) {
        if (!select.tomselect) {
            initPicker(select);
        }
    });
}

ready(function () {
    initSelects();

    //When update/edit modal box submitted
    var modal = document.getElementById('modal');
    if (modal) {
        modal.addEventListener('hide.bs.modal', function () {
            if (typeof modaltarget !== 'undefined' && modaltarget && typeof modalobject !== 'undefined' && modalobject !== "") {
                //Update the selector with new values
                var select = document.querySelector(modaltarget);
                if (select) {
                    changeSelectedValue(select, modalobject[0]['pk'], modalobject[0]['fields']['name'], modalobject[0]['update_url']);
                }
            }
        });
    }
});
