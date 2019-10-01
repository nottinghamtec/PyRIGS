function filterAssetTable() {
    $.ajax({
        url : "/asset/filter/", // the endpoint
        type : "POST", // http method
        data : {
            form: $('#asset-filter-form').serialize()
        },
        traditional: true,

        success : function(data) {
            // console.log(data);
            $('#asset_table_body').html(data)
        },

        error : function(xhr) {console.log(xhr.status + ": " + xhr.responseText)}
    });
}

function updateAsset() {
    $.ajax({
        url : "/asset/update/", // the endpoint
        type : "POST", // http method
        data : {
            form: $('#asset_update_form').serialize()
        },
        traditional: true,

        success : function(data) {
            // console.log(data);
            window.location.href = data['url'];
        },

        error : function(xhr) {console.log(xhr.status + ": " + xhr.responseText)}
    });
}

function formAssetSearch() {
        $.ajax({
        url : "/asset/filter/", // the endpoint
        type : "POST", // http method
        data : {
            sender: 'asset_update',
            form: "csrfmiddlewaretoken=" + $('input[name=csrfmiddlewaretoken]').val() + "&asset_id=" + $('#parent_search').val()
        },
        traditional: true,

        success : function(data) {
            // console.log(data);
            $('#formAssetSearchResult').html(data);
            // window.location.href = data['url'];
        },

        error : function(xhr) {console.log(xhr.status + ": " + xhr.responseText)}
    });
}

function deleteAsset(asset_id) {
    $.ajax({
        url : "/asset/delete/", // the endpoint
        type : "POST", // http method
        data : {
            asset_id: asset_id
        },
        traditional: true,

        success : function(data) {
            // console.log(data);
            window.location.href = data['url'];
        },

        error : function(xhr) {console.log(xhr.status + ": " + xhr.responseText)}
    });
}