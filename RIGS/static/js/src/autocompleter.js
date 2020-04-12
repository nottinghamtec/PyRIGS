$(document).ready(function() {
clearSelectionLabel = '(no selection)';

function changeSelectedValue(obj,pk,text,update_url) { //Pass in JQuery object and new parameters
    //console.log('Changing selected value');
    obj.find('option').remove();  //Remove all the available options
    obj.append(  //Add the new option
    	$("<option></option>")
		.attr("value",pk)
		.text(text)
		.data('update_url',update_url)
		);
	obj.selectpicker('render'); //Re-render the UI
	obj.selectpicker('refresh'); //Re-render the UI
	obj.selectpicker('val', pk); //Set the new value to be selected
	obj.change(); //Trigger the change function manually
}

function refreshUpdateHref(obj) {
	//console.log('Refreshing Update URL');
    targetObject = $('#'+obj.attr('id')+'-update');
	update_url = $('option:selected', obj).data('update_url');

	if (update_url=="") {  //Probably "clear selection" has been chosen
	//	console.log('Trying to disable');
		targetObject.attr('disabled', true);
	} else {
		targetObject.attr('href', update_url);
		targetObject.attr('disabled', false);
	}
}


$(".selectpicker").each(function() {

	var options = {
        ajax: {
            url: $(this).data('sourceurl'),
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
            array.push({
                        text: clearSelectionLabel,
                        value: '',
                        data:{
                        	update_url: '',
                        	subtext:''
                        }
                    });

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

    $(this).prepend($("<option></option>")
		.attr("value",'')
		.text(clearSelectionLabel)
		.data('update_url',''));  //Add "clear selection" option


	$(this).selectpicker().ajaxSelectPicker(options); //Initiaise selectPicker

	$(this).change(function(){ //on change, update the edit button href
	//	console.log('Selectbox Changed');
		refreshUpdateHref($(this));
	});

	refreshUpdateHref($(this)); //Ensure href is correct at the beginning

});

//When update/edit modal box submitted
   $('#modal').on('hide.bs.modal', function (e) {
        if (modaltarget != undefined && modalobject != "") {
        	//Update the selector with new values
        	changeSelectedValue($(modaltarget),modalobject[0]['pk'],modalobject[0]['fields']['name'],modalobject[0]['update_url']);
        }
    });

});
