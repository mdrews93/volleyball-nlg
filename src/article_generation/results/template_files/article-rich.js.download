define(['jquery'], function($) {
	function ArticleRich(el, options) {
		this.element = el;
		var obj = this;
		
		$(window).on('refresh', function() {
		    obj.checkLayout();
		});
		obj.checkLayout();
	};
	
	ArticleRich.prototype.checkLayout = function() {
		var el = this.element;
		var w = el.width();

        if (w >= 690 && w <= 900) {
            el.removeClass('small').addClass('medium'); 
        } else if (w < 690) {
            el.removeClass('medium').addClass('small');
        } else {
            el.removeClass('small medium');
        } 
	};
	
	return ArticleRich;
});