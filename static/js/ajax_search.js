// ajax_search.js
// Watches the title input on the project registration form.
// Calls /api/title-check/?q=... and shows similar titles inline.

$(document).ready(function () {

  var typingTimer;
  var minChars  = 3;      // don't search until at least 3 chars typed
  var delay     = 400;    // ms to wait after user stops typing

  $('#id_title').on('keyup', function () {
    var query = $(this).val().trim();

    // clear previous timer on every keystroke
    clearTimeout(typingTimer);

    // hide suggestions if query is too short
    if (query.length < minChars) {
      $('#title-suggestions').addClass('d-none');
      $('#title-spinner').addClass('d-none');
      return;
    }

    // show spinner while waiting
    $('#title-spinner').removeClass('d-none');
    $('#title-suggestions').addClass('d-none');

    // wait for user to stop typing before firing request
    typingTimer = setTimeout(function () {
      $.ajax({
        url: '/api/title-check/',
        type: 'GET',
        data: { q: query },
        success: function (data) {
          $('#title-spinner').addClass('d-none');

          if (data.titles && data.titles.length > 0) {
            // populate the warning list
            var list = $('#title-list');
            list.empty();
            $.each(data.titles, function (i, title) {
              list.append('<li>' + $('<span>').text(title).html() + '</li>');
            });
            $('#title-suggestions').removeClass('d-none');
          } else {
            // no duplicates found — keep suggestions hidden
            $('#title-suggestions').addClass('d-none');
          }
        },
        error: function () {
          // silently fail — server-side check still protects on submit
          $('#title-spinner').addClass('d-none');
        }
      });
    }, delay);
  });

});