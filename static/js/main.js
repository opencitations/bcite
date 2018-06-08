jQuery(document).ready(function () {

  // utils
  function getParameterByName(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
  };

  ///////////////
  // main page //
  ///////////////

  // style form
  $('button[value="add"]').empty();
  $('button[value="add"]').prepend('<i class="fas fa-plus"></i>');

  $('button[value="search"]').empty();
  $('button[value="search"]').prepend('<i class="fas fa-search"></i>');

  // autoresize textarea
  $('textarea').each(function () {
    this.setAttribute('style', 'height:' + (this.scrollHeight) + 'px;overflow-y:hidden;');
  }).on('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
  });

  $('.tip').tooltip(); // info tooltip authors

  /////////////
  // results //
  /////////////

  // styles
  var loc = window.location.href; // returns the full URL
  if(/results/.test(loc)) {
    $('#disclaimer').show();
    $('.background').addClass('no-bck');
    $('body').addClass('no-bck');
    $('.background').css('position','relative');
    $('.background').css('height','25%');
    $('header').css('position','fixed');
    $('header').css('background-color','white');
    $('header').css('width','100%');
    $('h1').css('height','3.5em');
    $('header h1 span').css('color','#696969');
  };

  $('#references').attr('cols', '50'); // style references text area
  // highlight references in the textarea for double check -- DOES NOT WORK
  // $("textarea").markRegExp('(.+?)(\n|$)+');

  // buttons behaviour
  $('.accept').hide();
  $('.customRef').attr('data-update','false'); // default behaviour

  $('.close').click(function() {
    $('#disclaimer').toggle( "blind" );
  });

  $("button.modify").click(function() {
    $(this).prevAll('p:first').attr("contenteditable", 'true');
    $(this).nextAll('button.accept:first').show();
  });

  $("button.reject").click(function() {
      $(this).prevAll('p:first').attr("contenteditable", 'true');
      var area = $(this).prevAll('p:first');
      area.empty();
      area.focus();
      area.attr('data-update','true'); // if reject change the value
      $(this).next('button.accept:first').show();

      $("button.accept").click(function() {
        $(this).prevAll('p:first').attr("contenteditable", 'false');
      });
  });

  $("button.accept").click(function() {
    $(this).prevAll('p:first').attr("contenteditable", 'false');
  });

  // get the query strings
  var timestamp = getParameterByName('time');
  var citing = getParameterByName('idRef'); 
  // console.log(timespan);

  // save edits, update the table, export and update the triplestore
  $(".save").click(function() {
    $(this).attr('value','done!');

    // export only the 2nd column of the table
    var table = TableExport(document.getElementById("results-table"), {
      headings: false,                       
      footers: false, 
      formats: ["xls", "csv", "txt"],        
      fileName: "results",                         
      bootstrap: true,                     
      position: "top",                   
      ignoreRows: null,                 
      ignoreCols: [0,2],                 
      ignoreCSS: ".tableexport-ignore",       
      emptyCSS: ".tableexport-empty",      
      trimWhitespace: true          
    });

    // update the table and show export buttons
    var tableUpd = $("#results-table").html();
    $("#results-table").html(tableUpd); 
    table.reset();    
    table.getExportData();

    // third call to the API: /store/{timestamp}/{accept}/{citing}/{cited}/{reference}
    $( ".customRef" ).each(function() {
      console.log( timestamp+'/'+$(this).attr('data-update')+'/'+citing+'/'+$(this).attr('id')+'/'+encodeURIComponent($(this).text()) );
      var request = new XMLHttpRequest();
      request.open('GET', 'http://localhost:8000/store/'+timestamp+'/'+$(this).attr('data-update')+'/'+citing+'/'+$(this).attr('id')+'/'+encodeURIComponent($(this).text()), true);
      request.send();
    });
  });

  

});


