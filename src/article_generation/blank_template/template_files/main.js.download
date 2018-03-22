if (window.jQuery) {
  define('jquery', [], function() {
    return jQuery;
  });
}

require.config({
  baseUrl: "/info",
  paths: {
    "iscroll": "iscroll-v5.1.3",
    "history": "jquery.history",
	"underscore" : "vendor/underscore-min",
	"jwplayer": "jwplayer/jwplayer"
  },
  // be sure to set jQuery.fn.* exports for shimmed jQuery plugins
  shim: {
    "iscroll": { 
      exports: "IScroll" 
    },
    "history": { 
      deps: ["jquery"], 
      exports: "History" 
    },
    "jscroll": {
      deps: ["jquery", "iscroll"],
      exports: "jQuery.fn.jscroll"
    },
    "jslider": {
      deps: ["jquery"],
      exports: "jQuery.fn.jslider" 
    },
   "jswitcher": {
      deps: ["jquery"],
      exports: "jQuery.fn.jswitcher"
    },
    "jwplayer": {
    	exports: "jwplayer"
    }
  }
});

// bootstrap
require(["jquery", "initializer", "underscore", "lazysizes"], function($, initializer, _, lazysizes) {
  /*
      initialize everything that needs to be called when the dom is ready
      or when the dom is updated via ajax
  */
  $(document).on("dom_ready dom_updated", initialize);
  $(window).on("resize", _.debounce(refresh, 200));
  $(window).on("scroll", _.debounce(function() {
	  $(window).trigger('endscroll');
  }, 100));

  $(function() {
    $(document).trigger('dom_ready');
  });

  function initialize() {
    initializer();
  
    $('.bio-wrap').length && require(['stats/bio-init']);
    
    refresh();
  }
  
  function refresh() {
    $(window).trigger("refresh");
  }
});