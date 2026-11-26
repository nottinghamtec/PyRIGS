ready(function () {
    var root = document.getElementById('pat-export');
    if (!root) {
        return;
    }
    var assetsUrl = root.dataset.assetsUrl;
    var maxAssets = Number(root.dataset.maxAssets);

    function byId(id) {
        return document.getElementById(id);
    }

    var searchForm = byId('pat-search');
    var searchStatus = byId('pat-search-status');
    var searchResults = byId('pat-search-results');
    var addAll = byId('pat-add-all');
    var more = byId('pat-more');
    var selectedList = byId('pat-selected');
    var exportForm = byId('pat-export-form');
    var exportButton = byId('pat-export-button');
    var exportErrors = byId('pat-export-errors');
    var organisation = exportForm.elements.organisation;

    var selected = new Map();
    var found = [];
    var total = 0;
    var searchNumber = 0;
    var exporting = false;

    function element(tag, className, text) {
        var node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text !== undefined) {
            node.textContent = text;
        }
        return node;
    }

    function count(number, word) {
        return number + ' ' + word + (number === 1 ? '' : 's');
    }

    function resultBadge(passed) {
        if (passed === true) {
            return element('span', 'badge text-bg-success', 'Pass');
        }
        if (passed === false) {
            return element('span', 'badge text-bg-danger', 'Fail');
        }
        return element('span', 'badge text-bg-secondary', 'Unknown');
    }

    function heading(asset) {
        var line = element('div', 'd-flex flex-wrap align-items-center column-gap-2');
        if (asset.url) {
            var link = element('a', 'fw-bold', asset.id);
            link.href = asset.url;
            link.target = '_blank';
            line.appendChild(link);
        } else {
            line.appendChild(element('span', 'fw-bold', asset.id));
        }
        if (!asset.in_rigs) {
            line.appendChild(element('span', 'badge text-bg-info', 'Not in RIGS'));
        }
        var description = asset.description || asset.location;
        if (description) {
            line.appendChild(element('span', 'text-break', description));
        }
        return line;
    }

    function getJson(params) {
        return fetch(assetsUrl + '?' + params.toString(), {credentials: 'same-origin'}).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) {
                    throw new Error((data.errors || []).join(' '));
                }
                return data;
            });
        });
    }

    function searchParams() {
        return new URLSearchParams(new FormData(searchForm));
    }


    function search(offset) {
        var number = ++searchNumber;
        var params = searchParams();
        params.set('offset', offset);
        searchStatus.textContent = 'Searching…';
        addAll.disabled = true;
        more.disabled = true;
        getJson(params).then(function (data) {
            if (number !== searchNumber) {
                return;
            }
            if (!offset) {
                found = [];
                searchResults.replaceChildren();
                searchResults.scrollTop = 0;
            }
            total = data.total;
            data.assets.forEach(function (asset) {
                found.push(asset);
                searchResults.appendChild(searchRow(asset));
            });
            searchStatus.textContent = total ? count(total, 'asset') + ' with PAT results' : 'No PAT results match';
            more.classList.toggle('d-none', found.length >= total);
            more.disabled = false;
            refreshSearchButtons();
        }).catch(function (error) {
            if (number !== searchNumber) {
                return;
            }
            found = [];
            total = 0;
            searchResults.replaceChildren();
            more.classList.add('d-none');
            addAll.classList.add('d-none');
            searchStatus.textContent = error.message || 'The search failed, please try again';
        });
    }

    function searchRow(asset) {
        var row = element('div', 'list-group-item d-flex justify-content-between align-items-center gap-2');
        var info = element('div', 'flex-grow-1');
        info.appendChild(heading(asset));
        var latest = asset.tests[0];
        var summary = element('div', 'small text-body-secondary d-flex flex-wrap align-items-center column-gap-2');
        summary.appendChild(element('span', '', count(asset.tests.length, 'test') + ', latest ' + latest.tested));
        summary.appendChild(resultBadge(latest.passed));
        info.appendChild(summary);
        row.appendChild(info);
        var button = element('button', 'btn btn-sm flex-shrink-0');
        button.type = 'button';
        button.dataset.id = asset.id;
        button.addEventListener('click', function () {
            if (selected.has(asset.id)) {
                remove(asset.id);
            } else {
                add([asset]);
            }
        });
        row.appendChild(button);
        return row;
    }

    function refreshSearchButtons() {
        searchResults.querySelectorAll('button[data-id]').forEach(function (button) {
            var added = selected.has(button.dataset.id);
            button.className = 'btn btn-sm flex-shrink-0 ' + (added ? 'btn-outline-secondary' : 'btn-outline-success');
            button.textContent = added ? 'Remove' : 'Add';
            button.setAttribute('aria-label', (added ? 'Remove ' : 'Add ') + button.dataset.id);
        });
        var remaining = total > found.length || found.some(function (asset) { return !selected.has(asset.id); });
        addAll.classList.toggle('d-none', total < 2);
        addAll.disabled = !remaining;
        addAll.textContent = total > maxAssets ? 'Add the first ' + maxAssets : 'Add all ' + total;
    }


    function chosenKeys(item) {
        var keys = item.asset.tests.map(function (test) { return test.key; });
        if (item.mode === 'latest') {
            return keys.slice(0, 1);
        }
        if (item.mode === 'all') {
            return keys;
        }
        return keys.filter(function (key) { return item.chosen.has(key); });
    }

    function add(assets) {
        var skipped = 0;
        assets.forEach(function (asset) {
            if (selected.has(asset.id)) {
                return;
            }
            if (selected.size >= maxAssets) {
                skipped++;
                return;
            }
            var item = {asset: asset, mode: 'latest', chosen: new Set()};
            item.row = selectedRow(item);
            selected.set(asset.id, item);
            selectedList.appendChild(item.row);
        });
        refresh();
        if (skipped) {
            showErrors(['Up to ' + maxAssets + ' assets can be exported at once, so ' + count(skipped, 'asset') + ' weren’t added.']);
        }
    }

    function remove(id) {
        var item = selected.get(id);
        if (item) {
            item.row.remove();
            selected.delete(id);
            refresh();
        }
    }

    var rowNumber = 0;

    function selectedRow(item) {
        var asset = item.asset;
        var panelId = 'pat-tests-' + (++rowNumber);
        var row = element('li', 'list-group-item');

        var top = element('div', 'd-flex align-items-start gap-2');
        var toggle = element('button', 'btn btn-link btn-sm p-0');
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-controls', panelId);
        toggle.setAttribute('aria-label', 'Choose tests for ' + asset.id);
        toggle.appendChild(element('span', 'fas fa-chevron-right pat-export-chevron'));
        top.appendChild(toggle);
        var info = element('div', 'flex-grow-1');
        info.appendChild(heading(asset));
        top.appendChild(info);
        var close = element('button', 'btn-close flex-shrink-0');
        close.type = 'button';
        close.setAttribute('aria-label', 'Remove ' + asset.id);
        close.addEventListener('click', function () { remove(asset.id); });
        top.appendChild(close);
        row.appendChild(top);

        var controls = element('div', 'd-flex flex-wrap align-items-center gap-2 mt-1 ms-4');
        var mode = element('select', 'form-select form-select-sm w-auto');
        mode.setAttribute('aria-label', 'Tests to include for ' + asset.id);
        [['latest', 'Latest test only'], ['all', 'All tests'], ['custom', 'Chosen tests']].forEach(function (choice) {
            var option = element('option', '', choice[1]);
            option.value = choice[0];
            mode.appendChild(option);
        });
        controls.appendChild(mode);
        var included = element('span', 'small');
        controls.appendChild(included);
        row.appendChild(controls);

        var panel = element('div', 'pat-export-tests ms-4 mt-2 d-none');
        panel.id = panelId;
        var boxes = asset.tests.map(function (test) {
            var label = element('label', 'form-check d-flex gap-2 border-top py-1 mb-0');
            var box = element('input', 'form-check-input flex-shrink-0');
            box.type = 'checkbox';
            box.value = test.key;
            label.appendChild(box);
            var text = element('span', 'form-check-label small');
            var first = element('span', 'd-flex flex-wrap align-items-center column-gap-2');
            first.appendChild(element('span', '', test.tested));
            first.appendChild(resultBadge(test.passed));
            first.appendChild(element('span', '', test.program));
            text.appendChild(first);
            var second = [test.location, test.operator && 'by ' + test.operator, test.upload].filter(Boolean);
            text.appendChild(element('span', 'd-block text-body-secondary text-break', second.join(' · ')));
            label.appendChild(text);
            panel.appendChild(label);
            box.addEventListener('change', function () {
                var chosen = new Set(boxes.filter(function (other) { return other.checked; }).map(function (other) { return other.value; }));
                item.mode = 'custom';
                item.chosen = chosen;
                refresh();
            });
            return box;
        });
        row.appendChild(panel);

        function open(show) {
            panel.classList.toggle('d-none', !show);
            toggle.setAttribute('aria-expanded', show);
        }

        toggle.addEventListener('click', function () { open(panel.classList.contains('d-none')); });
        mode.addEventListener('change', function () {
            if (mode.value === 'custom') {
                item.chosen = new Set(chosenKeys(item));
                open(true);
            }
            item.mode = mode.value;
            refresh();
        });

        item.update = function () {
            var keys = new Set(chosenKeys(item));
            mode.value = item.mode;
            boxes.forEach(function (box) { box.checked = keys.has(box.value); });
            included.textContent = keys.size ? keys.size + ' of ' + count(asset.tests.length, 'test') : 'No tests chosen';
            included.className = 'small ' + (keys.size ? 'text-body-secondary' : 'text-danger fw-bold');
        };
        return row;
    }

    function refresh() {
        var tests = 0;
        var empty = [];
        selected.forEach(function (item, id) {
            item.update();
            var number = chosenKeys(item).length;
            tests += number;
            if (!number) {
                empty.push(id);
            }
        });
        byId('pat-selected-status').textContent = selected.size ? count(selected.size, 'asset') + ', ' + count(tests, 'test') : '';
        byId('pat-selected-empty').classList.toggle('d-none', selected.size > 0);
        byId('pat-bulk').classList.toggle('d-none', selected.size === 0);

        var missing = [];
        if (!selected.size) {
            missing.push('add at least one asset');
        } else if (empty.length) {
            missing.push('choose a test for ' + empty.slice(0, 3).join(', ') + (empty.length > 3 ? ' and others' : '') + ', or remove it');
        }
        if (!organisation.value) {
            missing.push('choose the client organisation');
        }
        byId('pat-export-hint').textContent = missing.length ? 'To export, ' + missing.join(' and ') + '.' : '';
        exportButton.disabled = exporting || missing.length > 0;
        exportErrors.classList.add('d-none');
        refreshSearchButtons();
    }


    function showOrganisation() {
        var preview = byId('pat-organisation-preview');
        var id = organisation.value;
        preview.classList.add('d-none');
        refresh();
        if (!id) {
            return;
        }
        fetch(root.dataset.organisationUrl + encodeURIComponent(id) + '/?fields=name,address,email,phone', {credentials: 'same-origin'})
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (organisation.value !== id) {
                    return;
                }
                var fields = data[0].fields;
                byId('pat-organisation-details').textContent = [fields.name, fields.address, fields.email, fields.phone].filter(Boolean).join('\n');
                preview.classList.remove('d-none');
            })
            .catch(function () {});
    }


    function showErrors(errors) {
        exportErrors.textContent = errors.join(' ');
        exportErrors.classList.remove('d-none');
    }

    function filenameFrom(response) {
        var header = response.headers.get('Content-Disposition') || '';
        var encoded = header.match(/filename\*=utf-8''([^;]+)/i);
        if (encoded) {
            return decodeURIComponent(encoded[1]);
        }
        var plain = header.match(/filename="([^"]+)"/i);
        return plain ? plain[1] : 'PAT records.pdf';
    }

    function download(blob, filename) {
        var link = element('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(function () { URL.revokeObjectURL(link.href); }, 60000);
    }

    function setExporting(busy) {
        exporting = busy;
        byId('pat-export-label').textContent = busy ? 'Generating PDF…' : 'Export PDF';
    }

    exportForm.addEventListener('submit', function (event) {
        event.preventDefault();
        if (exportButton.disabled) {
            return;
        }
        var data = new FormData(exportForm);
        data.set('selection', JSON.stringify(Array.from(selected, function (entry) {
            var item = entry[1];
            return {id: entry[0], mode: item.mode, tests: item.mode === 'custom' ? chosenKeys(item) : []};
        })));
        setExporting(true);
        refresh();
        var failed = 'The PDF couldn’t be generated. Try again, or export fewer assets at a time.';
        fetch(exportForm.action, {method: 'POST', body: data, credentials: 'same-origin'}).then(function (response) {
            if (response.ok && response.headers.get('Content-Type') === 'application/pdf') {
                return response.blob().then(function (blob) {
                    setExporting(false);
                    refresh();
                    download(blob, filenameFrom(response));
                });
            }
            return response.json().then(function (body) {
                throw body.errors;
            });
        }).catch(function (errors) {
            setExporting(false);
            refresh();
            showErrors(Array.isArray(errors) ? errors : [failed]);
        });
    });


    var debounce;
    searchForm.addEventListener('input', function (event) {
        if (!event.target.name) {
            return;
        }
        clearTimeout(debounce);
        debounce = setTimeout(function () { search(0); }, 300);
    });
    searchForm.addEventListener('submit', function (event) {
        event.preventDefault();
        clearTimeout(debounce);
        search(0);
    });
    byId('search_q').addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            clearTimeout(debounce);
            search(0);
        }
    });
    more.addEventListener('click', function () { search(found.length); });
    addAll.addEventListener('click', function () {
        var params = searchParams();
        params.set('all', '1');
        addAll.disabled = true;
        searchStatus.textContent = 'Adding…';
        getJson(params).then(function (data) {
            add(data.assets);
            searchStatus.textContent = count(data.total, 'asset') + ' with PAT results';
            if (data.total > data.assets.length) {
                showErrors(['Only the first ' + data.assets.length + ' matching assets were added.']);
            }
        }).catch(function () {
            searchStatus.textContent = 'Couldn’t add those assets, please try again';
            refreshSearchButtons();
        });
    });
    byId('pat-bulk').addEventListener('click', function (event) {
        var button = event.target.closest('[data-bulk]');
        if (button) {
            selected.forEach(function (item) { item.mode = button.dataset.bulk; });
            refresh();
        }
    });
    byId('pat-clear').addEventListener('click', function () {
        selected.clear();
        selectedList.replaceChildren();
        refresh();
    });
    organisation.addEventListener('change', showOrganisation);

    var preselected = JSON.parse(byId('pat-preselected').textContent);
    if (preselected.length) {
        var params = new URLSearchParams();
        preselected.forEach(function (id) { params.append('id', id); });
        getJson(params).then(function (data) { add(data.assets); });
    }
    showOrganisation();
    search(0);
});
