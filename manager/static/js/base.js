//Loading HTML5
var cog = new Image();
var canvas_set = false;
var rotation = 0;
//Interval control variable
var intVal = 0
function start_loader() {
	if (!canvas_set){
		var canvas = document.createElement('canvas');
		canvas.setAttribute("id", "ajax-loading");
		canvas.setAttribute("width", 27);
		canvas.setAttribute("height", 27);
		canvas.setAttribute("style", "display: none; position: absolute;");
		$('body').append(canvas)
		cog.src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAbCAYAAACN1PRVAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAABK1JREFUeNqMVt1ZGzkUvVfS4IW1l8GO82w6IBXE7mCpAFMB+Pt4Z6iApALcAe4AU0HoAJfg7BPYHinnXmmciX+y0YdmJHnQ0bk/R5cvh5cUyFPwRD4EChgEvGWMB36R3+JaiTkmD5gOs8yNb25uLlerFf1pM2yIGA82TEY7xow1oj4GBU6S6yywPNG4JwDH+XGv0Whs7ndN8n97mmPsLCSYgy7ImPQE/pFDyAF+7L0fgTNFUDBcLal90taD1doQ/T6NT9DnW8zkT+jJuQVYukG3hifCVk/L3JOxMBa8VVlSp9MhHKLaB+zpNo1fdgEpmByuMqUAV5viOQLwXNax9KBAFNEEpN1pUwnQmvl6aTza6zNjrCKaymeyOdYAMgfg18iG4T/qw+AC94zvpzDjcwqOXo3VGH26H0xMZ7jPxgT0R2zUi4BYt6bAfEbJvJFZKA4ODgZ5nhcJLE9mk35X21vWC/TXKmiwr2xszoQd/PQv3t/QCzY2twpqBpb5FKOp+hCgzWaTWq0W1Xx0ij5An9WC5VtiLMwvNBrVaSGMvQk5jHQVPN7sb0HzAtE+QJrNgrcUNEARieWCut0ugR0tl8sKcJ5Ahc3jRviPK8ZGTaaBwGKyT+gTiwM4a3Jrba6MbeVXo5F4kp9shn29ndUYC9vLirGDXzRhrYhD8DME5Hkg22df5rDYS/RXmVIsaP/Q/SXs600YnifTjbeSWliEdTYb3QyTqYfdDKTL4B1KS6tVqf6SgGq3P9BvZGpvNIrPCgVKZlGlCDQDxJiCjVppCab05DJHzb+b1Gm36X80cVjLuzozexs0f6IgRkA5XRhzIixRL1+IzhwdHVHrn1Y9oXe1i10aKT6bGGhg1CKK+cT0zCGCs0oXTIogybJMw/779//o48duMvnO9rzLn+Kz8wgS5Shqo4njpCoOQA5Ajb8adHh4SMvVghaLhYb/HsBip88krNVISSEigOlhjmi0LziNhr6wOsgO9C1339vbGznnNAU2AM9Svk235cqKieKGkldAf7DGvTrjnjJnzyQoMu0ZTuZgUqvmlYR+f39XIE4uqCX1E/rDZpCYmKwOOmivAfYK9KF1AM7EdG4uAMLAOjmQideQXOJQkyUisqYiFRhtSFbxCxj8do0T30dmTvLhC+an0MZZVBHX09tBTG4qFigZEJEChjTIEwtRik81Qa7uOQU0IrYAe7FRjqYw6SlYjgAyN1GmHsFIGPfVnxzFuFITKEkfYK+oWZ5qKlIkcZ7UE92oXBmeIgIxtAO5UtSHqo9uiLW+sme5ejSIRASeAFR4LYy8MMzL1aq3EYWzJF28BgMEzGYpBkrMKelgl+P6uTcVY8NjLYyYPwMTCcufSaouH6al9xNJcjC82vDb9uVZKbrWIumNO+waVsu1TCC+Wxcg6xaSpsZSYM2wLO9/U8qZWH+wztQnsfAxV/E3MIKZVf1FsmJVV8mamhEmxZ0X7sSsABsGv1tZJGejmptU7FBUDYzPAXQBwFEEl+9+stFEroJEci2ELwIMmZuWoSTE9DYYcWVCjlJrZWMpeBhlAEqBiulPE84S3ixU5gSTwGGOdyEVNJXxA8nPevshwABHktBS1YoQ+QAAAABJRU5ErkJggg=='; // Set source path
		canvas_set = true;
	}
	//Position loader spinner
	off = $('#content').offset();
	wid = $('#content').width();
	$('#ajax-loading').css("top", off.top + 100);
	$('#ajax-loading').css("left", off.left + (wid/2) - ($('#ajax-loading').width()/2));
	//Clear content
	$('#content').html("");
	//Show loader
	intVal = setInterval(draw_loader, 50);
	$('#ajax-loading').show();
}
function stop_loader(){
	//Reset rotation speed
	rotation = 0;
	clearInterval(intVal);
	$('#ajax-loading').hide();
}

