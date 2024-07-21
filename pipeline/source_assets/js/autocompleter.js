function changeSelectedValue(obj,pk,text,update_url) { //Pass in JQuery object and new parameters
    //console.log('Changing selected value');
    obj.find('option').remove();  //Remove all the available options
    obj[0].add(new Option(text, pk, true, true)); // Add new option
    //obj.selectpicker('val', pk); //Set the new value to be selected
    obj.selectpicker('refresh');
    obj.change(); //Trigger the change function manually
    //console.log(obj);
}

function refreshUpdateHref(obj) {
    //console.log('Refreshing Update URL');
    targetObject = $('#'+obj.attr('id')+'-update');
    update_url = $('option:selected', obj).data('update_url');

    if (update_url=="") {  //Probably "clear selection" has been chosen
        //console.log('Trying to disable');
        targetObject.removeAttr('href');
	    targetObject.addClass('disabled');
    } else {
	    targetObject.prop('href', update_url);
	    targetObject.removeClass('disabled');
    }
}

function initPicker(obj) {
	var options = {
        ajax: {
            url: obj.data('sourceurl'),
            type: 'GET',
            dataType: 'json',
            // Use "{{{q}}}" as a placeholder and Ajax Bootstrap Select will
            // automatically replace it with the value of the search query.
            data: {
                term: '{{{q}}}'
            }
        },
        locale: {
            emptyTitle: ''
        },
        clearOnEmpty:false,
        //log: 3,
        preprocessData: function (data) {
            var i, l = data.length, array = [];
            if (!obj.data('noclear')) {
                array.push({
                            text: clearSelectionLabel,
                            value: '',
                            data:{
                            	update_url: '',
                            	subtext:''
                            }
                        });
            }

            if (l) {
                for(i = 0; i < l; i++){
                    array.push($.extend(true, data[i], {
                        text: data[i]['label'],
                        value: data[i]['pk'],
                        data:{
                        	update_url: data[i]['update'],
                        	subtext:''
                        }
                    }));
                }
            }
            return array;
        }
    };
    //console.log(obj.data);
    if (!obj.data('noclear')) {
        obj.prepend($("<option></option>")
		    .attr("value",'')
		    .text(clearSelectionLabel)
		    .data('update_url',''));  //Add "clear selection" option
    }


	obj.selectpicker().ajaxSelectPicker(options); //Initiaise selectPicker
	obj.change(function(){ //on change, update the edit button href
		//console.log('Selectbox Changed');
		refreshUpdateHref(obj);
	});

	refreshUpdateHref(obj); //Ensure href is correct at the beginning
}

$(document).ready(function() {
    clearSelectionLabel = '(no selection)';

    $(".selectpicker").each(function(){initPicker($(this))});

    //When update/edit modal box submitted
   $('#modal').on('hide.bs.modal', function (e) {
        if (modaltarget != undefined && modalobject != "") {
        	//Update the selector with new values
        	changeSelectedValue($(modaltarget),modalobject[0]['pk'],modalobject[0]['fields']['name'],modalobject[0]['update_url']);
        }
    });
});
