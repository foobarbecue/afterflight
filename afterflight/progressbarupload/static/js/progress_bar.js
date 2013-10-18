$(document).ready(function(){
  uuid = $('#progressBar').data('progress_bar_uuid');
  // form submission
  $('form').submit(function(){
    // Prevent multiple submits
    if ($.data(this, 'submitted')) return false;
    // Append X-Progress-ID uuid form action
    this.action += (this.action.indexOf('?') == -1 ? '?' : '&') + 'X-Progress-ID=' + uuid;
    // Update progress bar
    function update_progress_info() {
      logfilename=$('#id_logfile')[0].value
      $.getJSON(upload_progress_url, {'X-Progress-ID': uuid, 'logfilename':logfilename}, function(data, status){
        //console.log(data);
        if(data){
          $('#progressBar').removeAttr('hidden');  // show progress bar if there are datas
          var progress = parseInt(data.uploaded, 10)/parseInt(data.length, 10)*100;
          $('#progressBar').attr('value', progress);
          $('#progressText').text(data.message);
        }
        else {
          $('#progressBar').attr('hidden', '');  // hide progress bar if no datas
        }
        window.setTimeout(update_progress_info, 20);
      });
    }
    window.setTimeout(update_progress_info, 20);
    $.data(this, 'submitted', true); // mark form as submitted.
    return true;
  });
});