function draw_loader(){
	var ctx = $('#ajax-loading')[0].getContext('2d');
	ctx.globalCompositeOperation = 'destination-over';
	ctx.save();
	ctx.clearRect(0, 0, 27, 27);
	ctx.translate(13.5, 13.5); 
	rotation += 1;
	ctx.rotate(rotation*Math.PI/32); 
	ctx.translate(-13.5, -13.5); 
	ctx.drawImage(cog, 0, 0);
	ctx.restore();
}

//Menu ajax
var error_codes = {
	404: function() {
		alert('Page not found');
	},
	500: function() {
		alert('Internal server error');
	},
	501: function() {
		alert('Not implemented');
	}
}

function load_ajax_menu(){
	$("#sidebar a").click(function(){
		//Show loader
		start_loader()
		//Loads page
		$.ajax({
			url: this.href,
			success: function(data){
				// When response is 302 Found, it is actually being redirected (usually to login)
				if (data.redirect) {
		            // data.redirect contains the string URL to redirect to
		            window.location.href = data.redirect;
		        }else{
					$('#content').html(data);
					load_ajax_content()
					stop_loader()		        	
		        }
			},
			error: stop_loader,
			statusCode: error_codes
		});
		return false;
	})
}

function load_ajax_content(){
	$("#content a").each(function(){
		if(!$(this).hasClass("no-ajax")){
			$(this).click(function(){
				//Show loader
				start_loader()
				//Loads page
				$.ajax({
					url: this.href,
					success: function(data){
						$('#content').html(data);
						stop_loader()
					},
					error: stop_loader,
					statusCode: error_codes
				});
				return false;
			})
		}
	})
}

// Loads options via ajax to populate another select field
function select_load_options(field, url, target_id){
	// Retrieves selected option
	selected = $(field).val()
	if (selected == "" || selected == null){
		return
	}
	// Replaces the selected id in the URL (if it is there)
	url_final = url.replace("__selected_id__", selected)
	$.ajax({
		url: url_final,
		dataType: 'json',
		success: function(data){
			//Clear destination select
			t = $("#"+target_id).html("")
			for ( var i in data) {
				t.append("<option value='" + data[i][0] + "'>" + data[i][1] + "</option>");
			}
			// Trigger again the event on the next chained select (possibly updates other select options)
			t.change()
		},
		statusCode: error_codes
	});
}

//Shows/hides an element
function toogle_display(element_id, triggerer){
	if ((el = $("#" + element_id))){
		//Slide in or out the element
		if (el.is(":visible")){
			$(triggerer).text("Show");
		}else{
			$(triggerer).text("Hide");
		}
		el.slideToggle();
	}
	return false; // Avoid navigation on links
}

//Gadget "class" definition
function Gadget(url, target){
	var self = this // Self reference

	// Attributes
	this.url = url;
	this.dataType = "html";
	this.refresh = 60 //seconds
	this.target = target
	this.scheduled = false

	// Sets the refresh interval
	this.schedule = function(){
		if (this.refresh > 0){
			window.setInterval(self.load, this.refresh*1000)
		}
		this.scheduled = true
	}
	
	// Loads the gadget
	this.load = function(){
		$.ajax({
			url: "/Aurora/manager/gadgets/" + self.url + "/",
			dataType: self.dataType,
			target:  self.target,
			success: function(data){
				if (self.dataType == "html"){
					//Loads content into target
					$("#" + self.target).html(data)
				}else{
					alert("Still don't know what to do with " + self.dataType)
				}
			},
			statusCode: error_codes
		});
		if (!self.scheduled){
			self.schedule()
		}
	}
}

//Load gadgets in the home page (when they are defined)
var gadgets_list = []
function load_gadgets(){
	if(gadgets_list.length > 0){
		for (g in gadgets_list){
			gadgets_list[g].load();
		}
	}
}

$(document).ready(function(){  
	//Disabled ajax menu because it is causing problems with user login redirects
	//	load_ajax_menu();
	load_gadgets();
});
