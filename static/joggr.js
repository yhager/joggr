$(function() {
    api('entries/list');
    callOn('a#login', 'users/login');
    callOn('a#signup', 'users/register');
    callOn('a#logout', 'users/logout', 'POST');
    callOn('a#entries', 'entries/list');
    callOn('a#weekly', 'entries/weekly');
    callOn('#showall', 'entries/list');
    $('form').ajaxForm({
        dataType: 'json',
        delegation: true,
        success: processResponse
    });
});

function callOn(sel, cmd, method, event) {
    event = (typeof event === 'undefined') ? 'click' : event;
    $('.body').on(event, sel, function() {
        api(cmd, method);
        return false;
    });
}

function api(cmd, method) {
    method = (typeof method === 'undefined') ? 'GET' : method;
    $.ajax({
        dataType: "json",
        url: '/api/v1/' + cmd,
        type: method,
        success: processResponse
    });
}

function processResponse(response) {
    $('div.body').html(response.body);
    if (!Modernizr.inputtypes.date && $('#datepicker').length > 0) {
        $('.datepicker').datepicker({
            dateFormat: 'yy-mm-dd',
            showButtonPanel: true,
            autoSize: true,
        });
    }
}
