$(function() {
    api('body');
    callOn('a#login', 'login');
    callOn('a#signup', 'signup');
    callOn('a#logout', 'logout');
    $('form#login').ajaxForm({
        dataType: 'json',
        delegation: true,
        success: processLogin
    });
    $('form#signup').ajaxForm({
        dataType: 'json',
        delegation: true,
        success: processSignup
    });
});

function callOn(sel, url, event='click') {
    $('.body').on(event, sel, function() {
        api(url);
        return false;
    });
}

function api(url) {
    $.getJSON('/api/v1/' + url, function(result) {
        $('div.body').html(result.body);
    });
}

function processLogin(data) {
    if (data.error) {
        alert(data.error);
    } else if (data.message) {
        alert(data.message)
    }
}
function processSignup(data) {
}
