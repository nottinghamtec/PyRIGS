/*!
  * Bootstrap popover.js v4.6.0 (https://getbootstrap.com/)
  * Copyright 2011-2021 The Bootstrap Authors (https://github.com/twbs/bootstrap/graphs/contributors)
  * Licensed under MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)
  */
!function(t,e){"object"==typeof exports&&"undefined"!=typeof module?module.exports=e(require("jquery"),require("./tooltip.js")):"function"==typeof define&&define.amd?define(["jquery","./tooltip"],e):(t="undefined"!=typeof globalThis?globalThis:t||self).Popover=e(t.jQuery,t.Tooltip)}(this,(function(t,e){"use strict";function n(t){return t&&"object"==typeof t&&"default"in t?t:{default:t}}var o=n(t),r=n(e);function i(t,e){for(var n=0;n<e.length;n++){var o=e[n];o.enumerable=o.enumerable||!1,o.configurable=!0,"value"in o&&(o.writable=!0),Object.defineProperty(t,o.key,o)}}function u(){return(u=Object.assign||function(t){for(var e=1;e<arguments.length;e++){var n=arguments[e];for(var o in n)Object.prototype.hasOwnProperty.call(n,o)&&(t[o]=n[o])}return t}).apply(this,arguments)}var f="popover",a="bs.popover",l="."+a,s=o.default.fn[f],c=new RegExp("(^|\\s)bs-popover\\S+","g"),p=u({},r.default.Default,{placement:"right",trigger:"click",content:"",template:'<div class="popover" role="tooltip"><div class="arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>'}),d=u({},r.default.DefaultType,{content:"(string|element|function)"}),h={HIDE:"hide"+l,HIDDEN:"hidden"+l,SHOW:"show"+l,SHOWN:"shown"+l,INSERTED:"inserted"+l,CLICK:"click"+l,FOCUSIN:"focusin"+l,FOCUSOUT:"focusout"+l,MOUSEENTER:"mouseenter"+l,MOUSELEAVE:"mouseleave"+l},y=function(t){var e,n;function r(){return t.apply(this,arguments)||this}n=t,(e=r).prototype=Object.create(n.prototype),e.prototype.constructor=e,e.__proto__=n;var u,s,y,v=r.prototype;return v.isWithContent=function(){return this.getTitle()||this._getContent()},v.addAttachmentClass=function(t){o.default(this.getTipElement()).addClass("bs-popover-"+t)},v.getTipElement=function(){return this.tip=this.tip||o.default(this.config.template)[0],this.tip},v.setContent=function(){var t=o.default(this.getTipElement());this.setElementContent(t.find(".popover-header"),this.getTitle());var e=this._getContent();"function"==typeof e&&(e=e.call(this.element)),this.setElementContent(t.find(".popover-body"),e),t.removeClass("fade show")},v._getContent=function(){return this.element.getAttribute("data-content")||this.config.content},v._cleanTipClass=function(){var t=o.default(this.getTipElement()),e=t.attr("class").match(c);null!==e&&e.length>0&&t.removeClass(e.join(""))},r._jQueryInterface=function(t){return this.each((function(){var e=o.default(this).data(a),n="object"==typeof t?t:null;if((e||!/dispose|hide/.test(t))&&(e||(e=new r(this,n),o.default(this).data(a,e)),"string"==typeof t)){if(void 0===e[t])throw new TypeError('No method named "'+t+'"');e[t]()}}))},u=r,y=[{key:"VERSION",get:function(){return"4.6.0"}},{key:"Default",get:function(){return p}},{key:"NAME",get:function(){return f}},{key:"DATA_KEY",get:function(){return a}},{key:"Event",get:function(){return h}},{key:"EVENT_KEY",get:function(){return l}},{key:"DefaultType",get:function(){return d}}],(s=null)&&i(u.prototype,s),y&&i(u,y),r}(r.default);return o.default.fn[f]=y._jQueryInterface,o.default.fn[f].Constructor=y,o.default.fn[f].noConflict=function(){return o.default.fn[f]=s,y._jQueryInterface},y}));