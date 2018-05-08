define(['jquery'], function($) {
  function initialize() {
    $('[data-module]').each(function(i, el) {
      var el = $(el),
          moduleName = el.data('module'),
          options = el.data();

      delete options.module;

      if (el.data(moduleName + '_initialized')) {
        return;
      }

      require([moduleName], function(Module) {
        if (!Module) { 
          return;
        }
		
		    // compare .fn and Module to avoid naming collisions
        if (el[moduleName] && el[moduleName] === Module) {
          el[moduleName](options);
        } else {
          new Module(el, options);
        }
        
        if (options.moduleBinding && options.moduleBinding === "always") {
          return;
        }
        
        el.data(moduleName + '_initialized', true); 
      });
    });
  }

  return initialize;
});