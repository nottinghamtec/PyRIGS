$(document).ready((function(){var t;(t=document.createElement("input")).setAttribute("type","datetime-local"),("text"===t.type||navigator.userAgent.toLowerCase().indexOf("firefox")>-1)&&($("<link>").appendTo("head").attr({type:"text/css",rel:"stylesheet"}).attr("href",'{% static "css/flatpickr.css" %}'),$.when($.getScript('{% static "js/flatpickr.min.js" %}'),$.Deferred((function(t){$(t.resolve)}))).done((function(){$("input[type=datetime-local]").attr("type","text").flatpickr({dateFormat:"Y-m-dTH:m",enableTime:!0,altInput:!0,altFormat:"d/m/y H:m"})})))}));