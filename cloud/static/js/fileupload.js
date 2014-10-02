$('input:file').change(function(){
    for (i=0; i<this.files.length; i++){
        var name = this.files[i].name;
        var size = this.files[i].size;
        var type = this.files[i].type;
        //Your validation
        console.log(
            "i: " + i + "\n" + 
            "name: " + name + "\n" + 
            "size: " + size + "\n" + 
            "type: " + type + "\n"  
        );
        console.log(this.files[i]);
    }
});

$('button:submit').click(function(){
    $('button:submit').text("Wait...").attr("disabled", true); // Aviod multiple submissions
    $('.progress').attr("class", "progress show");
    var formData = new FormData($('form')[0]);
    $.ajax({
        url: formData.action,
        type: 'POST',
        xhr: function() {  // Custom XMLHttpRequest
            var myXhr = $.ajaxSettings.xhr();
            if(myXhr.upload){ // Check if upload property exists
                myXhr.upload.addEventListener('progress', progressHandlingFunction, false); // For handling the progress of the upload
            }
            return myXhr;
        },
        //Ajax events
        beforeSend: beforeSendHandler,
        success: completeHandler,
        error: errorHandler,
        // Form data
        data: formData,
        //Options to tell jQuery not to process data or worry about content-type.
        cache: false,
        contentType: false,
        processData: false
    });
    return false; //Cancel event
});

function progressHandlingFunction(e){
    if(e.lengthComputable){
        pb = $('.progress-bar');
        perc = Math.floor(100*(e.loaded/e.total));
        pb.attr({
            'aria-valuemax': e.total,
            'aria-valuenow': e.loaded,
            'style': 'width: ' + perc + '%'
        }).text(perc + "%");
    }
}

function beforeSendHandler(jqXHR, settings){
    console.log("######## beforeSendHandler");
    console.log(jqXHR);
    console.log(settings);
    //alert("will send");
}

function completeHandler(data, textstatus, jqxhr){
    console.log("######## completeHandler");
    console.log(data);
    console.log(textstatus);
    console.log(jqxhr);
    $("#main-container").html(data);
}

function errorHandler(jqXHR, textstatus, error){
    console.log("######## errorHandler");
    console.log(jqxhr);
    console.log(textstatus);
    console.log(error);
    $('button:submit').text("Submit").attr("disabled", false); // Try again
}

