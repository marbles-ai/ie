/**
 * Created by tjt7a on 5/28/17.
 */

function generatedata(title, content, when, who) {
    return "<a href='#' class='list-group-item list-group-item-action flex-column align-items-start'>"
    + "<div class='d-flex w-100 justify-content-between'>"
    + "<h5 class='mb-1'>" + title + "</h5>"
    + "<small>" + when + "</small>"
    + "</div>"
    + "<p class='mb-1'>" + content + "</p>"
    + "<small>" + who + "</small>"
    + "</a>";
}


function addData(title, content) {
    $('#inputlist').append(generatedata(title, content, 'time', 'who'));
}


// The polling function
function poll(fn, callback, timeout, interval) {
    var endTime = Number(new Date()) + (timeout || 2000);
    interval = interval || 100;

    (function p() {
        // If the condition is met, we're done!
        if (fn()) {
            callback();
        }
        // If the condition isn't met but the timeout hasn't elapsed, go again
        else if (Number(new Date()) < endTime) {
            setTimeout(p, interval);
        }
        // Didn't match and too much time, reject!
        else {
            callback(new Error('timed out for ' + fn + ': ' + arguments));
        }
    })();
}

function grab_data(){

    $.getJSON("/getData", function(data){
        var article = data.article;
        var content = data.content;
        addData(article, content);
    });
}

// Usage: ensure element is visible
poll(function () {
    //return document.getElementById('lightbox').offsetWidth > 0;
    grab_data();

}, function (err) {
    if (err) {
        // Error, failure callback
    }
    else {
        // Done, success callback
    }
}, 10000, 1000);