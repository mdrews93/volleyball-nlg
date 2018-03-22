define(['jquery'], function($) {

    var pluginName = 'dropnav';
    
    const KEYCODES = { "leftArrow": 37, "rightArrow": 39, "upArrow": 38, "downArrow": 40, "escape": 27, "tab": 9, "space": 32, "enter": 13 }

    function Plugin(el) {
        var id = el.attr('id');
        var trigger = $('#jump-to-' + id);

        trigger.click(function(e) {
            e.preventDefault();
            $('html').toggleClass(id + "-active");           
            $(this).toggleClass('active');
            el.toggleClass('active');          
        });
    
        $('.close', el).click(function(e) {
            $('html').removeClass(id + "-active");         
            trigger.removeClass('active');
            el.removeClass('active');
            return false;
        });
    
        $('.has-submenu', el).on('click', function(e) {
            var targ = $(e.target);
            var item = $(this);
            
            if (targ.is(item)){
            	item.toggleClass('active');                    
            	return false; 
            } else if (targ.is(item.children('a')) && !item.data('follow-link')) {            	
            	item.toggleClass('active');                    
            	return false;       
            }
        });
        
        $('a', el).on('focus', function(e) {
            var setAriaState = function(submenu) {
                submenu.attr('aria-hidden', !submenu.is(':visible'));
            };
            
            var li = $(this).parent();
            li.addClass('focus');
            
            if (li.is('.has-submenu')) {
                setAriaState(li.children('.submenu'));
            }
            
            li.siblings().each(function() {
                $(this).removeClass('focus');
                if ($(this).is('.has-submenu')) {
                    setAriaState($(this).children('.submenu'));
                }
            });
        });
        
        $('a', el).last().keydown(function(e) { 
		    if (e.keyCode == KEYCODES['tab'] || e.keyCode == KEYCODES['downArrow']) {
			    // If the user tabs out of the navigation hide all menus
                $('.has-submenu', el).removeClass('focus');
		    }
	    });
      
        $('a', el).keydown(function(e) {
            var li = $(this).parent();
            
		    if (e.keyCode == KEYCODES['escape']) {
                $('.has-submenu', el).removeClass('focus');
		    } else if (e.keyCode == KEYCODES['tab']) {
                return true;		        
            } else if (e.keyCode == KEYCODES['leftArrow']) {
	            if (li.prev('li').length) {
	                li.prev('li').children('a').focus();
	            } else if (li.parent().closest('li').length) {
	                li.parent().closest('li').children('a').focus();
	            }
	        } else if (e.keyCode == KEYCODES['rightArrow']) {
	            if (li.next('li').length) {
	                li.next('li').children('a').focus();   
	            } else if (li.parent().closest('li').next('li').length) {
	                li.parent().closest('li').next('li').children('a').focus();
	            }
	        } else if (e.keyCode == KEYCODES['upArrow']) {
	            if (li.prev('li').length) {
	                li.prev('li').children('a').focus();
	            } else if (li.parent().closest('li').length) {
	                li.parent().closest('li').children('a').focus();
	            }
	        } else if (e.keyCode == KEYCODES['downArrow']) {
	            if (li.is('.has-submenu')) {
	                li.children('.submenu').find('li:first').children('a').focus();
	            } else {
	                if (li.next('li').length) {
	                    li.next('li').children('a').focus();
	                } else if (li.parent().next('ul').length) {
	                    li.parent().next('ul').children('li:first').children('a').focus();
	                } else if (li.parent().closest('li').next('li').length) {
	                    li.parent().closest('li').next('li').children('a').focus();
	                }
	            }
	        } else if (e.keyCode == KEYCODES['space'] || e.keyCode == KEYCODES['enter']) {
	            if (li.is('.has-submenu')) {
	                li.children('.submenu').find('li:first').children('a').focus();
	            } else {
	                return true;
	            }
	        }
	        e.preventDefault();
	    });
      
        $(document).on('click', function(e) {
        	$('.has-submenu', el).removeClass('focus active');
        });
        
        $('li', el).each(function() {
            $(this).attr({ 'role': 'menuitem', 'aria-haspopup': $(this).is('.has-submenu') });
        });
    };
    
    return Plugin;
    
});