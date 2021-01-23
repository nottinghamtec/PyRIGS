/*!
 * Ajax Bootstrap Select
 *
 * Extends existing [Bootstrap Select] implementations by adding the ability to search via AJAX requests as you type. Originally for CROSCON.
 *
 * @version 1.4.5
 * @author Adam Heim - https://github.com/truckingsim
 * @link https://github.com/truckingsim/Ajax-Bootstrap-Select
 * @copyright 2019 Adam Heim
 * @license Released under the MIT license.
 *
 * Contributors:
 *   Mark Carver - https://github.com/markcarver
 *
 * Last build: 2019-04-23 12:18:55 PM EDT
 */
!function(t,e){var i=function(i,s){var o,l,n=this;s=s||{},this.$element=t(i),this.options=t.extend(!0,{},t.fn.ajaxSelectPicker.defaults,s),this.LOG_ERROR=1,this.LOG_WARNING=2,this.LOG_INFO=3,this.LOG_DEBUG=4,this.lastRequest=!1,this.previousQuery="",this.query="",this.request=!1;var a=[{from:"ajaxResultsPreHook",to:"preprocessData"},{from:"ajaxSearchUrl",to:{ajax:{url:"{{{value}}}"}}},{from:"ajaxOptions",to:"ajax"},{from:"debug",to:function(e){var i={};i.log=Boolean(n.options[e.from])?n.LOG_DEBUG:0,n.options=t.extend(!0,{},n.options,i),delete n.options[e.from],n.log(n.LOG_WARNING,'Deprecated option "'+e.from+'". Update code to use:',i)}},{from:"mixWithCurrents",to:"preserveSelected"},{from:"placeHolderOption",to:{locale:{emptyTitle:"{{{value}}}"}}}];a.length&&t.map(a,(function(e){if(n.options[e.from])if(t.isPlainObject(e.to))n.replaceValue(e.to,"{{{value}}}",n.options[e.from]),n.options=t.extend(!0,{},n.options,e.to),n.log(n.LOG_WARNING,'Deprecated option "'+e.from+'". Update code to use:',e.to),delete n.options[e.from];else if(t.isFunction(e.to))e.to.apply(n,[e]);else{var i={};i[e.to]=n.options[e.from],n.options=t.extend(!0,{},n.options,i),n.log(n.LOG_WARNING,'Deprecated option "'+e.from+'". Update code to use:',i),delete n.options[e.from]}}));var r=this.$element.data();r.searchUrl&&(n.log(n.LOG_WARNING,'Deprecated attribute name: "data-search-url". Update markup to use: \' data-abs-ajax-url="'+r.searchUrl+"\" '"),this.options.ajax.url=r.searchUrl);var p=function(t,e){return e.toLowerCase()},c=function(t,e,i){var s=[].concat(t),o=s.length,l=i||{};if(o){var n=s.shift();l[n]=c(s,e,l[n])}return o?l:e},h=Object.keys(r).filter(/./.test.bind(new RegExp("^abs[A-Z]")));if(h.length){var u={},g=["locale"];for(o=0,l=h.length;o<l;o++){var d=h[o].replace(/^abs([A-Z])/,p).replace(/([A-Z])/g,"-$1").toLowerCase(),f=d.split("-");if(f[0]&&f.length>1&&-1!==g.indexOf(f[0])){for(var v=[f.shift()],y="",O=0;O<f.length;O++)y+=0===O?f[O]:f[O].charAt(0).toUpperCase()+f[O].slice(1);v.push(y),f=v}this.log(this.LOG_DEBUG,'Processing data attribute "data-abs-'+d+'":',r[h[o]]),c(f,r[h[o]],u)}this.options=t.extend(!0,{},this.options,u),this.log(this.LOG_DEBUG,"Merged in the data attribute options: ",u,this.options)}if(this.selectpicker=r.selectpicker,!this.selectpicker)return this.log(this.LOG_ERROR,"Cannot instantiate an AjaxBootstrapSelect instance without selectpicker first being initialized!"),null;if(!this.options.ajax.url)return this.log(this.LOG_ERROR,'Option "ajax.url" must be set! Options:',this.options),null;if(this.locale=t.extend(!0,{},t.fn.ajaxSelectPicker.locale),this.options.langCode=this.options.langCode||e.navigator.userLanguage||e.navigator.language||"en",!this.locale[this.options.langCode]){var m=this.options.langCode;this.options.langCode="en";var G=m.split("-");for(o=0,l=G.length;o<l;o++){var k=G.join("-");if(k.length&&this.locale[k]){this.options.langCode=k;break}G.pop()}this.log(this.LOG_WARNING,'Unknown langCode option: "'+m+'". Using the following langCode instead: "'+this.options.langCode+'".')}this.locale[this.options.langCode]=t.extend(!0,{},this.locale[this.options.langCode],this.options.locale),this.list=new e.AjaxBootstrapSelectList(this),this.list.refresh(),setTimeout((function(){n.init()}),500)};i.prototype.init=function(){var i,s=this;this.options.preserveSelected&&this.selectpicker.$menu.off("click",".actions-btn").on("click",".actions-btn",(function(e){s.selectpicker.options.liveSearch?s.selectpicker.$searchbox.focus():s.selectpicker.$button.focus(),e.preventDefault(),e.stopPropagation(),t(this).is(".bs-select-all")?(null===s.selectpicker.$lis&&(s.selectpicker.$lis=s.selectpicker.$menu.find("li")),s.$element.find("option:enabled").prop("selected",!0),t(s.selectpicker.$lis).not(".disabled").addClass("selected"),s.selectpicker.render()):(null===s.selectpicker.$lis&&(s.selectpicker.$lis=s.selectpicker.$menu.find("li")),s.$element.find("option:enabled").prop("selected",!1),t(s.selectpicker.$lis).not(".disabled").removeClass("selected"),s.selectpicker.render()),s.selectpicker.$element.change()})),this.selectpicker.$searchbox.attr("placeholder",this.t("searchPlaceholder")).off("input propertychange"),this.selectpicker.$searchbox.on(this.options.bindEvent,(function(o){var l=s.selectpicker.$searchbox.val();if(s.log(s.LOG_DEBUG,'Bind event fired: "'+s.options.bindEvent+'", keyCode:',o.keyCode,o),s.options.cache||(s.options.ignoredKeys[13]="enter"),s.options.ignoredKeys[o.keyCode])s.log(s.LOG_DEBUG,"Key ignored.");else if(clearTimeout(i),l.length||(s.options.clearOnEmpty&&s.list.destroy(),s.options.emptyRequest))if(l.length<s.options.minLength)s.list.setStatus(s.t("statusTooShort"));else{if(s.previousQuery=s.query,s.query=l,s.options.cache&&13!==o.keyCode){var n=s.list.cacheGet(s.query);if(n)return s.list.setStatus(n.length?"":s.t("statusNoResults")),s.list.replaceOptions(n),void s.log(s.LOG_INFO,"Rebuilt options from cached data.")}i=setTimeout((function(){s.lastRequest&&s.lastRequest.jqXHR&&t.isFunction(s.lastRequest.jqXHR.abort)&&s.lastRequest.jqXHR.abort(),s.request=new e.AjaxBootstrapSelectRequest(s),s.request.jqXHR.always((function(){s.lastRequest=s.request,s.request=!1}))}),s.options.requestDelay||300)}}))},i.prototype.log=function(t,i){if(e.console&&this.options.log){if("number"!=typeof this.options.log)switch("string"==typeof this.options.log&&(this.options.log=this.options.log.toLowerCase()),this.options.log){case!0:case"debug":this.options.log=this.LOG_DEBUG;break;case"info":this.options.log=this.LOG_INFO;break;case"warn":case"warning":this.options.log=this.LOG_WARNING;break;default:case!1:case"error":this.options.log=this.LOG_ERROR}if(t<=this.options.log){var s=[].slice.apply(arguments,[2]);switch(t){case this.LOG_DEBUG:t="debug";break;case this.LOG_INFO:t="info";break;case this.LOG_WARNING:t="warn";break;default:case this.LOG_ERROR:t="error"}var o="["+t.toUpperCase()+"] AjaxBootstrapSelect:";"string"==typeof i?s.unshift(o+" "+i):(s.unshift(i),s.unshift(o)),e.console[t].apply(e.console,s)}}},i.prototype.replaceValue=function(e,i,s,o){var l=this;o=t.extend({recursive:!0,depth:!1,limit:!1},o),t.each(e,(function(n,a){if(!1!==o.limit&&"number"==typeof o.limit&&o.limit<=0)return!1;t.isArray(e[n])||t.isPlainObject(e[n])?(o.recursive&&!1===o.depth||o.recursive&&"number"==typeof o.depth&&o.depth>0)&&l.replaceValue(e[n],i,s,o):a===i&&(!1!==o.limit&&"number"==typeof o.limit&&o.limit--,e[n]=s)}))},i.prototype.t=function(t,e){return e=e||this.options.langCode,this.locale[e]&&this.locale[e].hasOwnProperty(t)?this.locale[e][t]:(this.log(this.LOG_WARNING,"Unknown translation key:",t),t)},e.AjaxBootstrapSelect=e.AjaxBootstrapSelect||i;var s=function(e){var i=this;this.$status=t(e.options.templates.status).hide().appendTo(e.selectpicker.$menu);var s=e.t("statusInitialized");s&&s.length&&this.setStatus(s),this.cache={},this.plugin=e,this.selected=[],this.title=null,this.selectedTextFormat=e.selectpicker.options.selectedTextFormat;var o=[];e.$element.find("option").each((function(){var i=t(this),s=i.attr("value");o.push({value:s,text:i.text(),class:i.attr("class")||"",data:i.data()||{},preserved:e.options.preserveSelected,selected:!!i.attr("selected")})})),this.cacheSet("",o),e.options.preserveSelected&&(i.selected=o,e.$element.on("change.abs.preserveSelected",(function(s){var o=e.$element.find(":selected");i.selected=[],e.selectpicker.multiple||(o=o.last()),o.each((function(){var e=t(this),s=e.attr("value");i.selected.push({value:s,text:e.text(),class:e.attr("class")||"",data:e.data()||{},preserved:!0,selected:!0})})),i.replaceOptions(i.cacheGet(i.plugin.query))})))};s.prototype.build=function(e){var i,s,o=e.length,l=t("<select/>"),n=t("<optgroup/>").attr("label",this.plugin.t("currentlySelected"));for(this.plugin.log(this.plugin.LOG_DEBUG,"Building the select list options from data:",e),s=0;s<o;s++){var a=e[s],r=t("<option/>").appendTo(a.preserved?n:l);if(a.hasOwnProperty("divider"))r.attr("data-divider","true");else for(i in r.val(a.value).text(a.text).attr("title",a.text),a.class.length&&r.attr("class",a.class),a.disabled&&r.attr("disabled",!0),a.selected&&!this.plugin.selectpicker.multiple&&l.find(":selected").prop("selected",!1),a.selected&&r.attr("selected",!0),a.data)a.data.hasOwnProperty(i)&&r.attr("data-"+i,a.data[i])}n.find("option").length&&n["before"===this.plugin.options.preserveSelectedPosition?"prependTo":"appendTo"](l);var p=l.html();return this.plugin.log(this.plugin.LOG_DEBUG,p),p},s.prototype.cacheGet=function(t,e){var i=this.cache[t]||e;return this.plugin.log(this.LOG_DEBUG,"Retrieving cache:",t,i),i},s.prototype.cacheSet=function(t,e){this.cache[t]=e,this.plugin.log(this.LOG_DEBUG,"Saving to cache:",t,e)},s.prototype.destroy=function(){this.replaceOptions(),this.plugin.list.setStatus(),this.plugin.log(this.plugin.LOG_DEBUG,"Destroyed select list.")},s.prototype.refresh=function(t){this.plugin.selectpicker.$menu.css("minHeight",0),this.plugin.selectpicker.$menu.find("> .inner").css("minHeight",0);var e=this.plugin.t("emptyTitle");!this.plugin.$element.find("option").length&&e&&e.length?this.setTitle(e):(this.title||"static"!==this.selectedTextFormat&&this.selectedTextFormat!==this.plugin.selectpicker.options.selectedTextFormat)&&this.restoreTitle(),this.plugin.selectpicker.refresh(),this.plugin.selectpicker.findLis(),t&&(this.plugin.log(this.plugin.LOG_DEBUG,"Triggering Change"),this.plugin.$element.trigger("change.$")),this.plugin.log(this.plugin.LOG_DEBUG,"Refreshed select list.")},s.prototype.replaceOptions=function(t){var e,i,s,o="",l=[],n=[],a=[];if(t=t||[],this.selected&&this.selected.length){for(this.plugin.log(this.plugin.LOG_INFO,"Processing preserved selections:",this.selected),i=(n=[].concat(this.selected,t)).length,e=0;e<i;e++)(s=n[e]).hasOwnProperty("value")&&-1===a.indexOf(s.value+"")?(a.push(s.value+""),l.push(s)):this.plugin.log(this.plugin.LOG_DEBUG,"Duplicate item found, ignoring.");t=l}t.length&&(o=this.plugin.list.build(t)),this.plugin.$element.html(o),this.refresh(),this.plugin.log(this.plugin.LOG_DEBUG,"Replaced options with data:",t)},s.prototype.restore=function(){var t=this.plugin.list.cacheGet(this.plugin.previousQuery);return t&&this.plugin.list.replaceOptions(t)&&this.plugin.log(this.plugin.LOG_DEBUG,"Restored select list to the previous query: ",this.plugin.previousQuery),this.plugin.log(this.plugin.LOG_DEBUG,"Unable to restore select list to the previous query:",this.plugin.previousQuery),!1},s.prototype.restoreTitle=function(){this.plugin.request||(this.plugin.selectpicker.options.selectedTextFormat=this.selectedTextFormat,this.title?this.plugin.$element.attr("title",this.title):this.plugin.$element.removeAttr("title"),this.title=null)},s.prototype.setTitle=function(t){this.plugin.request||(this.title=this.plugin.$element.attr("title"),this.plugin.selectpicker.options.selectedTextFormat="static",this.plugin.$element.attr("title",t))},s.prototype.setStatus=function(t){(t=t||"").length?this.$status.html(t).show():this.$status.html("").hide()},e.AjaxBootstrapSelectList=e.AjaxBootstrapSelectList||s;var o=function(e){var i,s=this,o=function(t){return function(){s.plugin.log(s.plugin.LOG_INFO,"Invoking AjaxBootstrapSelectRequest."+t+" callback:",arguments),s[t].apply(s,arguments),s.callbacks[t]&&(s.plugin.log(s.plugin.LOG_INFO,"Invoking ajax."+t+" callback:",arguments),s.callbacks[t].apply(s,arguments))}},l=["beforeSend","success","error","complete"],n=l.length;for(this.plugin=e,this.options=t.extend(!0,{},e.options.ajax),this.callbacks={},i=0;i<n;i++){var a=l[i];this.options[a]&&t.isFunction(this.options[a])&&(this.callbacks[a]=this.options[a]),this.options[a]=o(a)}this.options.data&&t.isFunction(this.options.data)&&(this.options.data=this.options.data.apply(this)||{q:"{{{q}}}"}),this.plugin.replaceValue(this.options.data,"{{{q}}}",this.plugin.query),this.options.url&&t.isFunction(this.options.url)&&(this.options.url=this.options.url.apply(this)),this.jqXHR=t.ajax(this.options)};o.prototype.beforeSend=function(t){this.plugin.list.destroy(),this.plugin.list.setStatus(this.plugin.t("statusSearching"))},o.prototype.complete=function(t,e){if("abort"!==e){var i=this.plugin.list.cacheGet(this.plugin.query);if(i){if(!i.length)return this.plugin.list.destroy(),this.plugin.list.setStatus(this.plugin.t("statusNoResults")),void this.plugin.log(this.plugin.LOG_INFO,"No results were returned.");this.plugin.list.setStatus()}this.plugin.list.refresh(!0)}},o.prototype.error=function(t,e,i){"abort"!==e&&(this.plugin.list.cacheSet(this.plugin.query),this.plugin.options.clearOnError&&this.plugin.list.destroy(),this.plugin.list.setStatus(this.plugin.t("errorText")),this.plugin.options.restoreOnError&&(this.plugin.list.restore(),this.plugin.list.setStatus()))},o.prototype.process=function(e){var i,s,o,l,n,a,r=[],p=[];if(this.plugin.log(this.plugin.LOG_INFO,"Processing raw data for:",this.plugin.query,e),n=e,t.isFunction(this.plugin.options.preprocessData)&&(this.plugin.log(this.plugin.LOG_DEBUG,"Invoking preprocessData callback:",this.plugin.options.processData),null!=(o=this.plugin.options.preprocessData.apply(this,[n]))&&!1!==o&&(n=o)),!t.isArray(n))return this.plugin.log(this.plugin.LOG_ERROR,'The data returned is not an Array. Use the "preprocessData" callback option to parse the results and construct a proper array for this plugin.',n),!1;for(s=n.length,i=0;i<s;i++)l=n[i],this.plugin.log(this.plugin.LOG_DEBUG,"Processing item:",l),t.isPlainObject(l)&&(l.hasOwnProperty("divider")||l.hasOwnProperty("data")&&t.isPlainObject(l.data)&&l.data.divider?(this.plugin.log(this.plugin.LOG_DEBUG,"Item is a divider, ignoring provided data."),r.push({divider:!0})):l.hasOwnProperty("value")?-1===p.indexOf(l.value+"")?(p.push(l.value+""),l=t.extend({text:l.value,class:"",data:{},disabled:!1,selected:!1},l),r.push(l)):this.plugin.log(this.plugin.LOG_DEBUG,"Duplicate item found, ignoring."):this.plugin.log(this.plugin.LOG_DEBUG,'Data item must have a "value" property, skipping.'));if(a=[].concat(r),t.isFunction(this.plugin.options.processData)&&(this.plugin.log(this.plugin.LOG_DEBUG,"Invoking processData callback:",this.plugin.options.processData),null!=(o=this.plugin.options.processData.apply(this,[a]))&&!1!==o)){if(!t.isArray(o))return this.plugin.log(this.plugin.LOG_ERROR,"The processData callback did not return an array.",o),!1;a=o}return this.plugin.list.cacheSet(this.plugin.query,a),this.plugin.log(this.plugin.LOG_INFO,"Processed data:",a),a},o.prototype.success=function(e,i,s){if(!t.isArray(e)&&!t.isPlainObject(e))return this.plugin.log(this.plugin.LOG_ERROR,"Request did not return a JSON Array or Object.",e),void this.plugin.list.destroy();var o=this.process(e);this.plugin.list.replaceOptions(o)},e.AjaxBootstrapSelectRequest=e.AjaxBootstrapSelectRequest||o,t.fn.ajaxSelectPicker=function(i){return this.each((function(){t(this).data("AjaxBootstrapSelect")||t(this).data("AjaxBootstrapSelect",new e.AjaxBootstrapSelect(this,i))}))},t.fn.ajaxSelectPicker.locale={},t.fn.ajaxSelectPicker.defaults={ajax:{url:null,type:"POST",dataType:"json",data:{q:"{{{q}}}"}},minLength:0,bindEvent:"keyup",cache:!0,clearOnEmpty:!0,clearOnError:!0,emptyRequest:!1,ignoredKeys:{9:"tab",16:"shift",17:"ctrl",18:"alt",27:"esc",37:"left",39:"right",38:"up",40:"down",91:"meta"},langCode:null,locale:null,log:"error",preprocessData:function(){},preserveSelected:!0,preserveSelectedPosition:"after",processData:function(){},requestDelay:300,restoreOnError:!1,templates:{status:'<div class="status"></div>'}},
/*!
 * English translation for the "en-US" and "en" language codes.
 * Mark Carver <mark.carver@me.com>
 */
t.fn.ajaxSelectPicker.locale["en-US"]={currentlySelected:"Currently Selected",emptyTitle:"Select and begin typing",errorText:"Unable to retrieve results",searchPlaceholder:"Search...",statusInitialized:"Start typing a search query",statusNoResults:"No Results",statusSearching:"Searching...",statusTooShort:"Please enter more characters"},t.fn.ajaxSelectPicker.locale.en=t.fn.ajaxSelectPicker.locale["en-US"]}(jQuery,window);